import logging
import math
import random
from pathlib import Path

import pandas as pd
import py_dss_interface

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# --- Configurações ---
QtdEVs = 50  
SEED = 42

BASE_DIR = Path(".").resolve()
REDE_DSS = BASE_DIR / 'data' / 'rede' / 'ESB01S4' / 'run_ESB01S4.dss'
EV_CSV = BASE_DIR / 'data' / 'datasets' / 'veiculos-eletricos' / 'ev_loadshapes_normalized.csv'
OUTPUT_DSS = BASE_DIR / 'data' / 'rede' / 'ESB01S4' / 'ESB01S4_evs.dss'

def obter_barras_baixa_tensao(caminho_dss: Path):
    """
    Compila o circuito e mapeia as barras de Baixa Tensão através da leitura
    das posições das cargas residenciais existentes.
    """
    dss = py_dss_interface.DSS()
    logger.info(f"Acessando topologia OpenDSS em: {caminho_dss.name}")
    
    # Zera o arquivo temporariamente para que cargas antigas 
    # não gerem avisos fantasmas de duplicidade durante a leitura da topologia.
    with open(OUTPUT_DSS, 'w') as f:
        f.write("! Arquivo temporario vazio\n")
        
    dss.text(f"Compile [{caminho_dss}]")
    dss.text("CalcVoltageBases")
    
    barras_disponiveis = []
    
    dss.loads.first()
    while True:
        nome_carga = dss.loads.name
        if not nome_carga:
            break
            
        dss.circuit.set_active_element(f"Load.{nome_carga}")
        
        bus_str = dss.cktelement.bus_names[0]
        base_bus = bus_str.split('.')[0]
        
        nos = bus_str.split('.')[1:]
        if not nos:
            nos = ['1', '2', '3']
            
        dss.circuit.set_active_bus(base_bus)
        kv_base = dss.bus.kv_base
        if kv_base == 0:
            kv_base = 0.38 
            
        barras_disponiveis.append({
            'bus': base_bus,
            'nodes': nos,
            'kv': kv_base
        })
        
        if not dss.loads.next():
            break
            
    logger.info(f"Mapeamento concluído: {len(barras_disponiveis)} locais de conexão identificados.")
    return barras_disponiveis

def criar_script_evs(qtd_evs: int, seed: int):
    random.seed(seed)
    
    barras = obter_barras_baixa_tensao(REDE_DSS)
    
    logger.info(f"Lendo perfis de VEs: {EV_CSV.name}")
    df_evs = pd.read_csv(EV_CSV)
    
    # Ignora colunas de data/hora
    curvas_disponiveis = [col for col in df_evs.columns if col.lower() not in ['date', 'time']]
    
    logger.info(f"Iniciando alocação de {qtd_evs} VEs Monofásicos...")
    ev_commands = []
    
    for i in range(1, qtd_evs + 1):
        curva_sorteada = random.choice(curvas_disponiveis)
        barra = random.choice(barras)
        
        no_fase = random.choice(barra['nodes'])
        bus_monofasico = f"{barra['bus']}.{no_fase}"
        
        potencia = 3.6 if '3.6kW' in curva_sorteada else 7.2
        kv_monofasico = barra['kv'] / math.sqrt(3)
        
        # O replace garante que o nome seja aceito pelo OpenDSS, e adicionamos _idx
        # para blindar contra qualquer duplicata extrema
        nome_id = f"{curva_sorteada.replace('.', '_')}_{i}"
        
        cmd = f"New Load.EV_{nome_id} Bus1={bus_monofasico} Phases=1 kV={kv_monofasico:.3f} kW={potencia} pf=1.0 status=variable"
        ev_commands.append(cmd)
        
    with open(OUTPUT_DSS, 'w') as f:
        f.write(f"! Alocação estocástica de {qtd_evs} VEs monofásicos (Seed: {seed})\n")
        for cmd in ev_commands:
            f.write(cmd + "\n")
            
    logger.info(f"Arquivo exportado para: {OUTPUT_DSS.name}")

if __name__ == "__main__":
    criar_script_evs(QtdEVs, SEED)
