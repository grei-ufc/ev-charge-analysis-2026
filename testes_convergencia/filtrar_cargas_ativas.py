#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Saneamento Cadastral: Filtragem de Consumidores Desativados (SIT_ATIV == 'DS')
Lê a situação cadastral (SIT_ATIV) diretamente da camada UCBT_tab do Geodatabase da BDGD
e sanitiza o arquivo de cargas de Baixa Tensão (CargasBT_Sintetico_20250139_ESB01S4.dss),
removendo todas as unidades desativadas e preservando a integridade das cargas ativas e IP.
"""

from pathlib import Path
import re
import shutil
import pyogrio
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
GDB_PATH = BASE_DIR.parent / "dados" / "dados-da-rede" / "Enel_CE_39_2024-12-31_V11_20250822-1151.gdb"
REDE_DIR = BASE_DIR / "data" / "rede" / "ESB01S4"

CARGAS_BT_DSS = REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4.dss"
BACKUP_TODAS_DSS = REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4_todas.dss"
CARGAS_DESATIVADAS_DSS = REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4_desativadas.dss"


def extrair_situacao_cadastral_bdgd():
    """Lê a tabela UCBT_tab do GDB e mapeia situação cadastral e transformador por RAMAL, PN_CON, PAC e COD_ID."""
    print(f"📂 Abrindo Geodatabase: {GDB_PATH.name}")
    print("⏳ Consultando 'UCBT_tab' para CTMT == 'ESB01S4'...")

    # CTMT DEVE estar em columns para que o filtro where funcione no GDAL
    colunas = ["RAMAL", "PN_CON", "PAC", "COD_ID", "CTMT", "UNI_TR_MT", "SIT_ATIV", "CAR_INST"]
    df = pyogrio.read_dataframe(
        GDB_PATH,
        layer="UCBT_tab",
        columns=colunas,
        where="CTMT = 'ESB01S4'"
    )

    df["SIT_ATIV_LIMPO"] = df["SIT_ATIV"].astype(str).str.strip().str.upper()
    df["UNI_TR_MT_STR"] = df["UNI_TR_MT"].astype(str).str.strip()

    print(f"✅ Total de UCs lidas no GDB: {len(df)}")
    print(f"   - Ativas (AT): {(df['SIT_ATIV_LIMPO'] == 'AT').sum()}")
    print(f"   - Desativadas (DS): {(df['SIT_ATIV_LIMPO'] == 'DS').sum()}")
    print(f"   - Exemplos de RAMAL: {df['RAMAL'].dropna().head(5).tolist()}")
    print(f"   - Exemplos de PN_CON: {df['PN_CON'].dropna().head(5).tolist()}")
    print(f"   - Exemplos de PAC: {df['PAC'].dropna().head(5).tolist()}")

    mapa_sit = {}
    mapa_trf = {}

    for _, row in df.iterrows():
        sit = row["SIT_ATIV_LIMPO"]
        trf = row["UNI_TR_MT_STR"]

        # Registra todas as chaves possíveis para garantir match
        chaves = []
        for col in ["RAMAL", "PN_CON", "PAC", "COD_ID"]:
            val = row[col]
            if pd.notna(val):
                sval = str(val).strip()
                if sval:
                    chaves.append(sval)
                    # Também versão sem sufixos
                    chaves.append(re.sub(r'_\d+$', '', sval))
                    # Versão numérica
                    m_num = re.search(r'(\d+)', sval)
                    if m_num:
                        chaves.append(m_num.group(1))

        for k in chaves:
            mapa_sit[k] = sit
            mapa_trf[k] = trf

    return mapa_sit, mapa_trf


def sanitizar_cargas_bt():
    mapa_sit, mapa_trf = extrair_situacao_cadastral_bdgd()

    if not CARGAS_BT_DSS.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {CARGAS_BT_DSS}")

    # Usa o backup de todas as cargas como fonte primária
    if BACKUP_TODAS_DSS.exists():
        arquivo_fonte = BACKUP_TODAS_DSS
        print(f"ℹ️ Usando arquivo fonte original: {arquivo_fonte.name}")
    else:
        shutil.copy2(CARGAS_BT_DSS, BACKUP_TODAS_DSS)
        arquivo_fonte = BACKUP_TODAS_DSS
        print(f"💾 Backup integral criado em: {BACKUP_TODAS_DSS.name}")

    with open(arquivo_fonte, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    linhas_ativas = []
    linhas_desativadas = []

    stats = {
        "total_linhas": len(linhas),
        "cargas_ativas": 0,
        "cargas_desativadas": 0,
        "cargas_ip": 0,
        "cargas_nao_encontradas": 0,
        "kw_ativo_total": 0.0,
        "kw_desativado_total": 0.0,
        "tok5079_ativas": 0,
        "tok5079_desativadas": 0,
        "tok5079_kw_ativo": 0.0,
        "tok5079_kw_desativado": 0.0,
    }

    padrao_load = re.compile(r'New\s+"Load\.BT_([^"]+)"', re.IGNORECASE)
    padrao_kw = re.compile(r'kw\s*=\s*([0-9.]+)', re.IGNORECASE)

    primeiros_matches = []

    for linha in linhas:
        texto = linha.strip()
        if not texto or texto.startswith("!"):
            linhas_ativas.append(linha)
            continue

        match_load = padrao_load.search(texto)
        if not match_load:
            linhas_ativas.append(linha)
            continue

        load_id_completo = match_load.group(1)  # ex: UC6416078_1_M1 ou IPIP682637_M1
        match_kw = padrao_kw.search(texto)
        kw_val = float(match_kw.group(1)) if match_kw else 0.0

        # Remove o sufixo de modelo de carga (_M1 ou _M2)
        cod_cons = re.sub(r'_M[12]$', '', load_id_completo)

        # Iluminação Pública (PIP) é sempre ativa
        if "IPIP" in cod_cons:
            linhas_ativas.append(linha)
            stats["cargas_ip"] += 1
            stats["kw_ativo_total"] += kw_val
            continue

        # Identifica a situação cadastral
        cod_base = re.sub(r'_\d+$', '', cod_cons)
        match_num = re.search(r'(\d+)', cod_cons)
        cod_num = match_num.group(1) if match_num else ""

        sit = (
            mapa_sit.get(cod_cons)
            or mapa_sit.get(cod_base)
            or (mapa_sit.get(cod_num) if cod_num else None)
        )
        trf = (
            mapa_trf.get(cod_cons)
            or mapa_trf.get(cod_base)
            or (mapa_trf.get(cod_num) if cod_num else None)
            or ""
        )

        if len(primeiros_matches) < 8:
            primeiros_matches.append((cod_cons, sit, trf))

        eh_tok5079 = "TOK5079" in trf

        if sit == "DS":
            linhas_desativadas.append(linha)
            stats["cargas_desativadas"] += 1
            stats["kw_desativado_total"] += kw_val
            if eh_tok5079:
                stats["tok5079_desativadas"] += 1
                stats["tok5079_kw_desativado"] += kw_val
        elif sit == "AT":
            linhas_ativas.append(linha)
            stats["cargas_ativas"] += 1
            stats["kw_ativo_total"] += kw_val
            if eh_tok5079:
                stats["tok5079_ativas"] += 1
                stats["tok5079_kw_ativo"] += kw_val
        else:
            # Caso não encontrado expressamente no mapa, mantém ativa por segurança
            linhas_ativas.append(linha)
            stats["cargas_nao_encontradas"] += 1
            stats["kw_ativo_total"] += kw_val
            if eh_tok5079:
                stats["tok5079_ativas"] += 1
                stats["tok5079_kw_ativo"] += kw_val

    # Escreve o arquivo sanitizado
    with open(CARGAS_BT_DSS, "w", encoding="utf-8") as f:
        f.writelines(linhas_ativas)

    # Escreve o arquivo de desativadas para auditoria
    with open(CARGAS_DESATIVADAS_DSS, "w", encoding="utf-8") as f:
        f.writelines(linhas_desativadas)

    print("\n🔍 Exemplos de correspondência de cargas no OpenDSS:")
    for c_cons, s_val, t_val in primeiros_matches:
        print(f"   • Load: {c_cons:20s} -> Status: {s_val} (TRF: {t_val})")

    print("\n" + "=" * 75)
    print("📊 RESULTADO DO SANEAMENTO CADASTRAL (OpenDSS - ESB01S4)")
    print("=" * 75)
    print(f"• Total de linhas processadas: {stats['total_linhas']}")
    print(f"• Cargas ATIVAS mantidas: {stats['cargas_ativas']} objetos OpenDSS (inclui {stats['cargas_ip']} de IP)")
    print(f"• Cargas DESATIVADAS removidas: {stats['cargas_desativadas']} objetos OpenDSS")
    if stats['cargas_nao_encontradas'] > 0:
        print(f"• Cargas não localizadas (mantidas ativas por precaução): {stats['cargas_nao_encontradas']}")
    print(f"• Potência Ativa Mantida: {stats['kw_ativo_total']:.2f} kW")
    print(f"• Potência Fantasma Removida: {stats['kw_desativado_total']:.2f} kW")

    print("\n" + "-" * 75)
    print("⚡ IMPACTO ESPECÍFICO NO TRANSFORMADOR CRÍTICO TRF_TOK5079A (150 kVA nominal):")
    print(f"• Objetos de carga ativos mantidos: {stats['tok5079_ativas']}")
    print(f"• Objetos de carga fantasmas removidos: {stats['tok5079_desativadas']}")
    print(f"• Potência Ativa Real mantida: {stats['tok5079_kw_ativo']:.2f} kW")
    print(f"• Potência Fantasma eliminada: {stats['tok5079_kw_desativado']:.2f} kW")
    total_tok = stats['tok5079_kw_ativo'] + stats['tok5079_kw_desativado']
    alivio_pct = (stats['tok5079_kw_desativado'] / total_tok) * 100 if total_tok > 0 else 0
    print(f"• Alívio de Carga no TRF_TOK5079A: {alivio_pct:.1f}% da demanda anterior foi removida!")
    print("=" * 75)

    print(f"\n✅ Arquivo principal sanitizado: {CARGAS_BT_DSS.name}")
    print(f"✅ Arquivo de cargas desativadas: {CARGAS_DESATIVADAS_DSS.name}")


if __name__ == "__main__":
    sanitizar_cargas_bt()
