import pandas as pd
import time
from pathlib import Path

# Importação dos módulos construídos em etapas
from passo1_limpeza_dados_ev import RAW_CSV_PATH, OUTPUT_DIR, limpar_dados_ev
from passo2_filtragem_setembro_ev import filtrar_semanas_setembro
from passo3_agrupamento_semanal_ev import agrupar_sessoes_por_usuario_e_semana
from passo4_geracao_curvas_ev import gerar_curvas_ev

def rodar_pipeline_completo():
    print("="*60)
    print("      ORQUESTRADOR DE VEÍCULOS ELÉTRICOS (TCC)")
    print("="*60)
    
    start_time = time.time()
    
    # ---------------------------------------------------------
    # PASSO 1: Leitura e Limpeza Inicial
    # ---------------------------------------------------------
    print("\n[1/4] Inicializando limpeza e formatação de dados...")
    # O orquestrador usa manter_todas_colunas=False para não pesar a memória
    df_p1 = limpar_dados_ev(RAW_CSV_PATH, manter_todas_colunas=False)
    
    # ---------------------------------------------------------
    # PASSO 2: Isolamento de Setembro + Time Shift BR
    # ---------------------------------------------------------
    print("\n[2/4] Aplicando Time-Shift BR e filtrando semanas lindeiras...")
    df_p2 = filtrar_semanas_setembro(df_p1)
    
    # ---------------------------------------------------------
    # PASSO 3: Agrupamento em Dicionários
    # ---------------------------------------------------------
    print("\n[3/4] Agrupando sessões intactas por ID de usuário e Semana...")
    dict_p3 = agrupar_sessoes_por_usuario_e_semana(df_p2)
    
    # ---------------------------------------------------------
    # PASSO 4: Motor Físico de Potência
    # ---------------------------------------------------------
    print("\n[4/4] Processando modelo de carga (Resample 1min -> 10min)...")
    curvas_finais = gerar_curvas_ev(dict_p3)
    
    # ---------------------------------------------------------
    # EXPORTAÇÃO
    # ---------------------------------------------------------
    print("\n[+] Consolidando e exportando CSV final...")
    df_opendss = pd.DataFrame(curvas_finais)
    
    # Adiciona a coluna de tempo exigida pelo simulador do Mosaik
    datas = pd.date_range(start="2026-01-01 00:00:00", periods=len(df_opendss), freq="10min")
    df_opendss.insert(0, "Date", datas)
    
    caminho_csv = OUTPUT_DIR / "ev_loadshapes_normalized.csv"
    df_opendss.to_csv(caminho_csv, index=False)
    
    end_time = time.time()
    
    print("="*60)
    print(f"✅ PIPELINE CONCLUÍDO COM SUCESSO! Tempo: {(end_time - start_time):.2f} segundos.")
    print(f"📊 Arquivo mestre disponível em: {caminho_csv.name}")
    print("="*60)

if __name__ == "__main__":
    rodar_pipeline_completo()
