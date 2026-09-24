import pandas as pd
import numpy as np
from pathlib import Path

# Importa o pipeline anterior
from passo1_limpeza_dados_ev import RAW_CSV_PATH, PROJECT_ROOT, OUTPUT_DIR, limpar_dados_ev
from passo2_filtragem_setembro_ev import filtrar_semanas_setembro
from passo3_agrupamento_semanal_ev import agrupar_sessoes_por_usuario_e_semana

def criar_malha_de_potencia(df_semana: pd.DataFrame, potencia_carregador_kw: float) -> np.ndarray:
    """
    Transforma as sessões de recarga numa malha fina de 1 MINUTO (10080 pontos).
    Usa a Lógica de Carga Imediata na potência nominal até suprir o 'El_kWh'.
    Ao final, aplica o RESAMPLE (média) para 10 minutos (1008 pontos) e NORMALIZA.
    """
    # Malha de 1 minuto (7 dias x 24h x 60 min = 10080 posições)
    malha_1min = np.zeros(10080)
    energia_max_por_minuto = potencia_carregador_kw * (1.0 / 60.0) # kWh que cabem em 1 min
    
    for _, row in df_semana.iterrows():
        energia_restante = row['El_kWh']
        if energia_restante <= 0:
            continue
            
        start_time = row['Start_plugin']
        
        # Encontra o minuto exato da semana (Segunda 00:00 = Minuto 0)
        segunda_meia_noite = start_time.floor('D') - pd.to_timedelta(start_time.weekday(), unit='D')
        minutos_desde_segunda = (start_time - segunda_meia_noite).total_seconds() / 60.0
        
        # Como a malha é de 1 minuto, o índice do bin é literalmente o minuto corrido!
        bin_atual = int(minutos_desde_segunda)
        
        # Preenche a malha de minuto em minuto
        while energia_restante > 0 and bin_atual < 10080:
            if energia_restante >= energia_max_por_minuto:
                malha_1min[bin_atual] += potencia_carregador_kw
                energia_restante -= energia_max_por_minuto
            else:
                potencia_fracionada = energia_restante / (1.0 / 60.0)
                malha_1min[bin_atual] += potencia_fracionada
                energia_restante = 0
                
            bin_atual += 1
            
    # --- RESAMPLE PARA 10 MINUTOS ---
    # Quebra o vetor de 10080 em blocos de 10, e tira a potência média de cada bloco
    # O resultado será nosso vetor final de 1008 pontos!
    malha_10min = malha_1min.reshape(-1, 10).mean(axis=1)
            
    # --- NORMALIZAÇÃO PELA POTÊNCIA NOMINAL ---
    # Divide pela capacidade do carregador em vez do pico encontrado.
    # Isso fará com que cargas normais fiquem em 1.0, e sobreposições (overlaps) ultrapassem 1.0 (ex: 2.0).
    if potencia_carregador_kw > 0:
        malha_10min = malha_10min / potencia_carregador_kw
        
    return malha_10min

def gerar_curvas_ev(dict_agrupado: dict) -> dict:
    """
    Varre o dicionário do Passo 3 e gera as curvas para 3.6 kW e 7.2 kW.
    Retorna um dicionário com os arrays já modelados e normalizados.
    """
    print("Gerando curvas de carga (10 min) para 3.6 kW e 7.2 kW...")
    dict_curvas = {}
    potencias_estudo = [3.6, 7.2]
    
    # Prepara dicionário linearizado para facilitar exportação e leitura
    for user_id, semanas in dict_agrupado.items():
        for week_label, df_semana in semanas.items():
            for p_kw in potencias_estudo:
                # Gera a chave no formato ex: "User1_semana_1_3.6kW"
                nome_curva = f"{user_id}_{week_label}_{p_kw}kW".replace('.', 'p')
                
                array_normalizado = criar_malha_de_potencia(df_semana, p_kw)
                dict_curvas[nome_curva] = array_normalizado
                
    print(f"-> {len(dict_curvas)} curvas exclusivas geradas.")
    return dict_curvas

if __name__ == "__main__":
    print("Execução Individual Detectada (Passo 4)...")
    
    # 1. Roda a pipeline inteira na RAM
    df_p1 = limpar_dados_ev(RAW_CSV_PATH)
    df_p2 = filtrar_semanas_setembro(df_p1)
    dict_p3 = agrupar_sessoes_por_usuario_e_semana(df_p2)
    
    # 2. Gera as matrizes do Passo 4
    curvas = gerar_curvas_ev(dict_p3)
    
    # 3. EXPORTAÇÃO (Apenas CSV)
    # Cria um único DataFrame onde cada coluna é a curva de um VE
    df_opendss = pd.DataFrame(curvas)
    
    # Adiciona a coluna de tempo exigida pelo simulador do Mosaik
    datas = pd.date_range(start="2026-01-01 00:00:00", periods=len(df_opendss), freq="10min")
    df_opendss.insert(0, "Date", datas)
    
    caminho_csv = OUTPUT_DIR / "ev_loadshapes_normalized.csv"
    df_opendss.to_csv(caminho_csv, index=False)
    
    print(f"✅ Curvas CSV geradas em: {caminho_csv.relative_to(PROJECT_ROOT)}")
