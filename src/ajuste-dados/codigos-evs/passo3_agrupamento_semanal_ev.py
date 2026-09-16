import pandas as pd
from pathlib import Path
import sys

# Importa o pipeline anterior para teste individual
from passo1_limpeza_dados_ev import limpar_dados_ev, RAW_CSV_PATH, PROJECT_ROOT, OUTPUT_DIR
from passo2_filtragem_setembro_ev import filtrar_semanas_setembro

def agrupar_sessoes_por_usuario_e_semana(df: pd.DataFrame) -> dict:
    """
    Recebe o DataFrame filtrado do Passo 2 e o estrutura em um dicionário aninhado:
    {
        'User_ID_1': {
            'Semana_2018-09-03': DataFrame_com_as_sessoes,
            'Semana_2018-09-10': DataFrame_com_as_sessoes,
            ...
        },
        'User_ID_2': ...
    }
    Garante a integridade das sessões roteando-as inteiras baseado no Start_plugin.
    """
    print("Agrupando dados por Usuário e por Semana...")
    
    # 1. Cria a tag da semana baseada na Segunda-Feira correspondente ao Start_plugin
    # Isso respeita perfeitamente a regra do Passo 2 (onde as sessões pertencem à semana de início)
    df = df.copy()
    # Pega apenas a DATA (sem hora) para garantir que todas as sessões da mesma semana tenham exatamente a mesma chave
    df['Date_Only'] = df['Start_plugin'].dt.floor('D')
    df['Monday_Date'] = df['Date_Only'] - pd.to_timedelta(df['Date_Only'].dt.weekday, unit='D')
    
    # Cria um índice contínuo (1, 2, 3, 4) PARA CADA USUÁRIO
    # Assim, o primeiro registro semanal de cada usuário será sempre 'semana_1', independente da data global
    df['Indice_Semana'] = df.groupby('User_ID')['Monday_Date'].rank(method='dense').astype(int)
    df['Week_Label'] = 'semana_' + df['Indice_Semana'].astype(str)
    
    # 2. Constrói o dicionário aninhado
    dict_agrupado = {}
    
    # Agrupa primeiro por usuário
    for user_id, df_user in df.groupby('User_ID'):
        dict_semanas = {}
        
        # Agrupa internamente por semana
        for week_label, df_week in df_user.groupby('Week_Label'):
            # Removemos as colunas de marcação temporária para o DataFrame final ficar limpo
            df_limpo_semana = df_week.drop(columns=['Date_Only', 'Monday_Date', 'Indice_Semana', 'Week_Label']).copy()
            # Reordena o index para ficar 0, 1, 2... dentro daquela semana
            df_limpo_semana = df_limpo_semana.reset_index(drop=True)
            
            dict_semanas[week_label] = df_limpo_semana
            
        dict_agrupado[user_id] = dict_semanas
        
    print(f"-> {len(dict_agrupado)} usuários estruturados em dicionários semanais.")
    
    return dict_agrupado

def achatar_dicionario_para_csv(dict_agrupado: dict) -> pd.DataFrame:
    """
    Função auxiliar apenas para poder exportar o dicionário aninhado em um CSV legível
    quando o código for rodado de forma individual.
    """
    lista_dfs = []
    for user_id, semanas in dict_agrupado.items():
        for week_label, df_week in semanas.items():
            df_temp = df_week.copy()
            df_temp.insert(0, 'Identificador_Semana', week_label)
            lista_dfs.append(df_temp)
            
    df_final = pd.concat(lista_dfs, ignore_index=True)
    # Garante a ordenação absoluta por Usuário, depois por Semana (1 a 4), e cronologicamente
    return df_final.sort_values(by=['User_ID', 'Identificador_Semana', 'Start_plugin']).reset_index(drop=True)


if __name__ == "__main__":
    print("Execução Individual Detectada (Passo 3)...")
    
    # Pipeline RAM
    df_p1 = limpar_dados_ev(RAW_CSV_PATH)
    df_p2 = filtrar_semanas_setembro(df_p1)
    
    # Executa o Passo 3
    dicionario_ve = agrupar_sessoes_por_usuario_e_semana(df_p2)
    
    # Para salvar no disco, achatamos o dicionário devolta pra tabela com a tag da semana
    df_export = achatar_dicionario_para_csv(dicionario_ve)
    
    caminho_saida = OUTPUT_DIR / "sessoes_ve_agrupadas.csv"
    df_export.to_csv(caminho_saida, index=False)
    
    print(f"✅ Arquivo agrupado exportado com sucesso em: {caminho_saida.relative_to(PROJECT_ROOT)}")
