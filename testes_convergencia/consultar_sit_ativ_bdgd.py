#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para consultar o campo SIT_ATIV (Situação de Ativação do Consumidor)
diretamente na tabela UCBT_tab do Geodatabase original da BDGD (Enel Ceará).
"""

from pathlib import Path
import pyogrio
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
GDB_PATH = BASE_DIR.parent / "dados" / "dados-da-rede" / "Enel_CE_39_2024-12-31_V11_20250822-1151.gdb"


def consultar_ucbt():
    print(f"📂 Abrindo Geodatabase: {GDB_PATH.name}")
    print("⏳ Lendo camada 'UCBT_tab' com filtro CTMT == 'ESB01S4' via pyogrio...")

    colunas = ["COD_ID", "CTMT", "UNI_TR_MT", "SIT_ATIV", "DAT_CON", "CAR_INST"]
    
    df = pyogrio.read_dataframe(
        GDB_PATH,
        layer="UCBT_tab",
        columns=colunas,
        where="CTMT = 'ESB01S4'"
    )

    print("\n" + "=" * 70)
    print("📊 RESULTADO DA CONSULTA NA BDGD ORIGINAL (UCBT_tab - ESB01S4)")
    print("=" * 70)
    print(f"• Total de UCs encontradas no alimentador ESB01S4: {len(df)}")
    
    # Distribuição de SIT_ATIV no alimentador
    contagem_sit = df["SIT_ATIV"].value_counts(dropna=False)
    print("\n• Distribuição de SIT_ATIV no alimentador ESB01S4:")
    for status, count in contagem_sit.items():
        pct = (count / len(df)) * 100.0
        desc = "Ativo" if status == "AT" else ("Desativado" if status == "DS" else str(status))
        print(f"  - '{status}' ({desc}): {count} consumidores ({pct:.2f}%)")

    # Análise específica no transformador crítico TOK5079 / TOK5079A
    df_tok = df[df["UNI_TR_MT"].astype(str).str.contains("TOK5079", case=False, na=False)]
    print("\n" + "-" * 70)
    print(f"• Análise específica no transformador TOK5079 (Total: {len(df_tok)} UCs):")
    if not df_tok.empty:
        contagem_tok = df_tok["SIT_ATIV"].value_counts(dropna=False)
        for status, count in contagem_tok.items():
            pct = (count / len(df_tok)) * 100.0
            desc = "Ativo" if status == "AT" else ("Desativado" if status == "DS" else str(status))
            print(f"  - '{status}' ({desc}): {count} consumidores ({pct:.2f}%)")
    else:
        print("  - Nenhuma UC encontrada com código TOK5079 diretamente em UNI_TR_MT.")
        print(f"  - Exemplos de códigos de transformadores presentes: {df['UNI_TR_MT'].dropna().unique()[:5]}")

    print("=" * 70)


if __name__ == "__main__":
    consultar_ucbt()
