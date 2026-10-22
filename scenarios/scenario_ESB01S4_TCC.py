"""Cenário Principal do TCC (ESB01S4 - Co-simulação Nativa com Mosaik)
===================================================================

Este script constitui o cenário definitivo de co-simulação para análise do
impacto da integração de Veículos Elétricos (VEs) no alimentador real ESB01S4.

Características principais:
---------------------------
1. Suporte a Múltiplos Cenários de VEs:
   - Caso Base (0 VEs / 0% penetração).
   - Alocação estocástica por Quantidade Fixa (ex: 20, 50, 100 VEs).
   - Alocação por Taxa de Penetração (Adoção Domiciliar BT, Barras BT ou Total de Barras).
   - Eletroquímica realista via Caldera ICM (C++ / IEC 61000).

2. Modulação dos Sistemas Fotovoltaicos (PVs):
   - Por padrão (`usar_pv_mosaik=False`), delega a injeção solar ao OpenDSS nativo
     (preservando estabilidade de tensão e evitando divergências numéricas de convergência).
   - O código dos simuladores Mosaik (`PVSimulator` + `InverterSim`) permanece
     totalmente pronto e implementado, podendo ser ativado pelo parâmetro `--usar-pv-mosaik`.

3. Controle de Reguladores de Tensão:
   - Integrado ao `RegulatorSimulator` do Mosaik para ajuste dinâmico de taps.

4. Monitoramento Detalhado:
   - Coleta de tensões nodais de Baixa Tensão (BT), fluxos de linha, perfis de VEs e PVs.
"""

import argparse
import asyncio
import concurrent.futures
import contextlib
import os
from pathlib import Path
from typing import Optional

import mosaik
import pandas as pd
from mosaik.util import connect_many_to_one
from simulators.util.ev_creator import alocar_evs
from simulators.util.topologia import exportar_topologia


@contextlib.contextmanager
def suprimir_stdout_c():
    """
    Silencia no nível do sistema operacional (C / libc) saídas diretas no stdout (FD 1),
    como as mensagens repetitivas '>>Waiting...' e 'Actor 1: Job done' emitidas pela DLL
    do OpenDSS a cada passo de solução.
    """
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        saved_stdout_fd = os.dup(1)
        os.dup2(devnull_fd, 1)
        os.close(devnull_fd)
        try:
            yield
        finally:
            os.dup2(saved_stdout_fd, 1)
            os.close(saved_stdout_fd)
    except Exception:
        yield

# ==============================================================================
# 1. CAMINHOS LOCAIS DO PROJETO
# ==============================================================================
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "rede" / "ESB01S4"
CIRCUITO_DSS = DATA_DIR / "run_ESB01S4.dss"
EVS_DSS_PATH = DATA_DIR / "ESB01S4_evs.dss"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JSON_SAIDA = str(OUTPUT_DIR / "topologia_ESB01S4_TCC.json")

SESSIONS_EV_CSV = (
    PROJECT_ROOT / "data" / "datasets" / "veiculos-eletricos" / "ev_sessions_caldera.csv"
)

# ==============================================================================
# 2. CONFIGURAÇÕES TEMPORAIS (Unificadas para 2024-09-09)
# ==============================================================================
START_DATE = "2024-09-09 00:00:00"
STEP_MINUTES = 10
STEP_SIZE = 60 * STEP_MINUTES
DIAS_SIMULACAO = 7
N_PASSOS = DIAS_SIMULACAO * 24 * (60 // STEP_MINUTES)
END_TIME = N_PASSOS * STEP_SIZE

IRRADIANCE_CSV_NAME = f"ESB01S4_shape_pv_{STEP_MINUTES}min.csv"
TEMPERATURE_CSV_NAME = f"ESB01S4_temperature_{STEP_MINUTES}min.csv"
IRRADIANCE_PATH = DATA_DIR / IRRADIANCE_CSV_NAME
TEMPERATURE_PATH = DATA_DIR / TEMPERATURE_CSV_NAME

# ==============================================================================
# 3. REGISTRO DE SIMULADORES NO MOSAIK
# ==============================================================================
SIM_CONFIG = {
    "DSS": {
        "python": "simulators.opendss.api_opendss:OpenDSSSimulator",
    },
    "Regulator": {
        "python": "simulators.controller.regulator_control:RegulatorSimulator",
    },
    "CalderaEV": {
        "python": "simulators.ev.caldera_ev_sim:CalderaEVSim",
    },
    "Collector": {
        "python": "simulators.collector.collector:Collector",
    },
    # Simuladores PV do Mosaik (prontos para acoplamento dinâmico)
    "PVSimulator": {
        "python": "simulators.pv.pv_panel_simulator:PVPanelSim",
    },
    "InverterSim": {
        "python": "simulators.inverter.smart_inverter_simulator:SmartInverterSim",
    },
    "CSV_Irr": {
        "python": "simulators.collector.csv_sim_pandas:CSV",
    },
    "CSV_Temp": {
        "python": "simulators.collector.csv_sim_pandas:CSV",
    },
}


def _run_scenario_impl(
    qtd_evs: Optional[int] = None,
    penetracao_pct: Optional[float] = None,
    base_calculo: str = "residencial_bt",
    seed: int = 42,
    usar_pv_mosaik: bool = False,
    nome_cenario: Optional[str] = None,
    reexecutar_alocacao: bool = False,
    mostrar_progresso: bool = False,
):
    """
    Executa o cenário principal de co-simulação com Mosaik.

    Parâmetros:
    -----------
    qtd_evs: int, opcional
        Número fixo de VEs para alocar. Se 0, executa caso base sem VEs.
    penetracao_pct: float, opcional
        Taxa de penetração em porcentagem. Se 0.0, executa caso base sem VEs.
    base_calculo: str
        "residencial_bt" (padrão), "barras_bt" ou "total_barras".
    seed: int
        Semente pseudoaleatória para reproducibilidade.
    usar_pv_mosaik: bool
        Se True, utiliza os modelos de Smart Inverter e PVPanel do Mosaik.
        Se False (padrão), utiliza o PVSystem nativo do OpenDSS.
    nome_cenario: str, opcional
        Identificador textual para nomear o arquivo CSV de saída.
    reexecutar_alocacao: bool
        Força regeração do arquivo de VEs antes da simulação.
    """
    if not CIRCUITO_DSS.exists():
        print(f"[ERRO]: Arquivo DSS não encontrado em:\n{CIRCUITO_DSS}")
        return

    # 1. Determinação do Identificador do Cenário e Arquivo de Saída
    if (qtd_evs == 0) or (penetracao_pct == 0.0):
        cenario_tag = "baseline"
    elif penetracao_pct is not None:
        cenario_tag = f"ev_p{int(penetracao_pct)}_{base_calculo}"
    elif qtd_evs is not None:
        cenario_tag = f"ev_q{qtd_evs}"
    else:
        cenario_tag = "default"

    nome_final = nome_cenario or f"result_TCC_{cenario_tag}"
    arquivo_resultados_csv = OUTPUT_DIR / f"{nome_final}.csv"

    print("\n" + "=" * 70)
    print(f" CENÁRIO PRINCIPAL TCC: {nome_final.upper()}")
    print("=" * 70)

    # 2. Configuração e Alocação dos Veículos Elétricos
    deve_alocar = (
        qtd_evs is not None
        or penetracao_pct is not None
        or reexecutar_alocacao
        or not EVS_DSS_PATH.exists()
    )

    if (qtd_evs == 0) or (penetracao_pct == 0.0):
        print("Configurando CASO BASE (Sem Veículos Elétricos)...")
        with open(EVS_DSS_PATH, "w", encoding="utf-8") as f:
            f.write("! Caso Base sem Veiculos Eletricos\n")
    elif deve_alocar:
        print("Configurando alocação estocástica de Veículos Elétricos...")
        info_aloc = alocar_evs(
            quantidade=qtd_evs,
            penetracao_pct=penetracao_pct,
            base_calculo=base_calculo,
            seed=seed,
            caminho_dss=CIRCUITO_DSS,
            output_dss=EVS_DSS_PATH,
            ev_sessions_csv=SESSIONS_EV_CSV,
        )
        print(f"Alocação concluída: {info_aloc['metrica']}")

    # 3. Exportação e Atualização da Topologia
    print("Atualizando topologia do cenário...")
    with suprimir_stdout_c():
        exportar_topologia(CIRCUITO_DSS, JSON_SAIDA)

    # 4. Inicialização da Co-simulação no Mosaik
    with mosaik.World(SIM_CONFIG, mosaik_config={"start_timeout": 60}) as world:
        print("\n--- Inicializando Co-simulação Nativa Mosaik ---")
        print(f"  Modo PV: {'Simuladores Mosaik (Smart Inverter)' if usar_pv_mosaik else 'OpenDSS Nativo (Estável)'}")
        print(f"  Arquivo de saída: {arquivo_resultados_csv.name}")

        # 4.1. Instanciação dos Simuladores Fundamentais
        reg_sim = world.start("Regulator", step_size=STEP_SIZE)
        
        # Se usar PV Mosaik, ativa bypass das curvas nativas no OpenDSS; caso contrário, desativa o bypass.
        dss_sim = world.start(
            "DSS",
            topofile=str(CIRCUITO_DSS),
            step_size=STEP_SIZE,
            bypass_native_pv_curves=usar_pv_mosaik,
        )
        
        ev_sim = world.start("CalderaEV", step_size=STEP_SIZE)
        collector = world.start(
            "Collector",
            start_date=START_DATE,
            output_file=str(arquivo_resultados_csv),
            print_results=False,
        )

        grid = dss_sim.Grid()
        monitor = collector.Monitor()

        # 4.2. Mapeamento e Conexão dos Reguladores de Tensão
        print("Conectando Reguladores de Tensão...")
        reg_info_list = dss_sim.get_detected_regulators()
        regs_dss_map = {e.eid: e for e in grid.children if e.type == "RegControl"}

        for r_info in reg_info_list:
            r_name = r_info["name"]
            r_eid = f"RegControl-{r_name}"

            ctrl_model = reg_sim.RegController.create(
                1,
                delay=r_info["delay"],
                tap_delay=r_info["tap_delay"],
                vreg=r_info["vreg"],
                band=r_info["band"],
                pt_ratio=r_info["pt_ratio"],
                ct_primary=r_info["ct_primary"],
                R=r_info["R"],
                X=r_info["X"],
                tap_ini=r_info["tap_ini"],
            )

            dss_reg = regs_dss_map[r_eid]
            world.connect(dss_reg, ctrl_model[0], "v_meas", "i_meas")
            world.connect(
                ctrl_model[0],
                dss_reg,
                ("tap_cmd", "tap"),
                time_shifted=True,
                initial_data={"tap_cmd": r_info["tap_ini"]},
            )

        # 4.3. Tratamento dos Sistemas Fotovoltaicos (PVs)
        pvs_dss_map = {e.eid: e for e in grid.children if e.type == "PVSystem"}
        buses_map = {e.eid: e for e in grid.children if e.type == "Bus"}

        if usar_pv_mosaik:
            print("Instanciando e conectando simuladores de PV e Smart Inverter via Mosaik...")
            pv_sim = world.start("PVSimulator", step_size=STEP_SIZE)
            inv_sim = world.start("InverterSim", step_size=STEP_SIZE)
            csv_sim_irr = world.start("CSV_Irr", sim_start=START_DATE, datafile=str(IRRADIANCE_PATH))
            csv_sim_temp = world.start("CSV_Temp", sim_start=START_DATE, datafile=str(TEMPERATURE_PATH))

            csv_data_irr = csv_sim_irr.Data.create(1)
            csv_data_temp = csv_sim_temp.Data.create(1)

            cols_irr = [
                c for c in pd.read_csv(IRRADIANCE_PATH, nrows=0).columns
                if c.lower() not in ["time", "date"]
            ]
            cols_tmp = [
                c for c in pd.read_csv(TEMPERATURE_PATH, nrows=0).columns
                if c.lower() not in ["time", "date"]
            ]

            pv_info = dss_sim.get_detected_pvsystems()
            for info in pv_info:
                pv_name = info["name"]
                eid_dss = info["eid_dss"]
                bus_full = info.get("bus", "")
                bus_base = bus_full.split(".")[0]

                if eid_dss in pvs_dss_map:
                    pv_dss_obj = pvs_dss_map[eid_dss]
                    bus_eid = f"Bus-{bus_base}"
                    if bus_eid not in buses_map:
                        continue
                    bus_obj = buses_map[bus_eid]

                    pv_panel_obj = pv_sim.PVPanel.create(
                        1,
                        P_mpp=info["pmpp"],
                        irradiance_base=1.0,
                        pt_curve_x=info["pt_curve_x"],
                        pt_curve_y=info["pt_curve_y"],
                        bus_name=bus_base,
                    )[0]

                    inv_obj = inv_sim.Inverter.create(
                        1,
                        kVA=info["kva"],
                        eff_curve_x=info["eff_curve_x"],
                        eff_curve_y=info["eff_curve_y"],
                        ctrl_config={
                            "reactive_mode": "none",  # Volt-VAr desligado (FP=1.0, realidade regulatória atual)
                            "volt_watt": None,        # Volt-Watt desligado (sem curtailment de potência ativa)
                        },
                        bus_name=bus_base,
                    )[0]

                    if len(cols_irr) > 1:
                        pv_num = "".join(filter(str.isdigit, pv_name)) or "1"
                        cand_irrad = f"shape_irrad_{pv_num}"
                        col_irrad = cand_irrad if cand_irrad in cols_irr else f"my_shape{pv_num}_irrad"
                        col_irrad = col_irrad if col_irrad in cols_irr else cols_irr[0]
                        cand_temp = f"shape_temp_{pv_num}"
                        col_temp = cand_temp if cand_temp in cols_tmp else f"my_shape{pv_num}_temperature"
                        col_temp = col_temp if col_temp in cols_tmp else cols_tmp[0]
                    else:
                        col_irrad, col_temp = cols_irr[0], cols_tmp[0]

                    world.connect(csv_data_irr[0], pv_panel_obj, (col_irrad, "irradiance"))
                    world.connect(csv_data_temp[0], pv_panel_obj, (col_temp, "temperature"))
                    world.connect(pv_panel_obj, inv_obj, ("P_dc", "P_dc"))

                    world.connect(
                        bus_obj,
                        inv_obj,
                        ("V1_pu", "V_meas_1"),
                        ("V2_pu", "V_meas_2"),
                        ("V3_pu", "V_meas_3"),
                        time_shifted=True,
                        initial_data={"V1_pu": 1.0, "V2_pu": 1.0, "V3_pu": 1.0},
                    )

                    world.connect(inv_obj, pv_dss_obj, ("P_ac", "P_des"), ("Q_ac", "Q_des"))

                    world.connect(pv_panel_obj, monitor, "irradiance", "temperature", "P_dc")
                    world.connect(inv_obj, monitor, "P_ac", "Q_ac")
                    world.connect(pv_dss_obj, monitor, "P_meas", "Q_meas", "P1", "P2", "P3", "Q1", "Q2", "Q3")
        else:
            print("Monitorando PVSystems nativos do OpenDSS...")
            for eid_dss, pv_dss_obj in pvs_dss_map.items():
                world.connect(
                    pv_dss_obj,
                    monitor,
                    "P_meas",
                    "Q_meas",
                    "P1",
                    "P2",
                    "P3",
                    "Q1",
                    "Q2",
                    "Q3",
                )

        # 4.4. Mapeamento e Conexão dos Veículos Elétricos (Caldera ICM)
        ev_dss_map = {e.eid: e for e in grid.children if e.type == "Load" and "ev_" in e.eid.lower()}
        
        if ev_dss_map and SESSIONS_EV_CSV.exists():
            print(f"Mapeando {len(ev_dss_map)} Veículos Elétricos com física Caldera...")
            df_sessions = pd.read_csv(SESSIONS_EV_CSV)
            perfis_disponiveis = set(df_sessions["Profile_Name"].unique())
            perfis_map = {p.lower(): p for p in perfis_disponiveis}

            count_evs = 0
            for eid_dss, ev_dss_obj in ev_dss_map.items():
                nome_raw = eid_dss.split("-", 1)[1] if "-" in eid_dss else eid_dss
                nome_id = nome_raw[3:] if nome_raw.lower().startswith("ev_") else nome_raw

                profile_slug = "_".join(nome_id.split("_")[:-1])
                profile_name = perfis_map.get(profile_slug.lower())

                if not profile_name:
                    print(f"[AVISO] Perfil não encontrado no dataset Caldera: {profile_slug}")
                    continue

                ev_obj = ev_sim.CalderaEV.create(1, profile_name=profile_name)[0]

                # Injeta potência ativa (kW) e reativa indutiva (kVAr) na barra do OpenDSS
                world.connect(ev_obj, ev_dss_obj, ("P_kw", "P_kw"), ("Q_kvar", "Q_kvar"))

                # Registra no Monitor do Coletor
                world.connect(ev_obj, monitor, "P_kw", "Q_kvar", "fp", "is_charging")
                count_evs += 1

            print(f"Total de {count_evs} VEs conectados à rede com sucesso.")
        else:
            print("Nenhum VE ativo na rede neste cenário.")

        # 4.5. Monitores de Rede (Barras BT e Linhas Críticas)
        print("Conectando barras de Baixa Tensão e linhas ao monitor...")
        barras_bt = [
            e for e in grid.children
            if e.type == "Bus" and e.extra_info.get("kv_base", 13.8) < 1.0
        ]
        print(f"Total de {len(barras_bt)} barras BT monitoradas.")
        connect_many_to_one(world, barras_bt, monitor, "V1_pu", "V2_pu", "V3_pu")

        linhas_teste = [e for e in grid.children if e.type == "Line"][:10]
        connect_many_to_one(
            world,
            linhas_teste,
            monitor,
            "I1_A",
            "I1_ang",
            "I2_A",
            "I2_ang",
            "I3_A",
            "I3_ang",
            "P1_w",
            "Q1_var",
            "P2_w",
            "Q2_var",
            "P3_w",
            "Q3_var",
        )

        # 4.6. Execução da Simulação
        print(f"\nInicializando simulação de {N_PASSOS} passos (Step={STEP_SIZE}s, Total={DIAS_SIMULACAO} dias)...")
        with suprimir_stdout_c():
            world.run(until=END_TIME, print_progress=mostrar_progresso)
        print(f"\nSimulação concluída com sucesso! Resultados em: {arquivo_resultados_csv.name}")

    return arquivo_resultados_csv


def run_scenario(
    qtd_evs: Optional[int] = None,
    penetracao_pct: Optional[float] = None,
    base_calculo: str = "residencial_bt",
    seed: int = 42,
    usar_pv_mosaik: bool = False,
    nome_cenario: Optional[str] = None,
    reexecutar_alocacao: bool = False,
    mostrar_progresso: bool = False,
):
    """
    Despacha a execução do cenário garantindo compatibilidade com Jupyter Notebooks
    e scripts normais, evitando colisões com event loops existentes do asyncio.
    """
    # 1. Aplica nest_asyncio caso disponível
    try:
        import nest_asyncio2 as nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass

    # 2. Verifica se a thread atual já possui um event loop ativo (ex: IPython / Jupyter)
    loop_ativo = None
    try:
        loop_ativo = asyncio.get_running_loop()
    except RuntimeError:
        loop_ativo = None

    if loop_ativo is not None and loop_ativo.is_running():
        # Executa em uma thread separada com event loop limpo para o Mosaik
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_scenario_impl,
                qtd_evs=qtd_evs,
                penetracao_pct=penetracao_pct,
                base_calculo=base_calculo,
                seed=seed,
                usar_pv_mosaik=usar_pv_mosaik,
                nome_cenario=nome_cenario,
                reexecutar_alocacao=reexecutar_alocacao,
                mostrar_progresso=mostrar_progresso,
            )
            return future.result()
    else:
        return _run_scenario_impl(
            qtd_evs=qtd_evs,
            penetracao_pct=penetracao_pct,
            base_calculo=base_calculo,
            seed=seed,
            usar_pv_mosaik=usar_pv_mosaik,
            nome_cenario=nome_cenario,
            reexecutar_alocacao=reexecutar_alocacao,
            mostrar_progresso=mostrar_progresso,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cenário Principal do TCC (ESB01S4) - Co-simulação Mosaik com Veículos Elétricos."
    )
    parser.add_argument(
        "--qtd-evs", "-n", type=int, default=None,
        help="Quantidade fixa de VEs para alocar (use 0 para Caso Base sem VEs)."
    )
    parser.add_argument(
        "--penetracao", "-p", type=float, default=None,
        help="Taxa de penetração de VEs em porcentagem (ex: 20 para 20%%, 0 para Caso Base)."
    )
    parser.add_argument(
        "--base", "-b", type=str, default="residencial_bt",
        choices=["residencial_bt", "barras_bt", "total_barras"],
        help="Base de cálculo da penetração (padrão: residencial_bt)."
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=42,
        help="Semente pseudoaleatória (padrão: 42)."
    )
    parser.add_argument(
        "--usar-pv-mosaik", action="store_true", default=False,
        help="Ativa os simuladores PVSimulator e InverterSim via Mosaik (padrão: False, usa PVSystem nativo do OpenDSS)."
    )
    parser.add_argument(
        "--cenario-nome", "-o", type=str, default=None,
        help="Nome identificador customizado para o arquivo de resultados CSV."
    )
    parser.add_argument(
        "--realocar", action="store_true",
        help="Força nova alocação estocástica de VEs antes de iniciar."
    )
    parser.add_argument(
        "--progresso", action="store_true", default=False,
        help="Exibe a barra de progresso durante a co-simulação (padrão: False)."
    )

    args = parser.parse_args()

    run_scenario(
        qtd_evs=args.qtd_evs,
        penetracao_pct=args.penetracao,
        base_calculo=args.base,
        seed=args.seed,
        usar_pv_mosaik=args.usar_pv_mosaik,
        nome_cenario=args.cenario_nome,
        reexecutar_alocacao=args.realocar,
        mostrar_progresso=args.progresso,
    )

