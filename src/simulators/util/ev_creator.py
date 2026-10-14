import argparse
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional

import pandas as pd
import py_dss_interface

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# --- Caminhos Absolutos Baseados na Raiz do Projeto ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REDE_DSS = PROJECT_ROOT / 'data' / 'rede' / 'ESB01S4' / 'run_ESB01S4.dss'
EV_SESSIONS_CSV = PROJECT_ROOT / 'data' / 'datasets' / 'veiculos-eletricos' / 'ev_sessions_caldera.csv'
EV_CSV = PROJECT_ROOT / 'data' / 'datasets' / 'veiculos-eletricos' / 'ev_loadshapes_normalized.csv'
OUTPUT_DSS = PROJECT_ROOT / 'data' / 'rede' / 'ESB01S4' / 'ESB01S4_evs.dss'


def mapear_topologia_bt(caminho_dss: Path, output_dss_path: Path):
    """
    Compila o circuito no OpenDSS e mapeia as barras e domicílios de Baixa Tensão (BT),
    além de computar o total de barras e unidades consumidoras residenciais.
    """
    dss = py_dss_interface.DSS()
    logger.info(f"Compilando circuito para mapeamento de BT: {caminho_dss.name}")

    # Garante que o arquivo de EVs exista (mesmo vazio) para evitar erro de compilação
    output_dss_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_dss_path.exists():
        with open(output_dss_path, 'w', encoding='utf-8') as f:
            f.write("! Arquivo temporario vazio\n")

    dss.text(f"Compile [{caminho_dss}]")
    dss.text("CalcVoltageBases")

    todas_barras = dss.circuit.buses_names
    total_barras_feeder = dss.circuit.num_buses or len(todas_barras)

    # Dicionário de domicílios/consumidores BT: cada consumidor possui normalmente _M1 e _M2
    consumidores_bt: Dict[str, Dict[str, Any]] = {}

    dss.loads.first()
    while True:
        nome_carga = dss.loads.name
        if not nome_carga:
            break

        # Filtra cargas residenciais de Baixa Tensão
        if nome_carga.lower().startswith("bt_"):
            dss.circuit.set_active_element(f"Load.{nome_carga}")

            bus_str = dss.cktelement.bus_names[0]
            base_bus = bus_str.split('.')[0]
            nos = bus_str.split('.')[1:]

            fases = [n for n in nos if n in ['1', '2', '3']]
            if not fases:
                fases = ['1', '2', '3']

            dss.circuit.set_active_bus(base_bus)
            kv_base = dss.bus.kv_base

            # Filtra barras com tensão nominal <= 1 kV (Baixa Tensão)
            if kv_base <= 1.0:
                # Extrai o ID do domicílio (removendo sufixos _M1 / _M2 se existirem)
                # Exemplo: BT_U52513810_M1 -> BT_U52513810
                uc_id = nome_carga.rsplit('_', 1)[0]
                if uc_id not in consumidores_bt:
                    consumidores_bt[uc_id] = {
                        'uc_id': uc_id,
                        'bus': base_bus,
                        'phases': fases,
                        'kv': 0.220  # Tensão monofásica nominal fase-neutro no Ceará (220V)
                    }

        if not dss.loads.next():
            break

    barras_bt_unicas = sorted(list({c['bus'] for c in consumidores_bt.values()}))

    logger.info(
        f"Mapeamento concluído: {len(consumidores_bt)} domicílios BT identificados em "
        f"{len(barras_bt_unicas)} barras BT (Total do alimentador: {total_barras_feeder} barras)."
    )

    return {
        "consumidores_bt": consumidores_bt,
        "barras_bt_unicas": barras_bt_unicas,
        "total_barras_feeder": total_barras_feeder,
    }


def alocar_evs(
    quantidade: Optional[int] = None,
    penetracao_pct: Optional[float] = None,
    base_calculo: str = "residencial_bt",
    seed: int = 42,
    caminho_dss: Optional[Path] = None,
    output_dss: Optional[Path] = None,
    ev_sessions_csv: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Aloca Veículos Elétricos monofásicos (220V) de forma estocástica e reproduzível na rede.

    Parâmetros:
    -----------
    quantidade: int, opcional
        Número absoluto de VEs a serem alocados (ex: 10, 50, 100).
    penetracao_pct: float, opcional
        Taxa de penetração em porcentagem (ex: 5.0 para 5%, 20.0 para 20%).
    base_calculo: str, padrão "residencial_bt"
        Define a base para cálculo da penetração quando penetracao_pct for especificado:
        - "residencial_bt": Taxa de Adoção Residencial/Domiciliar (% dos domicílios BT com VE). [Recomendado cientificamente]
        - "barras_bt": % das barras de baixa tensão com VE.
        - "total_barras": % do total de barras do alimentador (incluindo MT).
    seed: int, padrão 42
        Semente pseudoaleatória para reprodutibilidade estrita da alocação e sorteio de perfis.
    caminho_dss: Path, opcional
        Caminho do arquivo principal do circuito DSS (padrão: run_ESB01S4.dss).
    output_dss: Path, opcional
        Caminho onde será salvo o arquivo de VEs (.dss) (padrão: ESB01S4_evs.dss).
    ev_sessions_csv: Path, opcional
        Caminho do CSV de sessões de recarga Caldera.

    Retorno:
    --------
    dict com informações detalhadas da alocação realizada.
    """
    caminho_dss = Path(caminho_dss).resolve() if caminho_dss else REDE_DSS
    output_dss = Path(output_dss).resolve() if output_dss else OUTPUT_DSS
    ev_sessions_csv = Path(ev_sessions_csv).resolve() if ev_sessions_csv else EV_SESSIONS_CSV

    random.seed(seed)

    dados_topologia = mapear_topologia_bt(caminho_dss, output_dss)
    consumidores_bt = dados_topologia["consumidores_bt"]
    barras_bt_unicas = dados_topologia["barras_bt_unicas"]
    total_barras_feeder = dados_topologia["total_barras_feeder"]

    total_domicilios = len(consumidores_bt)
    total_barras_bt = len(barras_bt_unicas)

    if total_domicilios == 0:
        raise RuntimeError("Nenhum domicílio ou carga de Baixa Tensão identificada para alocação dos VEs.")

    # 1. Determinação da Quantidade de VEs
    if quantidade is not None:
        qtd_evs = int(quantidade)
        metrica_str = f"Quantidade fixa ({qtd_evs} VEs)"
    elif penetracao_pct is not None:
        pct = float(penetracao_pct)
        if pct < 0:
            raise ValueError("A taxa de penetração percentual não pode ser negativa.")

        base_norm = base_calculo.lower().strip()
        if base_norm in ["residencial_bt", "domiciliar", "domicilio", "domicilios", "residencial"]:
            qtd_evs = max(1, round((pct / 100.0) * total_domicilios)) if pct > 0 else 0
            metrica_str = f"{pct:.1f}% de Adoção Domiciliar BT ({qtd_evs} VEs sobre {total_domicilios} domicílios)"
        elif base_norm in ["barras_bt", "barra_bt", "bus_bt"]:
            qtd_evs = max(1, round((pct / 100.0) * total_barras_bt)) if pct > 0 else 0
            metrica_str = f"{pct:.1f}% das Barras BT ({qtd_evs} VEs sobre {total_barras_bt} barras BT)"
        elif base_norm in ["total_barras", "barras_totais", "feeder_buses"]:
            qtd_evs = max(1, round((pct / 100.0) * total_barras_feeder)) if pct > 0 else 0
            metrica_str = f"{pct:.1f}% do Total de Barras ({qtd_evs} VEs sobre {total_barras_feeder} barras totais)"
        else:
            raise ValueError(
                f"Base de cálculo '{base_calculo}' não suportada. "
                f"Opções válidas: 'residencial_bt', 'barras_bt', 'total_barras'."
            )
    else:
        qtd_evs = 50
        metrica_str = f"Padrão fixo ({qtd_evs} VEs)"

    # 2. Carregamento dos Perfis Disponíveis
    if ev_sessions_csv.exists():
        logger.info(f"Lendo perfis de VEs do dataset Caldera: {ev_sessions_csv.name}")
        df_sessions = pd.read_csv(ev_sessions_csv)
        curvas_disponiveis = sorted(df_sessions["Profile_Name"].unique())
    elif EV_CSV.exists():
        logger.info(f"Lendo perfis de VEs do dataset CSV padrão: {EV_CSV.name}")
        df_evs = pd.read_csv(EV_CSV)
        curvas_disponiveis = [col for col in df_evs.columns if col.lower() not in ['date', 'time']]
    else:
        raise FileNotFoundError(f"Arquivo de perfis de VEs não encontrado em: {ev_sessions_csv} ou {EV_CSV}")

    # 3. Seleção Estocástica de Locais (Domicílios)
    lista_consumidores = list(consumidores_bt.values())
    if qtd_evs <= len(lista_consumidores):
        # Amostragem sem reposição: no máximo 1 VE por domicílio
        locais_sorteados = random.sample(lista_consumidores, qtd_evs)
    else:
        # Se a quantidade superar os domicílios, amostra com reposição
        locais_sorteados = random.choices(lista_consumidores, k=qtd_evs)

    logger.info(f"Iniciando geração de {qtd_evs} VEs Monofásicos BT (220V) [{metrica_str}]...")

    ev_commands: List[str] = []
    for i, local in enumerate(locais_sorteados, start=1):
        curva_sorteada = random.choice(curvas_disponiveis)
        no_fase = random.choice(local['phases'])

        # Conexão monofásica fase-neutro (.fase.4) com a ddp de 220V
        bus_monofasico = f"{local['bus']}.{no_fase}.4"

        # Reconhece 3.6kW ou 7.2kW conforme a nomenclatura do perfil
        potencia = 3.6 if ('3.6' in curva_sorteada or '3p6' in curva_sorteada) else 7.2
        kv_monofasico = local['kv']

        nome_id = f"{curva_sorteada}_{i}"
        cmd = (
            f"New Load.EV_{nome_id} Bus1={bus_monofasico} Phases=1 Conn=Wye "
            f"kV={kv_monofasico:.3f} kW={potencia} pf=1.0 status=variable"
        )
        ev_commands.append(cmd)

    # 4. Gravação do Arquivo DSS
    with open(output_dss, 'w', encoding='utf-8') as f:
        f.write("! ======================================================================\n")
        f.write(f"! Alocação Estocástica de Veículos Elétricos (OpenDSS)\n")
        f.write(f"! Métrica: {metrica_str}\n")
        f.write(f"! Quantidade de VEs: {qtd_evs}\n")
        f.write(f"! Semente (Seed): {seed}\n")
        f.write(f"! Total de Domicílios BT: {total_domicilios}\n")
        f.write(f"! Total de Barras BT com Cargas: {total_barras_bt}\n")
        f.write(f"! Total de Barras do Alimentador: {total_barras_feeder}\n")
        f.write("! ======================================================================\n\n")
        for cmd in ev_commands:
            f.write(cmd + "\n")

    logger.info(f"Arquivo DSS de VEs gerado com sucesso: {output_dss.name} ({len(ev_commands)} VEs salvos)")

    return {
        "qtd_evs": qtd_evs,
        "penetracao_pct": penetracao_pct,
        "base_calculo": base_calculo,
        "metrica": metrica_str,
        "seed": seed,
        "total_domicilios_bt": total_domicilios,
        "total_barras_bt": total_barras_bt,
        "total_barras_feeder": total_barras_feeder,
        "output_file": str(output_dss),
    }


def criar_script_evs(qtd_evs: int = 50, seed: int = 42):
    """
    Função legada para manter compatibilidade total com chamadas existentes.
    """
    return alocar_evs(quantidade=qtd_evs, seed=seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Alocação estocástica dinâmica de Veículos Elétricos em Baixa Tensão."
    )
    parser.add_argument(
        "--qtd", "-n", type=int, default=None,
        help="Quantidade absoluta de VEs a serem alocados."
    )
    parser.add_argument(
        "--penetracao", "-p", type=float, default=None,
        help="Taxa de penetração em porcentagem (ex: 20 para 20%%)."
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

    args = parser.parse_args()

    # Se nenhum parâmetro for fornecido na linha de comando, executa com 50 VEs padrão
    qtd_final = args.qtd if (args.qtd is not None or args.penetracao is not None) else 50
    resultado = alocar_evs(
        quantidade=qtd_final,
        penetracao_pct=args.penetracao,
        base_calculo=args.base,
        seed=args.seed,
    )
    print("\n--- Resultado da Alocação ---")
    for k, v in resultado.items():
        print(f"  {k}: {v}")
