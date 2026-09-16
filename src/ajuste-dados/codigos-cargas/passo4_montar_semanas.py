import pandas as pd
import numpy as np
import random
import re
from pathlib import Path

def suavizar_emendas(curva_semanal, pontos_por_dia=144, janela=4):
    """
    Aplica a interpolação PCHIP nas emendas (meia-noite) para evitar descontinuidades.
    """
    s = pd.Series(curva_semanal.copy())
    for dia in range(1, 7):
        corte = dia * pontos_por_dia
        idx_inicio = corte - (janela // 2)
        idx_fim = corte + (janela // 2)
        s.iloc[idx_inicio:idx_fim] = np.nan
        
    s_suave = s.interpolate(method='pchip')
    return s_suave.clip(lower=0.0).values

def gerar_semana_para_tipo(tipo, df_diario):
    cols_du = [c for c in df_diario.columns if c.startswith(f"{tipo}_DU-")]
    cols_sa = [c for c in df_diario.columns if c.startswith(f"{tipo}_SA-")]
    cols_do = [c for c in df_diario.columns if c.startswith(f"{tipo}_DO-")]
    
    if not cols_du or not cols_sa or not cols_do:
        return None
        
    if len(cols_du) >= 5:
        escolhas_du = random.sample(cols_du, k=5)
    else:
        escolhas_du = list(cols_du)
        escolhas_du += random.choices(cols_du, k=(5 - len(cols_du)))
        random.shuffle(escolhas_du)
        
    escolha_sa = random.choice(cols_sa)
    escolha_do = random.choice(cols_do)
    
    pedacos = [df_diario[c].values for c in escolhas_du]
    pedacos.append(df_diario[escolha_sa].values)
    pedacos.append(df_diario[escolha_do].values)
    
    semana_completa = np.concatenate(pedacos)
    semana_completa = suavizar_emendas(semana_completa)
    
    return semana_completa

def processar_dss_cargas(dss_in_path, dss_out_path, df_diario, dict_curves, missing_types):
    if not dss_in_path.exists():
        print(f"⚠️ Aviso: Arquivo de carga não encontrado {dss_in_path}")
        return

    with open(dss_in_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    # Busca por `New Load.X ... daily=Y`
    pattern = re.compile(r'(?i)(New\s+"?Load\.([\w_]+)"?.*?daily\s*=\s*)("?[\w\-]+"?)')
    
    count_sucesso = 0
    count_falha = 0
    
    for line in lines:
        match = pattern.search(line)
        if match:
            load_name = match.group(2)
            original_daily_quoted = match.group(3)
            original_daily = original_daily_quoted.replace('"', '').replace("'", "")
            
            # Gera nome único para o novo Loadshape
            novo_loadshape_name = f"LS_{load_name}"
            
            semana = gerar_semana_para_tipo(original_daily, df_diario)
            if semana is not None:
                dict_curves[novo_loadshape_name] = semana
                # Atualiza a linha do dss trocando daily=Tipo antigo por daily=Novo_Loadshape
                nova_linha = line[:match.start(3)] + f'"{novo_loadshape_name}"' + line[match.end(3):]
                out_lines.append(nova_linha)
                count_sucesso += 1
            else:
                missing_types.add(original_daily)
                out_lines.append(line)
                count_falha += 1
        else:
            out_lines.append(line)
            
    with open(dss_out_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
        
    print(f"   -> {dss_in_path.name}: {count_sucesso} curvas únicas geradas. {count_falha} mantidas originais.")

def executar_passo4(df_diario=None):
    base_dir = Path(__file__).resolve().parents[3]
    pasta_datasets = base_dir / "data" / "datasets" / "curvas-de-carga"
    pasta_rede = base_dir / "data" / "rede" / "ESB01S4"
    
    arquivo_entrada_diario = pasta_datasets / "Curvas_Agrupadas_Supervisionado_Diario.csv"
    arquivo_saida_csv = pasta_datasets / "Curvas_Semanas_Sinteticas.csv"
    
    # Arquivos DSS originais
    dss_cargas_bt = pasta_rede / "CargasBT_20250139_ESB01S4.dss"
    dss_cargas_mt = pasta_rede / "CargasMT_20250139_ESB01S4.dss"
    
    # Arquivos DSS de saída
    dss_cargas_bt_sint = pasta_rede / "CargasBT_Sintetico_20250139_ESB01S4.dss"
    dss_cargas_mt_sint = pasta_rede / "CargasMT_Sintetico_20250139_ESB01S4.dss"
    dss_loadshapes_sint = pasta_rede / "CurvaCarga_Sintetica_20250139_ESB01S4.dss"
    
    if df_diario is None:
        if not arquivo_entrada_diario.exists():
            print(f"❌ Erro: O dataset diário não foi encontrado em {arquivo_entrada_diario}")
            return
        print(f"📥 Carregando dataset de blocos diários: {arquivo_entrada_diario.name}...")
        df_diario = pd.read_csv(arquivo_entrada_diario, index_col='index')
    
    dict_curves = {}
    missing_types = set()
    
    print("\n⚙️ Processando Arquivos DSS e mapeando cargas...")
    processar_dss_cargas(dss_cargas_bt, dss_cargas_bt_sint, df_diario, dict_curves, missing_types)
    processar_dss_cargas(dss_cargas_mt, dss_cargas_mt_sint, df_diario, dict_curves, missing_types)
    
    if missing_types:
        print(f"\n⚠️ Aviso: Não foram encontradas curvas diárias suficientes para os tipos: {', '.join(missing_types)}")
        
    if not dict_curves:
        print("\n❌ Nenhuma curva sintética foi gerada!")
        return
        
    print(f"\n💾 Salvando {len(dict_curves)} Loadshapes únicos em {dss_loadshapes_sint.name}...")
    with open(dss_loadshapes_sint, 'w', encoding='utf-8') as f:
        f.write("! Arquivo gerado automaticamente - Curvas Sinteticas 168h\n\n")
        for ls_name, curve_array in dict_curves.items():
            # Limita a 5 casas decimais para poupar espaço no DSS
            mult_str = f"({', '.join(f'{x:.5f}' for x in curve_array)})"
            f.write(f"New Loadshape.{ls_name} npts=1008 minterval=10 mult={mult_str}\n")
            
    print(f"💾 Salvando DataFrame completo no CSV {arquivo_saida_csv.name}...")
    df_out = pd.DataFrame(dict_curves)
    # Natural sort nas colunas (opcional mas bom para a leitura do CSV)
    def chave_ordenacao(nome):
        # LS_BT_U52513810_M1 -> ignoramos "LS_" e tentamos ordernar pelo final se tiver numero
        partes = nome.split('_')
        return nome
        
    df_out = df_out.reindex(sorted(df_out.columns, key=chave_ordenacao), axis=1)
    df_out.to_csv(arquivo_saida_csv, index=True, index_label='index')
    
    print("\n" + "="*80)
    print("🎉 RELATÓRIO DO GERADOR SINTÉTICO INDIVIDUALIZADO")
    print("="*80)
    print(f"📈 Total de Cargas Individualizadas: {len(dict_curves)}")
    print(f"📂 Arquivos Gerados na pasta da rede ({pasta_rede.name}):")
    print(f"   -> {dss_cargas_bt_sint.name}")
    print(f"   -> {dss_cargas_mt_sint.name}")
    print(f"   -> {dss_loadshapes_sint.name}")
    print(f"📂 Dataset CSV Analítico atualizado:")
    print(f"   -> {arquivo_saida_csv.name}")
    print("="*80)

def main():
    executar_passo4()

if __name__ == '__main__':
    main()
