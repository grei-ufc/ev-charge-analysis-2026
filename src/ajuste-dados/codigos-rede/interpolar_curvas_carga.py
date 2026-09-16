#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para realizar a interpolação PCHIP das curvas de carga semanais (168h).
Lê o arquivo .dss que tem passo de 1 hora e gera um novo com passo de 10 minutos (1008 pontos).
"""

import os
import re
import argparse
import pandas as pd
from pathlib import Path

def interpolar_pchip(mults):
    """
    Interpola uma lista de 168 pontos (1 em 1 hora) para 1008 pontos (10 em 10 minutos) usando Pandas.
    Adiciona o primeiro ponto ao final temporariamente para garantir a continuidade circular 
    da semana (fechamento de domingo para segunda-feira).
    """
    if len(mults) != 168:
        raise ValueError(f"Esperado 168 pontos, recebido {len(mults)}")
    
    # Adiciona o primeiro ponto ao final (hora 168) para continuidade do PCHIP
    y = mults + [mults[0]]
    
    # Cria os índices de 1 hora
    idx_1h = pd.date_range("2026-01-01", periods=169, freq="h")
    s = pd.Series(y, index=idx_1h)
    
    # Cria os índices de 10 minutos (1009 pontos para cobrir de 0 a 168h exatos)
    idx_10min = pd.date_range("2026-01-01", periods=1009, freq="10min")
    
    # Reindexa para 10 minutos e aplica PCHIP
    s_interp = s.reindex(idx_10min).interpolate(method='pchip')
    
    # Descarta o último ponto (que representa o fechamento/início da próxima semana) e limita >= 0
    s_final = s_interp.iloc[:-1].clip(lower=0.0).round(6)
    
    return s_final.tolist()

def processar_arquivo(input_file: Path, output_file: Path):
    padrao = re.compile(r'New\s+["\']?Loadshape\.([a-zA-Z0-9\-_]+)["\']?.*mult=\(([^)]+)\)', re.IGNORECASE)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    contador = 0
    with open(input_file, 'r', encoding='utf-8') as fin, open(output_file, 'w', encoding='utf-8') as fout:
        for linha in fin:
            linha_strip = linha.strip()
            if not linha_strip or linha_strip.startswith('!'):
                fout.write(linha)
                continue
                
            match = padrao.search(linha_strip)
            if match:
                nome = match.group(1)
                mults_str = match.group(2)
                mults = [float(v.strip()) for v in mults_str.split(',')]
                
                if len(mults) == 168:
                    novos_mults = interpolar_pchip(mults)
                    mult_str = ", ".join(f"{val:g}" for val in novos_mults)
                    
                    # Gera a nova linha com npts=1008 e minterval=10
                    nova_linha = f'New "Loadshape.{nome}" npts=1008 minterval=10 mult=({mult_str})'
                    fout.write(nova_linha + '\n')
                    contador += 1
                else:
                    print(f"⚠️ Aviso: Loadshape {nome} tem {len(mults)} pontos em vez de 168. Mantendo original.")
                    fout.write(linha)
            else:
                fout.write(linha)
                
    print(f"✅ Interpolação concluída! {contador} curvas PCHIP geradas em: {output_file.name}")

def main():
    base_dir = Path(__file__).resolve().parents[3] # ev-analysis-2026
    
    arquivo_entrada_padrao = base_dir / "data" / "rede" / "ESB01S4" / "CurvaCarga_20250139_ESB01S4.dss"
    arquivo_saida_padrao = base_dir / "data" / "rede" / "ESB01S4" / "CurvaCarga_20250139_ESB01S4_10min.dss"
    
    parser = argparse.ArgumentParser(description="Interpola Curvas de Carga (1h para 10min) usando método PCHIP.")
    parser.add_argument("--entrada", "-i", type=Path, default=arquivo_entrada_padrao, help="Caminho do CurvaCarga.dss original (1h)")
    parser.add_argument("--saida", "-o", type=Path, default=arquivo_saida_padrao, help="Caminho do CurvaCarga interpolado a salvar (10min)")
    
    args = parser.parse_args()
    
    if not args.entrada.exists():
        print(f"❌ Arquivo não encontrado: {args.entrada}")
        return
        
    print(f"Processando {args.entrada.name}...")
    processar_arquivo(args.entrada, args.saida)

if __name__ == '__main__':
    main()

