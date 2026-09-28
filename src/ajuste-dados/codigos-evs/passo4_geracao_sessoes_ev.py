import pandas as pd
import numpy as np
from pathlib import Path

# Importa módulos locais
from passo1_limpeza_dados_ev import RAW_CSV_PATH, PROJECT_ROOT, OUTPUT_DIR, limpar_dados_ev
from passo2_filtragem_setembro_ev import filtrar_semanas_setembro
from passo3_agrupamento_semanal_ev import agrupar_sessoes_por_usuario_e_semana

# ==============================================================================
# CONFIGURAÇÃO DA FROTA BRASILEIRA (Top 10 Vendas 2022-2026)
# ==============================================================================
FROTA_BR = [
    {"modelo": "BYD DOLPHIN MINI GS5EV", "cap_kwh": 38.88, "vendas": 80820},
    {"modelo": "BYD DOLPHIN GS 180EV",   "cap_kwh": 44.90, "vendas": 58259},
    {"modelo": "BYD SONG PLUS GS DM",    "cap_kwh": 18.30, "vendas": 57821},
    {"modelo": "BYD SONG PRO GS DM",     "cap_kwh": 18.30, "vendas": 40565},
    {"modelo": "BYD KING GS DM",         "cap_kwh": 18.30, "vendas": 22091},
    {"modelo": "GEELY EX2 MAX",          "cap_kwh": 39.40, "vendas": 17966},
    {"modelo": "GWM HAVAL H6 PHEV 19",   "cap_kwh": 19.00, "vendas": 16980},
    {"modelo": "BYD SONG PRO GL DM",     "cap_kwh": 12.96, "vendas": 15848},
    {"modelo": "BYD DOLPHIN MINI GS EV", "cap_kwh": 38.88, "vendas": 15827},
    {"modelo": "GWM HAVAL H6 GT",        "cap_kwh": 35.00, "vendas": 14576},
]

def mapear_frota_as_semanas(dict_agrupado: dict) -> dict:
    """
    Analisa o consumo máximo histórico (E_max) de CADA SEMANA independente
    e sorteia 1 VE da frota brasileira, transformando cada semana num perfil virtual único.
    """
    mapa_frota = {}
    maior_bateria_do_mercado = max(FROTA_BR, key=lambda x: x["cap_kwh"])
    
    for user_id, semanas in dict_agrupado.items():
        for week_label, df_semana in semanas.items():
            chave_perfil = f"{user_id}_{week_label}"
            
            e_max = 0
            if not df_semana.empty:
                e_max = df_semana['El_kWh'].max()
                
            # Filtra opções viáveis (Capacidade >= Energia Máxima Gasta naquela semana)
            opcoes_validas = [v for v in FROTA_BR if v["cap_kwh"] >= e_max]
            
            if not opcoes_validas:
                veiculo_sorteado = maior_bateria_do_mercado
            else:
                # Sorteio viciado (ponderado pelas vendas)
                total_vendas_validas = sum(v["vendas"] for v in opcoes_validas)
                probabilidades = [v["vendas"] / total_vendas_validas for v in opcoes_validas]
                
                idx_escolhido = np.random.choice(len(opcoes_validas), p=probabilidades)
                veiculo_sorteado = opcoes_validas[idx_escolhido]
                
            mapa_frota[chave_perfil] = veiculo_sorteado
        
    return mapa_frota

# ==============================================================================
# PROCESSAMENTO DE SESSÕES
# ==============================================================================
def processar_sessoes_da_semana(df_semana: pd.DataFrame, profile_name: str, p_max_kw: float, veiculo: dict) -> list:
    """
    Processa as sessões brutas de UMA ÚNICA SEMANA de um usuário.
    Garante a bateria atribuída e realiza o encadeamento temporal (micro-sessões).
    """
    df_semana = df_semana.sort_values('Start_plugin').reset_index(drop=True)
    cap_bateria_kw = veiculo["cap_kwh"]
    modelo_veiculo = veiculo["modelo"]
    
    sessoes_export = []
    grupos_aglutinados = []
    grupo_atual = []
    
    # 1. Aglutinação de micro-sessões (Gap <= 30 min)
    for idx, row in df_semana.iterrows():
        if len(grupo_atual) == 0:
            grupo_atual.append(idx)
        else:
            last_idx = grupo_atual[-1]
            last_row = df_semana.iloc[last_idx]
            delta_t_min = (row['Start_plugin'] - last_row['End_plugout']).total_seconds() / 60.0
            
            if delta_t_min <= 30.0:
                grupo_atual.append(idx)
            else:
                grupos_aglutinados.append(grupo_atual)
                grupo_atual = [idx]
    if grupo_atual:
        grupos_aglutinados.append(grupo_atual)
        
    # 2. Retro-propagação Temporal em cada grupo
    for grupo in grupos_aglutinados:
        soc_final_obrigatorio = None
        
        # De trás pra frente
        for idx in reversed(grupo):
            row = df_semana.iloc[idx]
            t_in = row['Start_plugin']
            t_out = row['End_plugout']
            e_kwh = row['El_kWh']
            
            if e_kwh <= 0: continue
                
            delta_t_horas = (t_out - t_in).total_seconds() / 3600.0
            t_idle_horas = delta_t_horas - (e_kwh / p_max_kw)
            delta_soc = e_kwh / cap_bateria_kw
            
            # Definição do SoC Final (Target)
            if soc_final_obrigatorio is not None:
                target_soc = soc_final_obrigatorio
            else:
                if t_idle_horas > 0:
                    target_soc = 1.0  
                else:
                    initial_soc = np.random.uniform(0.20, 0.50)
                    target_soc = min(initial_soc + delta_soc, 1.0)
            
            # Cálculo do SoC Inicial
            if soc_final_obrigatorio is not None or t_idle_horas > 0:
                initial_soc = target_soc - delta_soc
                
            # Fallback: Proteção contra baterias que quase estouraram o limite
            if initial_soc < 0.05:
                initial_soc = 0.05
                target_soc = min(initial_soc + delta_soc, 1.0)
                
            soc_final_obrigatorio = initial_soc
            
            # Minuto absoluto na semana
            segunda_meia_noite = t_in.floor('D') - pd.to_timedelta(t_in.weekday(), unit='D')
            min_in = (t_in - segunda_meia_noite).total_seconds() / 60.0
            min_out = (t_out - segunda_meia_noite).total_seconds() / 60.0
            
            sessoes_export.append({
                'Profile_Name': profile_name,
                'Modelo_Veiculo': modelo_veiculo,
                'Start_Min': int(min_in),
                'End_Min': int(min_out),
                'Initial_SoC': round(initial_soc, 3),
                'Target_SoC': round(target_soc, 3),
                'Battery_Capacity_kWh': cap_bateria_kw,
                'P_max_kW': p_max_kw
            })
            
    sessoes_export.sort(key=lambda x: x['Start_Min'])
    return sessoes_export

def gerar_csv_sessoes_ev(dict_agrupado: dict) -> pd.DataFrame:
    print("Mapeando frota brasileira para os perfis semanais...")
    mapa_frota = mapear_frota_as_semanas(dict_agrupado)
    
    print("Gerando tabela FÍSICA de Eventos de Recarga...")
    todas_sessoes = []
    potencias_estudo = [3.6, 7.2]
    
    for user_id, semanas in dict_agrupado.items():
        for week_label, df_semana in semanas.items():
            chave_perfil = f"{user_id}_{week_label}"
            veiculo_atribuido = mapa_frota[chave_perfil]
            
            for p_kw in potencias_estudo:
                nome_curva = f"{chave_perfil}_{p_kw}kW".replace('.', 'p')
                sessoes = processar_sessoes_da_semana(df_semana, nome_curva, p_kw, veiculo_atribuido)
                todas_sessoes.extend(sessoes)
                
    df_eventos = pd.DataFrame(todas_sessoes)
    print(f"-> {len(df_eventos)} eventos físicos gerados com sucesso.")
    return df_eventos

if __name__ == "__main__":
    print("Execução Individual Detectada (Passo 4 - Caldera)...")
    df_p1 = limpar_dados_ev(RAW_CSV_PATH)
    df_p2 = filtrar_semanas_setembro(df_p1)
    dict_p3 = agrupar_sessoes_por_usuario_e_semana(df_p2)
    df_eventos = gerar_csv_sessoes_ev(dict_p3)
    print(df_eventos.head(10))
