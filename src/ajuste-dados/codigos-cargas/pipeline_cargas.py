#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script mestre para rodar o pipeline completo de geração estocástica de cargas.
Este script orquestra os 4 passos, mantendo os dataframes em memória 
(sem gravar CSVs intermediários no disco) e salvando apenas o resultado
final na pasta da rede e no CSV final.
"""

import sys
from pathlib import Path

# Adiciona o diretório atual ao sys.path para garantir os imports
sys.path.append(str(Path(__file__).parent))

import passo1_dss_para_csv_cargas as p1
import passo2_processar_telemetria_cargas as p2
import passo3_clusterizar_curvas as p3
import passo4_montar_semanas as p4

def rodar_pipeline_completo():
    print("="*80)
    print("🚀 INICIANDO PIPELINE DE GERAÇÃO ESTOCÁSTICA DE CARGAS")
    print("="*80)
    
    # ------------------------------------------------------------------
    # PASSO 1: BDGD
    # ------------------------------------------------------------------
    print("\n" + "-"*80)
    print("▶️ PASSO 1: Extração e Interpolação das Referências BDGD")
    print("-"*80)
    # Rodamos pedindo para não salvar CSV no disco
    df_ref = p1.executar_passo1(salvar_csv=False)
    
    if df_ref is None:
        print("❌ Falha no Passo 1. Abortando.")
        return

    # ------------------------------------------------------------------
    # PASSO 2: TELEMETRIA
    # ------------------------------------------------------------------
    print("\n" + "-"*80)
    print("▶️ PASSO 2: Separação e Processamento da Telemetria (DU, SA, DO)")
    print("-"*80)
    df_du, df_sa, df_do = p2.executar_passo2(salvar_csv=False)
    
    if df_du is None or df_du.empty:
        print("❌ Falha no Passo 2. Abortando.")
        return
        
    dfs_telemetria = {
        'DU': df_du,
        'SA': df_sa,
        'DO': df_do
    }

    # ------------------------------------------------------------------
    # PASSO 3: GALE-SHAPLEY
    # ------------------------------------------------------------------
    print("\n" + "-"*80)
    print("▶️ PASSO 3: Batalha de Alocação (Gale-Shapley)")
    print("-"*80)
    # Passamos os DataFrames diretamente da memória!
    df_agrupado = p3.executar_passo3(
        df_ref_completo=df_ref, 
        dfs_telemetria=dfs_telemetria, 
        salvar_csv=False
    )
    
    if df_agrupado is None or df_agrupado.empty:
        print("❌ Falha no Passo 3. Abortando.")
        return

    # ------------------------------------------------------------------
    # PASSO 4: SEMANAS SINTÉTICAS E DSS
    # ------------------------------------------------------------------
    print("\n" + "-"*80)
    print("▶️ PASSO 4: Geração Semanal Estocástica e Atualização OpenDSS")
    print("-"*80)
    # Este passo é o final, então ele SEMPRE salva no disco
    p4.executar_passo4(df_diario=df_agrupado)
    
    print("\n" + "="*80)
    print("✅ PIPELINE CONCLUÍDO COM SUCESSO! A rede do OpenDSS está atualizada.")
    print("="*80)

if __name__ == '__main__':
    rodar_pipeline_completo()
