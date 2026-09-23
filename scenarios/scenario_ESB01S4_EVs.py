import mosaik
import pandas as pd
from pathlib import Path
from mosaik.util import connect_many_to_one
from simulators.util.topologia import exportar_topologia

# ==============================================================================
# 1. CAMINHOS NO HOST (Windows)
# ==============================================================================
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR_HOST = PROJECT_ROOT / "data" / "rede" / "ESB01S4"
CIRCUITO_DSS_HOST = DATA_DIR_HOST / "run_ESB01S4.dss"
OUTPUT_DIR_HOST = PROJECT_ROOT / "output"
OUTPUT_DIR_HOST.mkdir(parents=True, exist_ok=True)
ARQUIVO_RESULTADOS_CSV_HOST = OUTPUT_DIR_HOST / 'result_run_ESB01S4_EVs.csv'
JSON_SAIDA = str(PROJECT_ROOT / 'output' / 'topologia_ESB01S4_EVs.json')

EV_CSV_HOST = PROJECT_ROOT / "data" / "datasets" / "veiculos-eletricos" / "ev_loadshapes_normalized.csv"

# ==============================================================================
# 2. CONFIGURAÇÕES DE TEMPO E PASSOS
# ==============================================================================
START_DATE = "2026-01-01 00:00:00"
STEP_MINUTES = 10
STEP_SIZE = 60 * STEP_MINUTES
DIAS_SIMULACAO = 7
N_PASSOS = DIAS_SIMULACAO * 24 * (60 // STEP_MINUTES)
END_TIME = N_PASSOS * STEP_SIZE

# ==============================================================================
# 3. CAMINHOS NO CONTAINER (Linux/Docker)
# ==============================================================================
CONTAINER_DATA = "/app/data/rede/ESB01S4"
CIRCUITO_DSS_CONT = f"{CONTAINER_DATA}/run_ESB01S4.dss"

IRRADIANCE_CSV_NAME = f"ESB01S4_shape_pv_{STEP_MINUTES}min.csv"
TEMPERATURE_CSV_NAME = f"ESB01S4_temperature_{STEP_MINUTES}min.csv"

IRRADIANCE_CONT = f"{CONTAINER_DATA}/{IRRADIANCE_CSV_NAME}"
TEMPERATURE_CONT = f"{CONTAINER_DATA}/{TEMPERATURE_CSV_NAME}"
ARQUIVO_RESULTADOS_CSV_CONT = "/app/output/result_run_ESB01S4_EVs.csv"

EV_CSV_CONT = "/app/data/datasets/veiculos-eletricos/ev_loadshapes_normalized.csv"

# ==============================================================================
# 4. CONFIGURAÇÃO DE CONEXÃO (DOCKER)
# ==============================================================================
SIM_CONFIG = {
    'DSS': {
        'connect': 'localhost:5771',
    },
    'PVSimulator': {
        'connect': 'localhost:5778'
    },
    'InverterSim': {
        'connect': 'localhost:5780' # Porta 5780 = inverter-smart
    },
    'CSV_Irr': {
        'connect': 'localhost:5775' # Porta 5775 = csv-data-1
    },
    'CSV_Temp': {
        'connect': 'localhost:5776' # Porta 5776 = csv-data-2
    },
    'CSV_EV': {
        'connect': 'localhost:5782' # Porta 5782 = csv-data-3
    },
    'EVCharger': {
        'connect': 'localhost:5781' # Porta 5781 = ev-charger
    },
    'Collector': {
        'connect': 'localhost:5773',
    },
}

def run_scenario():
    if not CIRCUITO_DSS_HOST.exists():
        print(f"[ERRO]: Arquivo DSS não encontrado no Windows em:\n{CIRCUITO_DSS_HOST}")
        return

    with mosaik.World(SIM_CONFIG, mosaik_config={'start_timeout': 600}) as world:
        print("--- Conectando aos Simuladores no Docker ---")

        dss_sim = world.start('DSS', topofile=CIRCUITO_DSS_CONT, step_size=STEP_SIZE)
        pv_sim = world.start('PVSimulator', step_size=STEP_SIZE)
        inv_sim = world.start('InverterSim', step_size=STEP_SIZE)
        csv_sim_irr = world.start('CSV_Irr', sim_start=START_DATE, datafile=IRRADIANCE_CONT)
        csv_sim_temp = world.start('CSV_Temp', sim_start=START_DATE, datafile=TEMPERATURE_CONT)
        csv_sim_ev = world.start('CSV_EV', sim_start=START_DATE, datafile=EV_CSV_CONT)
        ev_sim = world.start('EVCharger', step_size=STEP_SIZE)

        collector = world.start('Collector', start_date=START_DATE, output_file=ARQUIVO_RESULTADOS_CSV_CONT, print_results=False)

        print("Instanciando a Grid do OpenDSS...")
        grid = dss_sim.Grid()
        csv_data_irr = csv_sim_irr.Data.create(1)
        csv_data_temp = csv_sim_temp.Data.create(1)
        csv_data_ev = csv_sim_ev.Data.create(1)
        monitor = collector.Monitor()

        # ====================================================================
        # ALGORITMO DE INSTANCIAÇÃO E CONEXÃO DO SMART INVERTER E PV
        # ====================================================================
        print("Mapeando PVs...")
        pv_info = dss_sim.get_detected_pvsystems()
        pvs_dss_map = {e.eid: e for e in grid.children if e.type == 'PVSystem'}
        buses_map = {e.eid: e for e in grid.children if e.type == 'Bus'}

        for info in pv_info:
            pv_name = info['name']
            eid_dss = info['eid_dss']
            bus_full = info.get('bus', '')
            bus_base = bus_full.split('.')[0]

            if eid_dss in pvs_dss_map:
                pv_dss_obj = pvs_dss_map[eid_dss]
                bus_eid = f"Bus-{bus_base}"
                
                if bus_eid not in buses_map:
                    continue
                bus_obj = buses_map[bus_eid]

                pv_panel_obj = pv_sim.PVPanel.create(
                    1, P_mpp=info['pmpp'], irradiance_base=1.0,
                    pt_curve_x=info['pt_curve_x'], pt_curve_y=info['pt_curve_y'],
                    bus_name=bus_base
                )[0]

                inv_obj = inv_sim.Inverter.create(
                    1, kVA=info['kva'], eff_curve_x=info['eff_curve_x'],
                    eff_curve_y=info['eff_curve_y'], ctrl_config={}, bus_name=bus_base
                )[0]

                cols_irr = [c for c in pd.read_csv(DATA_DIR_HOST / IRRADIANCE_CSV_NAME, nrows=0).columns if c.lower() not in ['time', 'date']]
                cols_tmp = [c for c in pd.read_csv(DATA_DIR_HOST / TEMPERATURE_CSV_NAME, nrows=0).columns if c.lower() not in ['time', 'date']]
                
                if len(cols_irr) > 1:
                    pv_number = ''.join(filter(str.isdigit, pv_name)) or '1'
                    col_irrad = f"my_shape{pv_number}_irrad"
                    col_irrad = col_irrad if col_irrad in cols_irr else cols_irr[0]
                    col_temp = f"my_shape{pv_number}_temperature"
                    col_temp = col_temp if col_temp in cols_tmp else cols_tmp[0]
                else:
                    col_irrad, col_temp = cols_irr[0], cols_tmp[0]

                world.connect(csv_data_irr[0], pv_panel_obj, (col_irrad, 'irradiance'))
                world.connect(csv_data_temp[0], pv_panel_obj, (col_temp, 'temperature'))
                world.connect(pv_panel_obj, inv_obj, ('P_dc', 'P_dc'))

                world.connect(bus_obj, inv_obj,
                                ('V1_pu', 'V_meas_1'), ('V2_pu', 'V_meas_2'), ('V3_pu', 'V_meas_3'),
                                time_shifted=True, initial_data={'V1_pu': 1.0, 'V2_pu': 1.0, 'V3_pu': 1.0})

                world.connect(inv_obj, pv_dss_obj, ('P_ac', 'P_des'), ('Q_ac', 'Q_des'))

                world.connect(pv_panel_obj, monitor, 'irradiance', 'temperature', 'P_dc')
                world.connect(inv_obj, monitor, 'P_ac', 'Q_ac')
                world.connect(pv_dss_obj, monitor, 'P_meas', 'Q_meas')
                world.connect(pv_dss_obj, monitor, 'P1', 'P2', 'P3', 'Q1', 'Q2', 'Q3')


        # ====================================================================
        # ALGORITMO DE INSTANCIAÇÃO E CONEXÃO DOS VEÍCULOS ELÉTRICOS (EV)
        # ====================================================================
        print("Mapeando Veículos Elétricos...")
        ev_dss_map = {e.eid: e for e in grid.children if e.type == 'Load' and 'EV_' in e.eid}
        
        # Mapeamento reverso para encontrar a coluna exata do CSV
        cols_ev = [c for c in pd.read_csv(EV_CSV_HOST, nrows=0).columns if c.lower() not in ['time', 'date']]
        ev_col_map = {c.replace('.', '_'): c for c in cols_ev}

        for eid_dss, ev_dss_obj in ev_dss_map.items():
            # eid_dss vem no formato "Load-EV_User_1_semana_1_7_2kW_1"
            nome_id = eid_dss.replace('Load-EV_', '')
            
            # Remove o sufixo numérico (_1, _2) que foi adicionado no ev_creator
            nome_id_limpo = '_'.join(nome_id.split('_')[:-1])
            
            col_csv = ev_col_map.get(nome_id_limpo)
            
            if not col_csv:
                print(f"[AVISO] Curva não encontrada no CSV para o VE: {nome_id_limpo}")
                continue

            potencia = 3.6 if '3.6kW' in col_csv else 7.2

            ev_charger_obj = ev_sim.EVCharger.create(
                1,
                charger_capacity_kw=potencia,
                power_factor=1.0,
                bus_name=nome_id
            )[0]

            # Conecta a coluna de demanda (CSV) no Carregador
            world.connect(csv_data_ev[0], ev_charger_obj, (col_csv, 'normalized_power'))
            
            # Conecta o Carregador na Carga do OpenDSS (Injeção de P e Q)
            world.connect(ev_charger_obj, ev_dss_obj, ('P_kw', 'P_kw'), ('Q_kvar', 'Q_kvar'))
            
            # Monitoramento
            world.connect(ev_charger_obj, monitor, 'P_kw', 'Q_kvar')


        # ====================================================================
        # MONITORES DE REDE
        # ====================================================================
        print("Conectando apenas 5 barras ao monitor (modo teste)...")
        barras_teste = [e for e in grid.children if e.type == 'Bus'][:5]
        connect_many_to_one(world, barras_teste, monitor, 'V1_pu', 'V2_pu', 'V3_pu')

        print("Conectando apenas 5 linhas ao monitor (modo teste)...")
        linhas_teste = [e for e in grid.children if e.type == 'Line'][:5]
        connect_many_to_one(
            world, linhas_teste, monitor,
            'I1_A', 'I1_ang', 'I2_A', 'I2_ang', 'I3_A', 'I3_ang',
            'P1_w', 'Q1_var', 'P2_w', 'Q2_var', 'P3_w', 'Q3_var'
        )

        print(f"\nInicializando simulação de {N_PASSOS} passos (Step={STEP_SIZE}s)...")

        world.run(until=END_TIME, print_progress=True)
        print("Simulação concluída.")

        if ARQUIVO_RESULTADOS_CSV_HOST.exists():
            print(f"\nResultados salvos em: {ARQUIVO_RESULTADOS_CSV_HOST}")

print("Gerando topologia do cenário...")
exportar_topologia(CIRCUITO_DSS_HOST, JSON_SAIDA)

if __name__ == '__main__':
    run_scenario()
