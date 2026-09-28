import pandas as pd
import time
from pathlib import Path

# Importação dos módulos construídos em etapas
from passo1_limpeza_dados_ev import RAW_CSV_PATH, OUTPUT_DIR, limpar_dados_ev
from passo2_filtragem_setembro_ev import filtrar_semanas_setembro
from passo3_agrupamento_semanal_ev import agrupar_sessoes_por_usuario_e_semana
from passo4_geracao_sessoes_ev import gerar_csv_sessoes_ev

def rodar_pipeline_completo():
    print("="*60)
    print("      ORQUESTRADOR DE VEÍCULOS ELÉTRICOS (CALDERA ICM)")
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
    # PASSO 4: Motor Físico (Eventos, SoC e t_idle)
    # ---------------------------------------------------------
    print("\n[4/4] Processando modelo FÍSICO (Extração de SoC Inicial e Tapering)...")
    df_eventos = gerar_csv_sessoes_ev(dict_p3)
    
    # ---------------------------------------------------------
    # EXPORTAÇÃO
    # ---------------------------------------------------------
    print("\n[+] Consolidando e exportando CSV final de Eventos...")
    
    caminho_csv = OUTPUT_DIR / "ev_sessions_caldera.csv"
    df_eventos.to_csv(caminho_csv, index=False)
    
    end_time = time.time()
    
    print("="*60)
    print(f"✅ PIPELINE FÍSICO CONCLUÍDO COM SUCESSO! Tempo: {(end_time - start_time):.2f} segundos.")
    print(f"📊 Arquivo mestre de Eventos disponível em: {caminho_csv.name}")
    print("="*60)

if __name__ == "__main__":
    rodar_pipeline_completo()
