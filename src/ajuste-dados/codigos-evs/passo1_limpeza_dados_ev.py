import pandas as pd
from pathlib import Path
import sys

# Definição de caminhos padrão
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_CSV_PATH = PROJECT_ROOT / "data/datasets/veiculos-eletricos/Dataset 1_EV charging reports.csv"
OUTPUT_DIR = PROJECT_ROOT / "data/datasets/veiculos-eletricos"

def limpar_dados_ev(caminho_csv: Path, manter_todas_colunas: bool = False) -> pd.DataFrame:
    """
    Lê o dataset bruto de sessões de VE, limpa os dados e retorna o DataFrame processado.
    Por padrão (manter_todas_colunas=False), retorna apenas as colunas essenciais para o orquestrador.
    """
    print(f"Lendo dataset: {caminho_csv.name}")
    df = pd.read_csv(caminho_csv, sep=';')
    
    # 1. Tratamento Numérico (Trocar vírgula por ponto)
    colunas_numericas = ['El_kWh', 'Duration_hours']
    for col in colunas_numericas:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(',', '.').astype(float)
            
    # 2. Tratamento de Data/Hora
    # Formato original: 21.12.2018 10:20
    df['Start_plugin'] = pd.to_datetime(df['Start_plugin'], format='%d.%m.%Y %H:%M')
    df['End_plugout'] = pd.to_datetime(df['End_plugout'], format='%d.%m.%Y %H:%M')
    
    # Ordena pelo horário de plugin globalmente para organização
    df = df.sort_values(by='Start_plugin').reset_index(drop=True)
    
    # Filtra as colunas se não for exigido manter todas
    if not manter_todas_colunas:
        colunas_importantes = ['User_ID', 'User_type', 'Start_plugin', 'End_plugout', 'El_kWh', 'Duration_hours']
        df = df[colunas_importantes]
    
    return df


if __name__ == "__main__":
    # Quando rodado INDIVIDUALMENTE, o código salva o arquivo para inspeção
    print("Execução Individual Detectada: Processando e exportando arquivos de saída...")
    
    # Roda a função principal (exigindo todas as colunas apenas para gerar o CSV completo)
    df_limpo = limpar_dados_ev(RAW_CSV_PATH, manter_todas_colunas=True)
    
    # =========================================================================
    # TRADUÇÕES APLICADAS APENAS PARA O CSV (Execução Individual)
    # =========================================================================
    traducao_duracao = {
        'Less than 3 hours': 'Menos de 3 horas',
        'Between 3 and 6 hours': 'Entre 3 e 6 horas',
        'Between 6 and 9  hours': 'Entre 6 e 9 horas', 
        'Between 9 and 12 hours': 'Entre 9 e 12 horas',
        'Between 12 and 15 hours': 'Entre 12 e 15 horas',
        'Between 15 and 18 hours': 'Entre 15 e 18 horas',
        'More than 18 hours': 'Mais de 18 horas',
        'NA': 'N/D'
    }
    
    traducao_dias = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 
        'Wednesday': 'Quarta-feira', 'Thursday': 'Quinta-feira', 
        'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    
    traducao_plugin = {
        'early night (midnight-3)': 'Madrugada (00-03)',
        'late night (3-6)': 'Fim da madrugada (03-06)',
        'early morning (6-9)': 'Início da manhã (06-09)',
        'late morning (9-12)': 'Fim da manhã (09-12)',
        'early afternoon (12-15)': 'Início da tarde (12-15)',
        'late afternoon (15-18)': 'Fim da tarde (15-18)',
        'early evening (18-21)': 'Início da noite (18-21)',
        'late evening (21-midnight)': 'Fim da noite (21-00)'
    }
    
    traducao_meses = {
        'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr',
        'May': 'Mai', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
        'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'
    }
    
    traducao_colunas = {
        'session_ID': 'id_sessao',
        'Garage_ID': 'id_garagem',
        'User_ID': 'id_usuario',
        'User_type': 'tipo_usuario',
        'Shared_ID': 'id_compartilhado',
        'Start_plugin': 'inicio_conexao',
        'Start_plugin_hour': 'hora_inicio_conexao',
        'End_plugout': 'fim_conexao',
        'End_plugout_hour': 'hora_fim_conexao',
        'El_kWh': 'energia_kwh',
        'Duration_hours': 'duracao_horas',
        'month_plugin': 'mes_conexao',
        'weekdays_plugin': 'dia_semana_conexao',
        'Plugin_category': 'categoria_horario_conexao',
        'Duration_category': 'categoria_duracao'
    }

    # Aplica as traduções nas colunas categóricas
    df_limpo['Duration_category'] = df_limpo['Duration_category'].replace(traducao_duracao)
    df_limpo['weekdays_plugin'] = df_limpo['weekdays_plugin'].replace(traducao_dias)
    df_limpo['Plugin_category'] = df_limpo['Plugin_category'].replace(traducao_plugin)
    df_limpo['month_plugin'] = df_limpo['month_plugin'].replace(traducao_meses)
    
    # Aplica a tradução dos cabeçalhos das colunas
    df_limpo = df_limpo.rename(columns=traducao_colunas)
    
    # =========================================================================
    
    # Caminho de saída
    caminho_saida = OUTPUT_DIR / "sessoes_ve_limpas.csv"
    
    # Salva o arquivo CSV
    df_limpo.to_csv(caminho_saida, index=False)
    print(f"✅ Arquivo de limpeza exportado com sucesso para: {caminho_saida.relative_to(PROJECT_ROOT)}")
