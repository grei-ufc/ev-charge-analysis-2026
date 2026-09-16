import pandas as pd
import numpy as np
from pathlib import Path
from scipy.spatial.distance import cdist
from collections import deque

def alocar_gale_shapley(df_telemetria_pu, df_ref, vagas_maximas):
    X = df_telemetria_pu.T.values
    Y = df_ref.T.values
    nomes_ref = df_ref.columns.tolist()
    nomes_tel = df_telemetria_pu.columns.tolist()
    
    dist_euclidiana = cdist(X, Y, metric='euclidean')
    rmse = dist_euclidiana / np.sqrt(X.shape[1])
    similaridades = 1.0 - rmse
    
    preferencias = {}
    for i, t_nome in enumerate(nomes_tel):
        prefs = []
        for j, r_nome in enumerate(nomes_ref):
            sim = similaridades[i, j]
            prefs.append((sim, r_nome))
                
        prefs.sort(key=lambda x: x[0], reverse=True)
        preferencias[t_nome] = {
            'lista': prefs,
            'index_atual': 0
        }
        
    fila = deque(nomes_tel)
    baldes = {r_nome: [] for r_nome in nomes_ref}
    
    while fila:
        t_nome = fila.popleft()
        pref = preferencias[t_nome]
        
        if pref['index_atual'] >= len(pref['lista']):
            continue
            
        sim_atual, r_alvo = pref['lista'][pref['index_atual']]
        pref['index_atual'] += 1 
        
        balde = baldes[r_alvo]
        
        if len(balde) < vagas_maximas:
            balde.append((sim_atual, t_nome))
            balde.sort(key=lambda x: x[0])
        else:
            pior_sim, pior_t_nome = balde[0]
            if sim_atual > pior_sim:
                balde.pop(0)
                balde.append((sim_atual, t_nome))
                balde.sort(key=lambda x: x[0])
                fila.append(pior_t_nome)
            else:
                fila.append(t_nome)
                
    return baldes

def processar_tipo_dia(tipo, df_tel, df_ref_completo, vagas_maximas):
    if df_tel is None or df_tel.empty:
        print(f"⚠️ Aviso: Dataset de telemetria não fornecido. Ignorando tipo {tipo}.")
        return pd.DataFrame(), []
        
    print(f"\n[{tipo}] Processando {len(df_tel.columns)} curvas na memória...")
    
    df_ref = df_ref_completo.filter(regex=f".*_{tipo}$")
    
    print(f"[{tipo}] Normalizando as {len(df_tel.columns)} curvas do medidor para P.U...")
    df_tel_pu = df_tel.copy()
    for col in df_tel_pu.columns:
        max_val = df_tel_pu[col].max()
        df_tel_pu[col] = 0.0 if max_val == 0 or pd.isna(max_val) else df_tel_pu[col] / max_val
        
    print(f"[{tipo}] Iniciando a Batalha de Alocação (SEM LIMIAR, Vagas: {vagas_maximas})...")
    baldes = alocar_gale_shapley(df_tel_pu, df_ref, vagas_maximas)
    
    colunas_finais = {}
    todas_similaridades = []
    
    for aprovados in baldes.values():
        for sim, _ in aprovados:
            todas_similaridades.append(sim)
            
    print(f"\n[{tipo}] 📊 Relatório Específico por Curva de Referência:")
    for r_nome, aprovados in baldes.items():
        if len(aprovados) > 0:
            pior_sim = aprovados[0][0]
            print(f"   -> {r_nome:<20} | Alocadas: {len(aprovados):02d}/{vagas_maximas} | Menor Similaridade Aceita: {pior_sim:.1%}")
        else:
            print(f"   -> {r_nome:<20} | Alocadas: 00/{vagas_maximas} | Menor Similaridade Aceita: N/A")
            
        aprovados.sort(key=lambda x: x[0], reverse=True)
        for idx, (sim, t_nome) in enumerate(aprovados):
            novo_nome = f"{r_nome}-{idx+1}"
            colunas_finais[novo_nome] = df_tel_pu[t_nome]
            
    df_agrupado = pd.DataFrame(colunas_finais)
    print(f"\n[{tipo}] Concluído! {len(df_agrupado.columns)} curvas conseguiram vaga nas {len(df_ref.columns)} referências {tipo}.")
    return df_agrupado, todas_similaridades

def executar_passo3(df_ref_completo=None, dfs_telemetria=None, salvar_csv=True):
    base_dir = Path(__file__).resolve().parents[3]
    pasta_datasets = base_dir / "data" / "datasets" / "curvas-de-carga"
    arquivo_ref = pasta_datasets / "CurvaCarga_referencia_diaria.csv"
    arquivo_saida = pasta_datasets / "Curvas_Agrupadas_Supervisionado_Diario.csv"

    if df_ref_completo is None:
        if not arquivo_ref.exists():
            print(f"❌ Erro: Arquivo de referência {arquivo_ref.name} não encontrado.")
            return None
        print(f"📥 Carregando matriz de referência com 108 grupos: {arquivo_ref.name}")
        df_ref_completo = pd.read_csv(arquivo_ref, index_col='index')

    if dfs_telemetria is None:
        dfs_telemetria = {}
        for t in ['DU', 'SA', 'DO']:
            p = pasta_datasets / f"Telemetria_{t}.csv"
            if p.exists():
                dfs_telemetria[t] = pd.read_csv(p, index_col='index')
            else:
                dfs_telemetria[t] = None

    tipos_dia = ['DU', 'SA', 'DO']
    dfs_processados = []
    similaridades_globais = []

    for tipo in tipos_dia:
        vagas_atuais = 10 if tipo == 'DU' else 5
        df_tel = dfs_telemetria.get(tipo)
        df_agrupado, sims_tipo = processar_tipo_dia(tipo, df_tel, df_ref_completo, vagas_atuais)
        if not df_agrupado.empty:
            dfs_processados.append(df_agrupado)
            similaridades_globais.extend(sims_tipo)

    if dfs_processados:
        print("\n📝 Unindo todos os DataFrames (DU, SA, DO) num único arquivo final...")
        df_final = pd.concat(dfs_processados, axis=1)
        def chave_ordenacao(nome):
            partes = nome.rsplit('-', 1)
            return (partes[0], int(partes[1]))
        df_final = df_final.reindex(sorted(df_final.columns, key=chave_ordenacao), axis=1)
        
        if salvar_csv:
            df_final.to_csv(arquivo_saida, index=True, index_label='index')
            print("="*80)
            print("🎉 RELATÓRIO GLOBAL DE ALOCAÇÃO")
            print("="*80)
            print(f"💾 Dataset salvo em:\n   -> {arquivo_saida}")
            print(f"📊 Total de curvas aprovadas globalmente: {len(df_final.columns)}")
            
            if similaridades_globais:
                media = np.mean(similaridades_globais)
                mediana = np.median(similaridades_globais)
                maxima = np.max(similaridades_globais)
                minima = np.min(similaridades_globais)
                std = np.std(similaridades_globais)
                print("-" * 80)
                print("📈 ESTATÍSTICAS GERAIS (Todas as curvas alocadas, todos os dias):")
                print(f"   -> Similaridade Média:  {media:.1%}")
                print(f"   -> Mediana:             {mediana:.1%}")
                print(f"   -> Máxima: {maxima:.1%} | Mínima: {minima:.1%}")
                print(f"   -> Desvio Padrão:       {std:.1%}")
            print("="*80)
        return df_final
    return None

def main():
    executar_passo3(salvar_csv=True)

if __name__ == '__main__':
    main()
