import mosaik
import pandas as pd
from pathlib import Path
from mosaik.util import connect_many_to_one
from simulators.util.topologia import exportar_topologia

# ==============================================================================
# 1. CAMINHOS LOCAIS DO PROJETO (Nativo)
# ==============================================================================
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "rede" / "ESB01S4"
CIRCUITO_DSS = DATA_DIR / "run_ESB01S4.dss"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARQUIVO_RESULTADOS_CSV = OUTPUT_DIR / "result_run_ESB01S4.csv"
JSON_SAIDA = str(OUTPUT_DIR / "topologia_ESB01S4.json")

# ==============================================================================
# 2. CONFIGURAÇÕES DE TEMPO E PASSOS
# ==============================================================================
START_DATE = "2026-01-01 00:00:00"
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
# 3. CONFIGURAÇÃO DE SIMULADORES (MOSAIK NATIVO EM PYTHON - SEM DOCKER)
# ==============================================================================
SIM_CONFIG = {
    "DSS": {
        "python": "simulators.opendss.api_opendss:OpenDSSSimulator",
    },
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
    "Collector": {
        "python": "simulators.collector.collector:Collector",
    },
}


def run_scenario():
    if not CIRCUITO_DSS.exists():
        print(f"[ERRO]: Arquivo DSS não encontrado em:\n{CIRCUITO_DSS}")
        return

    with mosaik.World(SIM_CONFIG, mosaik_config={"start_timeout": 60}) as world:
        print("--- Iniciando Co-simulação Mosaik Nativa (Sem Docker) ---")

        # 1. Iniciando Simuladores Nativamente em Python
        dss_sim = world.start("DSS", topofile=str(CIRCUITO_DSS), step_size=STEP_SIZE)
        pv_sim = world.start("PVSimulator", step_size=STEP_SIZE)
        inv_sim = world.start("InverterSim", step_size=STEP_SIZE)
        csv_sim_irr = world.start("CSV_Irr", sim_start=START_DATE, datafile=str(IRRADIANCE_PATH))
        csv_sim_temp = world.start("CSV_Temp", sim_start=START_DATE, datafile=str(TEMPERATURE_PATH))
        collector = world.start(
            "Collector",
            start_date=START_DATE,
            output_file=str(ARQUIVO_RESULTADOS_CSV),
            print_results=False,
        )

        print("Instanciando a Grid do OpenDSS...")
        grid = dss_sim.Grid()
        csv_data_irr = csv_sim_irr.Data.create(1)
        csv_data_temp = csv_sim_temp.Data.create(1)
        monitor = collector.Monitor()

        pv_info = dss_sim.get_detected_pvsystems()
        pvs_dss_map = {e.eid: e for e in grid.children if e.type == "PVSystem"}
        buses_map = {e.eid: e for e in grid.children if e.type == "Bus"}

        # ====================================================================
        # ALGORITMO DE INSTANCIAÇÃO E CONEXÃO DO SMART INVERTER
        # ====================================================================
        print("Mapeando PVs e Inversores...")
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
                    ctrl_config={},
                    bus_name=bus_base,
                )[0]

                cols_irr = [
                    c
                    for c in pd.read_csv(IRRADIANCE_PATH, nrows=0).columns
                    if c.lower() not in ["time", "date"]
                ]
                cols_tmp = [
                    c
                    for c in pd.read_csv(TEMPERATURE_PATH, nrows=0).columns
                    if c.lower() not in ["time", "date"]
                ]

                if len(cols_irr) > 1:
                    pv_number = "".join(filter(str.isdigit, pv_name)) or "1"
                    col_irrad = f"my_shape{pv_number}_irrad"
                    col_irrad = col_irrad if col_irrad in cols_irr else cols_irr[0]
                    col_temp = f"my_shape{pv_number}_temperature"
                    col_temp = col_temp if col_temp in cols_tmp else cols_tmp[0]
                else:
                    col_irrad, col_temp = cols_irr[0], cols_tmp[0]

                world.connect(csv_data_irr[0], pv_panel_obj, (col_irrad, "irradiance"))
                world.connect(csv_data_temp[0], pv_panel_obj, (col_temp, "temperature"))
                world.connect(pv_panel_obj, inv_obj, ("P_dc", "P_dc"))

                # Malha fechada de controle com a tensão da barra
                world.connect(
                    bus_obj,
                    inv_obj,
                    ("V1_pu", "V_meas_1"),
                    ("V2_pu", "V_meas_2"),
                    ("V3_pu", "V_meas_3"),
                    time_shifted=True,
                    initial_data={"V1_pu": 1.0, "V2_pu": 1.0, "V3_pu": 1.0},
                )

                # Injeção de P e Q na rede
                world.connect(inv_obj, pv_dss_obj, ("P_ac", "P_des"), ("Q_ac", "Q_des"))

                # Monitoramento
                world.connect(pv_panel_obj, monitor, "irradiance", "temperature", "P_dc")
                world.connect(inv_obj, monitor, "P_ac", "Q_ac")
                world.connect(pv_dss_obj, monitor, "P_meas", "Q_meas")
                world.connect(pv_dss_obj, monitor, "P1", "P2", "P3", "Q1", "Q2", "Q3")

        # ====================================================================
        # MONITORES DE REDE
        # ====================================================================
        print("Conectando barras ao monitor...")
        barras_teste = [e for e in grid.children if e.type == "Bus"][:5]
        connect_many_to_one(world, barras_teste, monitor, "V1_pu", "V2_pu", "V3_pu")

        linhas_teste = [e for e in grid.children if e.type == "Line"][:5]
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

        print(f"\nInicializando simulação nativa de {N_PASSOS} passos (Step={STEP_SIZE}s)...")
        world.run(until=END_TIME, print_progress=True)
        print("Simulação concluída com sucesso!")

        if ARQUIVO_RESULTADOS_CSV.exists():
            print(f"\nResultados salvos em: {ARQUIVO_RESULTADOS_CSV}")


print("Gerando topologia do cenário...")
exportar_topologia(CIRCUITO_DSS, JSON_SAIDA)

if __name__ == "__main__":
    run_scenario()