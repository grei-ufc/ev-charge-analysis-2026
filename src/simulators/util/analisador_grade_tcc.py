"""Módulo de Análise Comparativa Diferencial e Relativa da Grade de VEs
========================================================================

Este módulo processa os arquivos de simulação da grade paramétrica de penetração
de Veículos Elétricos (0% a 50% em passos de 5%) e calcula as métricas diferenciais
e relativas ao Caso Base (0 VEs), conforme documentado em:
`docs/metodologia_analise_comparativa_relativa.md`.

Métricas Calculadas:
--------------------
1. Demanda e Coincidência de Ponta: ΔP_max (kW), %ΔP_max (%), ΔFC (Fator de Carga).
2. Balanço Energético: Energia Tronco (kWh), %ΔE_tronco (%), Energia VEs (kWh).
3. Tensão em Regime Permanente: ΔV_min (pu), ΔV_med (pu).
4. Indicadores Regulatórios PRODIST Módulo 8 Desagregados (Marinho et al., 2026):
   - ΔDRP_sub, ΔDRC_sub (Subtensão precária e crítica).
   - Novas Barras Transgressoras: ΔN_barras(DRP > 3%) e ΔN_barras(DRC > 0.5%).
5. Índice de Desvio de Tensão (Nwobu et al., 2026):
   - ΔVDI_RMS (%), %ΔVDI_sub (%).
6. Determinação da Capacidade de Hospedagem (Hosting Capacity) do alimentador.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
FIGURAS_DIR = OUTPUT_DIR / "figuras_comparativas"
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


def identificar_colunas_circuito(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Identifica colunas de tensões de barras, linhas e VEs no DataFrame de forma robusta."""
    colunas = list(df.columns)
    
    # 1. Tensões de fase nas barras BT (2.210 barras por fase, conforme Módulo 2 do notebook)
    v1_cols = [c for c in colunas if "V1_pu" in c]
    v2_cols = [c for c in colunas if "V2_pu" in c]
    v3_cols = [c for c in colunas if "V3_pu" in c]
    
    # 2. Linhas de distribuição (correntes e potências ativas das fases 1, 2 e 3)
    line_i_cols = [c for c in colunas if "Line" in c and any(i in c for i in ["I1_A", "I2_A", "I3_A"])]
    line_p_cols = [c for c in colunas if "Line" in c and any(p in c for p in ["P1_w", "P2_w", "P3_w"])]
    line_q_cols = [c for c in colunas if "Line" in c and any(q in c for q in ["Q1_var", "Q2_var", "Q3_var"])]
    
    # 3. Potência de carregamento dos Veículos Elétricos (CalderaEV)
    ev_cols = [c for c in colunas if "CalderaEV" in c and "-P" in c]

    return {
        "v1": v1_cols,
        "v2": v2_cols,
        "v3": v3_cols,
        "line_i": line_i_cols,
        "line_p": line_p_cols,
        "line_q": line_q_cols,
        "ev_p": ev_cols,
    }



def extrair_metrica_cenario(
    caminho_csv: Path,
    cols_map: Dict[str, List[str]],
    nome_tronco: Optional[str] = None,
    delta_t_h: float = 10.0 / 60.0,
) -> Dict:
    """Extrai métricas consolidadas de um único arquivo CSV de cenário."""
    df = pd.read_csv(caminho_csv)
    n_passos = len(df)

    # 1. Tensão e Desagregação PRODIST (Marinho et al., 2026)
    # Filtra valores válidos de tensão (>= 0.1 pu), ignorando fases inexistentes (0V)
    v1_cols = [c for c in cols_map["v1"] if c in df.columns]
    v2_cols = [c for c in cols_map["v2"] if c in df.columns]
    v3_cols = [c for c in cols_map["v3"] if c in df.columns]

    v1 = df[v1_cols].where(df[v1_cols] >= 0.1, np.nan)
    v2 = df[v2_cols].where(df[v2_cols] >= 0.1, np.nan)
    v3 = df[v3_cols].where(df[v3_cols] >= 0.1, np.nan)

    v_all = pd.concat([v1.stack(), v2.stack(), v3.stack()])
    v_min_global = float(v_all.min())
    v_med_global = float(v_all.mean())

    # Indicadores DRP e DRC por barra
    def calcular_drp_drc(df_fase):
        passos_validos = df_fase.count(axis=0).replace(0, np.nan)

        m_prec_sub = (df_fase >= 0.87) & (df_fase < 0.92)
        m_prec_sob = (df_fase > 1.05) & (df_fase <= 1.06)
        m_crit_sub = df_fase < 0.87
        m_crit_sob = df_fase > 1.06

        drp_sub = (m_prec_sub.sum(axis=0) / passos_validos) * 100.0
        drp_sob = (m_prec_sob.sum(axis=0) / passos_validos) * 100.0
        drc_sub = (m_crit_sub.sum(axis=0) / passos_validos) * 100.0
        drc_sob = (m_crit_sob.sum(axis=0) / passos_validos) * 100.0

        return drp_sub.dropna(), drp_sob.dropna(), drc_sub.dropna(), drc_sob.dropna()

    drp_sub1, drp_sob1, drc_sub1, drc_sob1 = calcular_drp_drc(v1)
    drp_sub2, drp_sob2, drc_sub2, drc_sob2 = calcular_drp_drc(v2)
    drp_sub3, drp_sob3, drc_sub3, drc_sob3 = calcular_drp_drc(v3)

    drp_sub_total = pd.concat([drp_sub1, drp_sub2, drp_sub3])
    drp_sob_total = pd.concat([drp_sob1, drp_sob2, drp_sob3])
    drc_sub_total = pd.concat([drc_sub1, drc_sub2, drc_sub3])
    drc_sob_total = pd.concat([drc_sob1, drc_sob2, drc_sob3])

    drp_total = drp_sub_total + drp_sob_total
    drc_total = drc_sub_total + drc_sob_total

    n_barras_violam_drp = int((drp_total > 3.0).sum())
    n_barras_violam_drc = int((drc_total > 0.5).sum())
    n_barras_violam_drc_sub = int((drc_sub_total > 0.5).sum())

    # 2. VDI (Nwobu et al., 2026)
    dev_v1 = (v1 - 1.0).fillna(0)
    dev_v2 = (v2 - 1.0).fillna(0)
    dev_v3 = (v3 - 1.0).fillna(0)

    vdi_mat_total = (dev_v1 ** 2).sum(axis=1) + (dev_v2 ** 2).sum(axis=1) + (dev_v3 ** 2).sum(axis=1)
    vdi_sob_t = (np.maximum(0, dev_v1)**2).sum(axis=1) + (np.maximum(0, dev_v2)**2).sum(axis=1) + (np.maximum(0, dev_v3)**2).sum(axis=1)
    vdi_sub_t = (np.maximum(0, -dev_v1)**2).sum(axis=1) + (np.maximum(0, -dev_v2)**2).sum(axis=1) + (np.maximum(0, -dev_v3)**2).sum(axis=1)

    vdi_total_acum = float(vdi_mat_total.sum())
    vdi_sob_acum = float(vdi_sob_t.sum())
    vdi_sub_acum = float(vdi_sub_t.sum())
    n_leituras = float(v_all.count())
    vdi_rms_pct = float(np.sqrt(vdi_total_acum / n_leituras) * 100.0) if n_leituras > 0 else 0.0

    # 3. Potência e Demanda da Linha Tronco
    # Suporta passar a lista direta de colunas ou o identificador da linha tronco
    if isinstance(nome_tronco, list) and len(nome_tronco) > 0:
        tronco_cols = [c for c in nome_tronco if c in df.columns]
    elif isinstance(nome_tronco, str) and nome_tronco:
        tronco_cols = [c for c in df.columns if f"Line-{nome_tronco}-" in c and any(p in c for p in ["P1_w", "P2_w", "P3_w"])]
    else:
        tronco_cols = [c for c in df.columns if "smt_1071706" in c and any(p in c for p in ["P1_w", "P2_w", "P3_w"])]
    
    if not tronco_cols:
        tronco_cols = [c for c in df.columns if "Line" in c and any(p in c for p in ["P1_w", "P2_w", "P3_w"])][:3]

    p_tronco_kw = df[tronco_cols].sum(axis=1).abs()
    p_max_kw = float(p_tronco_kw.max())
    p_med_kw = float(p_tronco_kw.mean())
    fc_tronco = float(p_med_kw / p_max_kw) if p_max_kw > 0 else 0.0
    energia_tronco_kwh = float((p_tronco_kw * delta_t_h).sum())

    # 4. Potência de VEs (CalderaEV)
    ev_cols = [c for c in df.columns if "CalderaEV" in c and "-P" in c]
    energia_ves_kwh = float((df[ev_cols].sum(axis=1).abs() * delta_t_h).sum()) if ev_cols else 0.0

    return {
        "p_max_kw": p_max_kw,
        "p_med_kw": p_med_kw,
        "fc": fc_tronco,
        "energia_tronco_kwh": energia_tronco_kwh,
        "energia_ves_kwh": energia_ves_kwh,
        "v_min_global": v_min_global,
        "v_med_global": v_med_global,
        "drp_med": float(drp_total.mean()),
        "drp_sub_med": float(drp_sub_total.mean()),
        "drp_sob_med": float(drp_sob_total.mean()),
        "drc_med": float(drc_total.mean()),
        "drc_sub_med": float(drc_sub_total.mean()),
        "drc_sob_med": float(drc_sob_total.mean()),
        "n_barras_violam_drp": n_barras_violam_drp,
        "n_barras_violam_drc": n_barras_violam_drc,
        "n_barras_violam_drc_sub": n_barras_violam_drc_sub,
        "vdi_rms_pct": vdi_rms_pct,
        "vdi_total_acum": vdi_total_acum,
        "vdi_sub_acum": vdi_sub_acum,
        "vdi_sob_acum": vdi_sob_acum,
    }


def carregar_e_processar_grade(
    cenarios: List[int] = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    base_calculo: str = "residencial_bt",
    output_dir: Path = OUTPUT_DIR,
) -> pd.DataFrame:
    """
    Carrega o Caso Base e todos os cenários da grade, gerando o DataFrame comparativo relativo.
    """
    arquivo_base = output_dir / "result_TCC_baseline.csv"
    if not arquivo_base.exists():
        raise FileNotFoundError(f"Arquivo do Caso Base não encontrado: {arquivo_base}")

    print("\n" + "=" * 80)
    print(" PROCESSAMENTO DA GRADE DE CENÁRIOS (ANÁLISE DIFERENCIAL E RELATIVA)")
    print("=" * 80)
    print("Lendo estrutura de colunas do Caso Base...")
    df_head = pd.read_csv(arquivo_base, nrows=1)
    cols_map = identificar_colunas_circuito(df_head)

    # Identifica a linha tronco principal (maior corrente e potência, como no Módulo 5 do notebook)
    df_temp = pd.read_csv(arquivo_base, nrows=100)
    def extrair_id_linha(col: str) -> str:
        if "Line-" in col:
            return col.split("Line-")[1].split("-")[0]
        return ""

    nomes_linhas = list({extrair_id_linha(c) for c in cols_map["line_p"] if "Line-" in c})
    nomes_linhas = [l for l in nomes_linhas if l]

    linhas_info = []
    for l in nomes_linhas:
        p_c = [c for c in df_head.columns if f"Line-{l}-" in c and any(p in c for p in ['P1_w', 'P2_w', 'P3_w', 'P1', 'P2', 'P3'])]
        i_c = [c for c in df_head.columns if f"Line-{l}-" in c and any(i in c for i in ['I1_A', 'I2_A', 'I3_A', 'I1_a', 'I2_a', 'I3_a'])]
        if p_c:
            i_max = df_temp[i_c].max().max() if i_c else df_temp[p_c].abs().sum(axis=1).max()
            linhas_info.append({'linha': l, 'p_cols': p_c, 'i_max': i_max})

    df_rank = pd.DataFrame(linhas_info).sort_values(by='i_max', ascending=False)
    linha_tronco = df_rank.iloc[0]
    linha_tronco_p_cols = linha_tronco['p_cols']
    print(f"Linha tronco de entrada identificada: {linha_tronco['linha']} ({len(linha_tronco_p_cols)} fases)")

    # 1. Processa Caso Base
    print("Processando métricas do Caso Base (0 VEs)...")
    metrica_base = extrair_metrica_cenario(arquivo_base, cols_map, linha_tronco_p_cols)

    linhas_relatorio = []
    # Registra Caso Base (C0)
    linhas_relatorio.append({
        "cenario": "Caso Base",
        "penetracao_pct": 0,
        "qtd_evs": 0,
        "p_max_kw": metrica_base["p_max_kw"],
        "delta_p_max_kw": 0.0,
        "pct_delta_p_max": 0.0,
        "fc": metrica_base["fc"],
        "delta_fc": 0.0,
        "energia_tronco_kwh": metrica_base["energia_tronco_kwh"],
        "delta_energia_tronco_kwh": 0.0,
        "pct_delta_energia": 0.0,
        "energia_ves_kwh": 0.0,
        "v_min_pu": metrica_base["v_min_global"],
        "delta_v_min_pu": 0.0,
        "vdi_rms_pct": metrica_base["vdi_rms_pct"],
        "delta_vdi_rms_pct": 0.0,
        "pct_delta_vdi_sub": 0.0,
        "drp_med_pct": metrica_base["drp_med"],
        "drp_sub_med_pct": metrica_base["drp_sub_med"],
        "drc_med_pct": metrica_base["drc_med"],
        "drc_sub_med_pct": metrica_base["drc_sub_med"],
        "delta_drc_sub_pct": 0.0,
        "n_barras_drp": metrica_base["n_barras_violam_drp"],
        "delta_n_barras_drp": 0,
        "n_barras_drc": metrica_base["n_barras_violam_drc"],
        "delta_n_barras_drc": 0,
        "n_barras_drc_sub": metrica_base["n_barras_violam_drc_sub"],
        "delta_n_barras_drc_sub": 0,
    })

    # 2. Processa cada cenário com VEs
    for p in cenarios:
        tag = f"ev_p{p}_{base_calculo}"
        arq_cenario = output_dir / f"result_TCC_{tag}.csv"
        if not arq_cenario.exists():
            print(f"[AVISO]: Arquivo para cenário {p}% não encontrado: {arq_cenario.name}. Pulando...")
            continue

        print(f"Processando cenário {p}% de penetração ({arq_cenario.name})...")
        m = extrair_metrica_cenario(arq_cenario, cols_map, linha_tronco_p_cols)

        delta_p_max = m["p_max_kw"] - metrica_base["p_max_kw"]
        pct_delta_p_max = (delta_p_max / metrica_base["p_max_kw"]) * 100.0 if metrica_base["p_max_kw"] > 0 else 0.0

        delta_energia = m["energia_tronco_kwh"] - metrica_base["energia_tronco_kwh"]
        pct_delta_energia = (delta_energia / metrica_base["energia_tronco_kwh"]) * 100.0 if metrica_base["energia_tronco_kwh"] > 0 else 0.0

        delta_fc = m["fc"] - metrica_base["fc"]
        delta_vmin = m["v_min_global"] - metrica_base["v_min_global"]
        delta_vdi_rms = m["vdi_rms_pct"] - metrica_base["vdi_rms_pct"]

        vdi_sub_base = metrica_base["vdi_sub_acum"]
        pct_delta_vdi_sub = ((m["vdi_sub_acum"] - vdi_sub_base) / vdi_sub_base) * 100.0 if vdi_sub_base > 0 else 0.0

        delta_drc_sub = m["drc_sub_med"] - metrica_base["drc_sub_med"]
        delta_n_drp = m["n_barras_violam_drp"] - metrica_base["n_barras_violam_drp"]
        delta_n_drc = m["n_barras_violam_drc"] - metrica_base["n_barras_violam_drc"]
        delta_n_drc_sub = m["n_barras_violam_drc_sub"] - metrica_base["n_barras_violam_drc_sub"]

        # Qtd de VEs aproximada
        qtd_evs = round(947 * (p / 100.0))

        linhas_relatorio.append({
            "cenario": f"{p}% VEs",
            "penetracao_pct": p,
            "qtd_evs": qtd_evs,
            "p_max_kw": m["p_max_kw"],
            "delta_p_max_kw": delta_p_max,
            "pct_delta_p_max": pct_delta_p_max,
            "fc": m["fc"],
            "delta_fc": delta_fc,
            "energia_tronco_kwh": m["energia_tronco_kwh"],
            "delta_energia_tronco_kwh": delta_energia,
            "pct_delta_energia": pct_delta_energia,
            "energia_ves_kwh": m["energia_ves_kwh"],
            "v_min_pu": m["v_min_global"],
            "delta_v_min_pu": delta_vmin,
            "vdi_rms_pct": m["vdi_rms_pct"],
            "delta_vdi_rms_pct": delta_vdi_rms,
            "pct_delta_vdi_sub": pct_delta_vdi_sub,
            "drp_med_pct": m["drp_med"],
            "drp_sub_med_pct": m["drp_sub_med"],
            "drc_med_pct": m["drc_med"],
            "drc_sub_med_pct": m["drc_sub_med"],
            "delta_drc_sub_pct": delta_drc_sub,
            "n_barras_drp": m["n_barras_violam_drp"],
            "delta_n_barras_drp": delta_n_drp,
            "n_barras_drc": m["n_barras_violam_drc"],
            "delta_n_barras_drc": delta_n_drc,
            "n_barras_drc_sub": m["n_barras_violam_drc_sub"],
            "delta_n_barras_drc_sub": delta_n_drc_sub,
        })

    df_resultado = pd.DataFrame(linhas_relatorio)

    # Exporta tabela consolidada
    csv_saida = output_dir / "tabela_comparativa_relativa_tcc.csv"
    json_saida = output_dir / "tabela_comparativa_relativa_tcc.json"
    df_resultado.to_csv(csv_saida, index=False, encoding="utf-8")
    with open(json_saida, "w", encoding="utf-8") as f:
        json.dump(df_resultado.to_dict(orient="records"), f, indent=2, ensure_ascii=False)

    print(f"\nProcessamento concluído com sucesso!")
    print(f"Tabela CSV salva em : {csv_saida}")
    print(f"Tabela JSON salva em: {json_saida}")

    return df_resultado


def plotar_curvas_sensibilidade_relativa(
    df_resumo: pd.DataFrame,
    figuras_dir: Path = FIGURAS_DIR,
):
    """
    Gera as figuras acadêmicas em alta resolução (300 DPI) com métricas relativas.
    """
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
    })

    p_pct = df_resumo["penetracao_pct"].values

    # -------------------------------------------------------------------------
    # FIGURA 1: Impacto Relativo no Pico e na Energia vs. Penetração
    # -------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(9, 5.5), dpi=300)

    color1 = "#b30000"  # Vermelho escuro
    color2 = "#004080"  # Azul escuro

    ax1.set_xlabel("Taxa de Penetração de Veículos Elétricos (%)", fontweight="bold")
    ax1.set_ylabel("Acréscimo Relativo no Pico de Demanda (%ΔP_max)", color=color1, fontweight="bold")
    line1 = ax1.plot(
        p_pct, df_resumo["pct_delta_p_max"],
        marker="o", color=color1, linewidth=2.0, markersize=6, label="%Δ Pico de Demanda (kW)"
    )
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=1))

    ax2 = ax1.twinx()
    ax2.set_ylabel("Acréscimo Relativo na Energia Entregue (%ΔE)", color=color2, fontweight="bold")
    line2 = ax2.plot(
        p_pct, df_resumo["pct_delta_energia"],
        marker="s", color=color2, linewidth=2.0, linestyle="--", markersize=6, label="%Δ Energia Semanal (kWh)"
    )
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=1))

    ax1.set_xticks(p_pct)
    ax1.grid(True, linestyle=":", alpha=0.6)
    
    # Legenda combinada
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", frameon=True)

    plt.title("Sensibilidade da Demanda Agregada Relativa ao Caso Base (ESB01S4)", fontweight="bold", pad=12)
    plt.tight_layout()
    fig1_path = figuras_dir / "fig1_impacto_relativo_pico_energia.png"
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"Salvo: {fig1_path.name}")

    # -------------------------------------------------------------------------
    # FIGURA 2: Capacidade de Hospedagem (Hosting Capacity) e Novas Transgressões PRODIST
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    ax.plot(
        p_pct, df_resumo["delta_n_barras_drc_sub"],
        marker="^", color="#d95f02", linewidth=2.2, markersize=7,
        label="Novas Barras em Tensão Crítica por Subtensão (ΔN DRC_sub)"
    )
    ax.plot(
        p_pct, df_resumo["delta_n_barras_drp"],
        marker="d", color="#7570b3", linewidth=1.8, linestyle="--", markersize=6,
        label="Novas Barras em Tensão Precária (ΔN DRP)"
    )

    ax.set_xlabel("Taxa de Penetração de Veículos Elétricos (%)", fontweight="bold")
    ax.set_ylabel("Quantidade Incremental de Barras Não Conformes (ΔN)", fontweight="bold")
    ax.set_xticks(p_pct)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", frameon=True)

    # Identifica o limiar de Hosting Capacity
    idx_hc = df_resumo[df_resumo["delta_n_barras_drc_sub"] > 0].index
    if len(idx_hc) > 0:
        p_hc = df_resumo.loc[idx_hc[0], "penetracao_pct"]
        ax.axvline(p_hc, color="red", linestyle=":", linewidth=1.8, label=f"Limiar de Hosting Capacity ({p_hc}%)")
        ax.annotate(
            f"Limiar Crítico\nde BT ({p_hc}%)",
            xy=(p_hc, df_resumo.loc[idx_hc[0], "delta_n_barras_drc_sub"]),
            xytext=(p_hc + 3, df_resumo.loc[idx_hc[0], "delta_n_barras_drc_sub"] + 15),
            arrowprops=dict(facecolor="black", shrink=0.08, width=1, headwidth=6),
            fontweight="bold", color="#990000"
        )

    plt.title("Capacidade de Hospedagem (Hosting Capacity): Novas Transgressões PRODIST Módulo 8", fontweight="bold", pad=12)
    plt.tight_layout()
    fig2_path = figuras_dir / "fig2_hosting_capacity_novas_barras_prodist.png"
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print(f"Salvo: {fig2_path.name}")

    # -------------------------------------------------------------------------
    # FIGURA 3: Degradação Relativa do VDI de Subtensão vs. Sobretensão
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    ax.plot(
        p_pct[1:], df_resumo["pct_delta_vdi_sub"].values[1:],
        marker="o", color="#e41a1c", linewidth=2.2, markersize=7,
        label="%Δ VDI de Subtensão Noturna (Distúrbio VEs)"
    )

    ax.set_xlabel("Taxa de Penetração de Veículos Elétricos (%)", fontweight="bold")
    ax.set_ylabel("Crescimento Relativo do VDI de Subtensão (%Δ)", fontweight="bold")
    ax.set_xticks(p_pct)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(decimals=0))
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", frameon=True)

    plt.title("Agravamento do Desvio de Tensão Noturno (VDI Subtensão - Nwobu et al., 2026)", fontweight="bold", pad=12)
    plt.tight_layout()
    fig3_path = figuras_dir / "fig3_vdi_subtensao_relativo.png"
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print(f"Salvo: {fig3_path.name}")

    # -------------------------------------------------------------------------
    # FIGURA 4: Afundamento da Tensão Mínima Global (ΔV_min)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    ax.plot(
        p_pct, df_resumo["v_min_pu"],
        marker="o", color="#2c7bb6", linewidth=2.0, markersize=7,
        label="Tensão Mínima Global Nodal (V_min)"
    )
    ax.axhline(0.92, color="orange", linestyle="--", linewidth=1.5, label="Limite Inferior Tensão Adequada (0.92 pu)")
    ax.axhline(0.87, color="red", linestyle=":", linewidth=1.8, label="Limite Inferior Tensão Precária / Crítica (0.87 pu)")

    ax.set_xlabel("Taxa de Penetração de Veículos Elétricos (%)", fontweight="bold")
    ax.set_ylabel("Tensão Mínima do Alimentador (pu)", fontweight="bold")
    ax.set_xticks(p_pct)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower left", frameon=True)

    plt.title("Degradação da Tensão Mínima Global em Regime Permanente (PRODIST Módulo 8)", fontweight="bold", pad=12)
    plt.tight_layout()
    fig4_path = figuras_dir / "fig4_tensao_minima_global_prodist.png"
    plt.savefig(fig4_path, dpi=300)
    plt.close()
    print(f"Salvo: {fig4_path.name}")


if __name__ == "__main__":
    df_resumo = carregar_e_processar_grade()
    plotar_curvas_sensibilidade_relativa(df_resumo)

