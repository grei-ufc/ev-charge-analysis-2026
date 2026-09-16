import pandas as pd
import numpy as np
import os
from pathlib import Path
import argparse

def processar_dataset(pasta_dados: Path, pasta_saida: Path = None, salvar_csv: bool = True):
    arquivos = list(pasta_dados.glob("*.csv"))
    if not arquivos:
        print(f"❌ Nenhum arquivo CSV encontrado na pasta: {pasta_dados}")
        return
        
    print(f"🔍 Encontrados {len(arquivos)} arquivos CSV de telemetria.")
    
    # ---------------------------------------------------------
    # 1. Carregamento e Unificação do Dataset
    # ---------------------------------------------------------
    dfs = []
    print("\n⏳ Lendo arquivos individuais e convertendo Timezone...")
    for arquivo in arquivos:
        casa_nome = arquivo.stem
        try:
            df_temp = pd.read_csv(arquivo)
            # Verifica a coluna principal da telemetria australiana
            col_energia = [c for c in df_temp.columns if 'load power' in c.lower()]
            if not col_energia:
                continue
            
            df_casa = df_temp[['original index', col_energia[0]]].copy()
            df_casa.rename(columns={col_energia[0]: casa_nome, 'original index': 'timestamp'}, inplace=True)
            
            # Converte Epoch para Datetime, focando no fuso da Austrália/Canberra
            df_casa['timestamp'] = pd.to_datetime(df_casa['timestamp'], unit='s', utc=True)
            df_casa['timestamp'] = df_casa['timestamp'].dt.tz_convert('Australia/Canberra')
            
            df_casa.set_index('timestamp', inplace=True)
            dfs.append(df_casa)
        except Exception as e:
            print(f"   -> Erro ao ler {casa_nome}: {e}")
            
    print("🧩 Juntando todos os dados em um único DataFrame gigante...")
    df_completo = pd.concat(dfs, axis=1)
    
    # ---------------------------------------------------------
    # 2. Alinhamento de Início e Resample (10 Minutos)
    # ---------------------------------------------------------
    print("\n⏱️ Calculando alinhamento perfeito de início...")
    latest_start = df_completo.apply(lambda col: col.first_valid_index()).max()
    
    # Arredonda para a PRÓXIMA meia-noite (00:00) para garantir que o primeiro dia esteja completo
    start_aligned = latest_start.ceil('D')
    print(f"   -> O primeiro momento seguro com todos os medidores online é: {start_aligned}")
    
    df_alinhado = df_completo.loc[start_aligned:]
    
    print("📊 Agrupando os ruídos de rede (resample) para blocos cravados de 10 minutos...")
    df_resampled = df_alinhado.resample('10min').mean()
    
    # ---------------------------------------------------------
    # 3. Segmentação em Dias (DU, SA, DO) e Filtro de Qualidade
    # ---------------------------------------------------------
    print("\n🔪 Fatiando a linha do tempo em dias (144 pontos de 10min) e categorizando...")
    pontos_por_dia = 144
    total_pontos = len(df_resampled)
    dias_completos = total_pontos // pontos_por_dia
    
    df_resampled = df_resampled.iloc[:dias_completos * pontos_por_dia]
    
    curvas_DU = {}
    curvas_SA = {}
    curvas_DO = {}
    
    # Rastreadores de nomeclatura (Ex: casa_01-1, casa_01-2)
    contadores = {'DU': {}, 'SA': {}, 'DO': {}}
    for casa in df_resampled.columns:
        contadores['DU'][casa] = 1
        contadores['SA'][casa] = 1
        contadores['DO'][casa] = 1
        
    for casa in df_resampled.columns:
        serie_casa = df_resampled[casa]
        
        for i in range(dias_completos):
            inicio = i * pontos_por_dia
            fim = (i + 1) * pontos_por_dia
            pedaço = serie_casa.iloc[inicio:fim]
            
            dia_semana = pedaço.index[0].dayofweek # 0=Seg, ..., 4=Sex, 5=Sab, 6=Dom
            valores = pedaço.values
            
            # FILTRO DE QUALIDADE: Descarta dias com buracos (NaN) ou falhas de medidor (< 0)
            if pd.isna(valores).any() or (valores < 0).any():
                continue
                
            if dia_semana <= 4:
                tipo = 'DU'
                dict_alvo = curvas_DU
            elif dia_semana == 5:
                tipo = 'SA'
                dict_alvo = curvas_SA
            else:
                tipo = 'DO'
                dict_alvo = curvas_DO
                
            num_atual = contadores[tipo][casa]
            nome_col = f"{casa}-{num_atual}"
            dict_alvo[nome_col] = valores
            contadores[tipo][casa] += 1
            
    # Cria os 3 DataFrames resultantes (os índices agora são de 0 a 143 automaticamente)
    df_DU = pd.DataFrame(curvas_DU)
    df_SA = pd.DataFrame(curvas_SA)
    df_DO = pd.DataFrame(curvas_DO)
    
    # ---------------------------------------------------------
    # 4. Salvar os CSVs Resultantes
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("🔍 VISUALIZAÇÃO FINAL: DATASETS DIÁRIOS IMACULADOS (Índice 0 a 143)")
    print("="*80)
    print(f"📊 Dias Úteis (DU) : {df_DU.shape[1]} curvas salvas.")
    print(f"📊 Sábados (SA)    : {df_SA.shape[1]} curvas salvas.")
    print(f"📊 Domingos (DO)   : {df_DO.shape[1]} curvas salvas.")
    print("="*80 + "\n")
    
    if pasta_saida and salvar_csv:
        pasta_saida.mkdir(parents=True, exist_ok=True)
        
        caminho_du = pasta_saida / "Telemetria_DU.csv"
        caminho_sa = pasta_saida / "Telemetria_SA.csv"
        caminho_do = pasta_saida / "Telemetria_DO.csv"
        
        df_DU.to_csv(caminho_du, index=True, index_label='index')
        df_SA.to_csv(caminho_sa, index=True, index_label='index')
        df_DO.to_csv(caminho_do, index=True, index_label='index')
        
        print(f"💾 Sucesso! Foram salvos 3 arquivos em:\n   -> {pasta_saida}")
        
    return df_DU, df_SA, df_DO

def executar_passo2(salvar_csv=True):
    base_dir = Path(__file__).resolve().parents[3]
    pasta_entrada = Path("/mnt/c/Users/pvict/OneDrive/TCC/dados/dados-das-cargas")
    pasta_saida = base_dir / "data" / "datasets" / "curvas-de-carga"
    return processar_dataset(pasta_entrada, pasta_saida, salvar_csv)

def main():
    base_dir = Path(__file__).resolve().parents[3]
    pasta_entrada_padrao = Path("/mnt/c/Users/pvict/OneDrive/TCC/dados/dados-das-cargas")
    pasta_saida_padrao = base_dir / "data" / "datasets" / "curvas-de-carga"
    
    parser = argparse.ArgumentParser(description="Processa telemetria e fatia em DU, SA e DO.")
    parser.add_argument("--pasta", "-p", type=Path, default=pasta_entrada_padrao, help="Pasta contendo os CSVs originais")
    parser.add_argument("--saida", "-o", type=Path, default=pasta_saida_padrao, help="Pasta para salvar os CSVs (DU, SA, DO)")
    
    args = parser.parse_args()
    processar_dataset(args.pasta, args.saida)

if __name__ == '__main__':
    main()
