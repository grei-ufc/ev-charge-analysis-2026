#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair as curvas de carga de um arquivo .dss (Loadshapes)
e organizá-las num arquivo CSV contendo apenas uma coluna de índice numérico
e uma coluna para cada curva.
"""

import re
import argparse
import pandas as pd
from pathlib import Path

def interpolar_pchip_diario(mults):
    """
    Interpola uma curva de 24 pontos (1 em 1 hora) para 144 pontos (10 em 10 minutos).
    Garante o comportamento suave (circular) fechando o dia com o ponto inicial.
    """
    if len(mults) != 24:
        raise ValueError(f"Esperado 24 pontos, recebido {len(mults)}")
    
    # Adicionamos o 1º ponto no fim (representando 00:00 do próximo dia) para garantir a curvatura correta
    y = mults + [mults[0]]
    
    # 25 pontos de hora em hora (das 00:00 até 00:00 do dia seguinte)
    idx_1h = pd.date_range("2026-01-01", periods=25, freq="h")
    s = pd.Series(y, index=idx_1h)
    
    # 145 pontos de 10 em 10 min
    idx_10min = pd.date_range("2026-01-01", periods=145, freq="10min")
    
    # Interpolação PCHIP e reindexação
    s_interp = s.reindex(idx_10min).interpolate(method='pchip')
    
    # Descarta o último ponto (145º) e previne pequenos ruídos negativos
    s_final = s_interp.iloc[:-1].clip(lower=0.0).round(6)
    
    return s_final.tolist()

def dss_para_csv(input_path: Path, output_path: Path, salvar_csv: bool = True):
    # Regex para capturar o nome do Loadshape e a lista dentro de mult=(...)
    padrao = re.compile(r'New\s+["\']?Loadshape\.([a-zA-Z0-9\-_]+)["\']?.*mult=\(([^)]+)\)', re.IGNORECASE)
    
    dados = {}
    with open(input_path, 'r', encoding='utf-8') as f:
        for linha in f:
            match = padrao.search(linha.strip())
            if match:
                nome = match.group(1)
                mults_str = match.group(2)
                # Converte os valores da string separada por vírgula em floats
                mults = [float(v.strip()) for v in mults_str.split(',')]
                
                # Aplica interpolação se a curva tiver exatamente 24 horas
                if len(mults) == 24:
                    dados[nome] = interpolar_pchip_diario(mults)
                else:
                    print(f"⚠️ Aviso: Curva {nome} ignorada pois possui {len(mults)} pontos em vez de 24.")
                
    if not dados:
        print("❌ Nenhuma curva válida de 24h encontrada no arquivo DSS fornecido.")
        return None
        
    # Converte o dicionário para um DataFrame (onde a chave vira a coluna e os valores viram as linhas)
    df = pd.DataFrame(dados)
    
    if salvar_csv:
        # Cria os diretórios necessários
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Salva o DataFrame num CSV
        df.to_csv(output_path, index=True, index_label='index')
        print(f"✅ Arquivo CSV gerado com sucesso: {output_path.name}")
    
    print(f"📊 Total de curvas diárias extraídas: {df.shape[1]}")
    print(f"📏 Resolução final: {df.shape[0]} pontos por curva (passo de 10 minutos)")
    return df

def executar_passo1(salvar_csv=True):
    base_dir = Path(__file__).resolve().parents[3] 
    arquivo_entrada_padrao = base_dir / "data" / "rede" / "ESB01S4" / "CurvaCarga_20250139_ESB01S4_------1-----.dss"
    arquivo_saida_padrao = base_dir / "data" / "datasets" / "curvas-de-carga" / "CurvaCarga_referencia_diaria.csv"
    
    if not arquivo_entrada_padrao.exists():
        print(f"❌ Erro: Arquivo não encontrado - {arquivo_entrada_padrao}")
        return None
        
    print(f"Lendo curvas de: {arquivo_entrada_padrao.name} ...")
    return dss_para_csv(arquivo_entrada_padrao, arquivo_saida_padrao, salvar_csv)

def main():
    executar_passo1(salvar_csv=True)

if __name__ == '__main__':
    main()
