import pandas as pd
from pathlib import Path
import sys

# Importa a função do passo 1 para quando for testar individualmente
from passo1_limpeza_dados_ev import limpar_dados_ev, RAW_CSV_PATH, PROJECT_ROOT, OUTPUT_DIR

def filtrar_semanas_setembro(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra as sessões para cobrir todas as semanas que tocam no mês de Setembro.
    Garante que o recorte comece exatamente na segunda-feira da primeira semana 
    de setembro e termine no domingo da última semana de setembro, englobando
    alguns dias de agosto ou outubro se necessário para manter as semanas completas.
    """
    print("Aplicando Time-Shifting (+2.5 horas) para adaptação Noruega -> Brasil...")
    # O expediente na Noruega acaba às 16h, no Brasil às 18h.
    # Adicionamos 2.5h (expediente + trânsito) para que o pico coincida perfeitamente 
    # com a ponta do sistema de distribuição brasileiro (18h30-19h).
    df['Start_plugin'] = df['Start_plugin'] + pd.Timedelta(hours=2.5)
    df['End_plugout'] = df['End_plugout'] + pd.Timedelta(hours=2.5)
    
    # Identifica os anos presentes nos dados que possuem o mês de setembro (mês 9)
    df_sep = df[df['Start_plugin'].dt.month == 9]
    if df_sep.empty:
        print("Aviso: Nenhuma sessão do mês de Setembro encontrada no dataset!")
        return df.iloc[0:0]
    
    anos_com_setembro = df_sep['Start_plugin'].dt.year.unique()
    
    df_filtrado = pd.DataFrame()
    total_semanas = 0
    print("Mapeando semanas que englobam Setembro:")
    
    for ano in anos_com_setembro:
        primeiro_dia_set = pd.Timestamp(ano, 9, 1)
        ultimo_dia_set = pd.Timestamp(ano, 9, 30)
        
        # --- LÓGICA DO INÍCIO (MAIORIA EM SETEMBRO) ---
        # weekday() -> 0: Segunda, 1: Terça, 2: Quarta, 3: Quinta, 4: Sexta, 5: Sábado, 6: Domingo
        if primeiro_dia_set.weekday() <= 3: 
            # Dia 1º caiu entre Segunda e Quinta -> Pelo menos 4 dias da semana (maioria) estão em Setembro.
            # Retrocede até a segunda-feira desta semana (podendo puxar dias finais de agosto).
            inicio_semana = primeiro_dia_set - pd.Timedelta(days=primeiro_dia_set.weekday())
        else:
            # Dia 1º caiu na Sexta, Sábado ou Domingo -> A maioria dessa semana cai em Agosto.
            # Ignora essa semana mista e pula para a Segunda-feira da semana seguinte.
            inicio_semana = primeiro_dia_set + pd.Timedelta(days=7 - primeiro_dia_set.weekday())
        
        # --- LÓGICA DO FIM (MAIORIA EM SETEMBRO) ---
        if ultimo_dia_set.weekday() >= 3:
            # Dia 30 caiu entre Quinta e Domingo -> Pelo menos 4 dias da semana (maioria) estão em Setembro.
            # Avança até o domingo desta semana (podendo puxar dias iniciais de outubro).
            fim_semana = ultimo_dia_set + pd.Timedelta(days=6 - ultimo_dia_set.weekday())
        else:
            # Dia 30 caiu na Segunda, Terça ou Quarta -> A maioria dessa semana cai em Outubro.
            # Ignora essa semana mista e retrocede para o Domingo da semana anterior.
            fim_semana = ultimo_dia_set - pd.Timedelta(days=ultimo_dia_set.weekday() + 1)
        
        # Para que o domingo englobe até as 23:59:59
        fim_semana_limite = fim_semana + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        # Calcula a quantidade de semanas deste ano
        dias_totais = (fim_semana - inicio_semana).days + 1
        semanas_no_ano = dias_totais // 7
        total_semanas += semanas_no_ano
        
        # Filtra pela data de início da sessão (mantendo a sessão completa, 
        # mesmo que desplugue fora desse período, pois a integridade da linha é mantida)
        mask = (df['Start_plugin'] >= inicio_semana) & (df['Start_plugin'] <= fim_semana_limite)
        df_ano = df[mask].copy()
        df_filtrado = pd.concat([df_filtrado, df_ano])
        
        print(f" - Ano {ano}: de {inicio_semana.strftime('%d/%m/%Y')} (Segunda) até {fim_semana.strftime('%d/%m/%Y')} (Domingo) -> {semanas_no_ano} semanas")
    
    # Ordenação cronológica
    df_filtrado = df_filtrado.sort_values(by='Start_plugin').reset_index(drop=True)
    
    # --- RELATÓRIO ---
    print("\n" + "="*40)
    print("      RELATÓRIO DE FILTRAGEM (PASSO 2)")
    print("="*40)
    print(f"-> Total de semanas retidas: {total_semanas} semanas")
    print(f"-> Total de sessões no arquivo bruto: {len(df)}")
    print(f"-> Total de sessões retidas (Setembro Expandido): {len(df_filtrado)}")
    
    if not df_filtrado.empty:
        inicio_real = df_filtrado['Start_plugin'].min()
        fim_real = df_filtrado['Start_plugin'].max()
        print(f"-> Primeira sessão da amostra: {inicio_real.strftime('%A, %d/%m/%Y %H:%M')}")
        print(f"-> Última sessão da amostra:   {fim_real.strftime('%A, %d/%m/%Y %H:%M')}")
    print("="*40 + "\n")
    
    return df_filtrado


if __name__ == "__main__":
    print("Execução Individual Detectada (Passo 2)...")
    
    # Executa o passo 1 para pegar o DF limpo na memória
    df_limpo = limpar_dados_ev(RAW_CSV_PATH)
    
    # Executa a filtragem do passo 2
    df_setembro = filtrar_semanas_setembro(df_limpo)
    
    # Exporta para verificação
    caminho_saida = OUTPUT_DIR / "sessoes_ve_semanas_setembro.csv"
    df_setembro.to_csv(caminho_saida, index=False)
    
    print(f"✅ Arquivo filtrado salvo com sucesso em: {caminho_saida.relative_to(PROJECT_ROOT)}")
