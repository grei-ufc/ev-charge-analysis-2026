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
EV_SESSIONS_CSV = BASE_DIR / 'data' / 'datasets' / 'veiculos-eletricos' / 'ev_sessions_caldera.csv'
EV_CSV = BASE_DIR / 'data' / 'datasets' / 'veiculos-eletricos' / 'ev_loadshapes_normalized.csv'
OUTPUT_DSS = BASE_DIR / 'data' / 'rede' / 'ESB01S4' / 'ESB01S4_evs.dss'

def obter_barras_baixa_tensao(caminho_dss: Path):
    """
    Compila o circuito e mapeia as barras de Baixa Tensão (BT) através da leitura
    das posições das cargas residenciais BT existentes (filtrando Média Tensão).
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
            
        # Filtra estritamente cargas residenciais de Baixa Tensão
        if not nome_carga.lower().startswith("bt_"):
            if not dss.loads.next():
                break
            continue

        dss.circuit.set_active_element(f"Load.{nome_carga}")
        
        bus_str = dss.cktelement.bus_names[0]
        base_bus = bus_str.split('.')[0]
        
        nos = bus_str.split('.')[1:]
        # Seleciona apenas nós de fase (1, 2, 3), excluindo o neutro (4) da seleção de fase
        fases = [n for n in nos if n in ['1', '2', '3']]
        if not fases:
            fases = ['1', '2', '3']
            
        dss.circuit.set_active_bus(base_bus)
        kv_base = dss.bus.kv_base
        
        # Ignora barras com tensão de média tensão (> 1 kV) por segurança
        if kv_base > 1.0:
            if not dss.loads.next():
                break
            continue
            
        # Tensão nominal monofásica Fase-Neutro no Ceará (220 V)
        kv_fn = 0.220
            
        barras_disponiveis.append({
            'bus': base_bus,
            'phases': fases,
            'kv': kv_fn
        })
        
        if not dss.loads.next():
            break
            
    logger.info(f"Mapeamento concluído: {len(barras_disponiveis)} locais de conexão BT identificados.")
    return barras_disponiveis

def criar_script_evs(qtd_evs: int, seed: int):
    random.seed(seed)
    
    barras = obter_barras_baixa_tensao(REDE_DSS)
    if not barras:
        raise RuntimeError("Nenhuma barra de Baixa Tensão identificada para alocação dos VEs.")
    
    # Prioriza os perfis diretamente do dataset Caldera para compatibilidade total
    if EV_SESSIONS_CSV.exists():
        logger.info(f"Lendo perfis de VEs do dataset Caldera: {EV_SESSIONS_CSV.name}")
        df_sessions = pd.read_csv(EV_SESSIONS_CSV)
        curvas_disponiveis = sorted(df_sessions["Profile_Name"].unique())
    else:
        logger.info(f"Lendo perfis de VEs: {EV_CSV.name}")
        df_evs = pd.read_csv(EV_CSV)
        curvas_disponiveis = [col for col in df_evs.columns if col.lower() not in ['date', 'time']]
    
    logger.info(f"Iniciando alocação estocástica de {qtd_evs} VEs Monofásicos BT (220V)...")
    ev_commands = []
    
    for i in range(1, qtd_evs + 1):
        curva_sorteada = random.choice(curvas_disponiveis)
        barra = random.choice(barras)
        
        no_fase = random.choice(barra['phases'])
        # Conexão monofásica fase-neutro (.fase.4) com a ddp de 220V
        bus_monofasico = f"{barra['bus']}.{no_fase}.4"
        
        # Reconhece 3.6kW ou 3p6kW
        potencia = 3.6 if ('3.6' in curva_sorteada or '3p6' in curva_sorteada) else 7.2
        kv_monofasico = barra['kv']
        
        nome_id = f"{curva_sorteada}_{i}"
        
        cmd = f"New Load.EV_{nome_id} Bus1={bus_monofasico} Phases=1 Conn=Wye kV={kv_monofasico:.3f} kW={potencia} pf=1.0 status=variable"
        ev_commands.append(cmd)
        
    with open(OUTPUT_DSS, 'w') as f:
        f.write(f"! Alocação estocástica de {qtd_evs} VEs monofásicos BT (Seed: {seed})\n")
        for cmd in ev_commands:
            f.write(cmd + "\n")
            
    logger.info(f"Arquivo exportado com sucesso para: {OUTPUT_DSS.name}")

if __name__ == "__main__":
    criar_script_evs(QtdEVs, SEED)
