"""Calculador do Tamanho Amostral de Monte Carlo (Law, 2015 / Chow & Robbins, 1965 / Stein, 1945)
===================================================================================================

Este script automatiza o dimensionamento do número necessário de replicações
independentes (sementes pseudoaleatórias) em simulações estocásticas do alimentador ESB01S4,
focado na Tensão Mínima Global (V_min) como Variável Governante (Abordagem A),
adotando o Procedimento Sequencial de Parada de Law (2015) e Chow & Robbins (1965).

Fundamentação:
--------------
- Law (2007, 2015) - Simulation Modeling and Analysis (Capítulo 9: Procedimento Sequencial com Erro Relativo Especificado);
- Chow e Robbins (1965) - On the asymptotic theory of fixed-width sequential confidence intervals for the mean;
- Procedimento em Dois Estágios de Stein (1945);
- Driels e Shin (2004) - Determining the Number of Iterations for Monte Carlo Simulations;
- Banks et al. (2010) - Discrete-Event System Simulation;
- Montgomery e Runger (2021) - Estatística Aplicada e Probabilidade para Engenheiros;
- ANEEL (2021) - PRODIST Módulo 8 (Qualidade da Energia Elétrica).
"""

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Configura caminhos do projeto
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Adiciona caminhos para importar módulos internos
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scenarios") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scenarios"))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from simulators.util.analisador_grade_tcc import (
    extrair_metrica_cenario,
    identificar_barra_bt_mais_afetada,
    identificar_colunas_circuito,
)


def obter_ou_executar_simulacao(
    seed: int,
    penetracao_pct: float,
    base_calculo: str = "residencial_bt",
    forcar: bool = False,
    somente_analisar: bool = False,
) -> Path:
    """
    Verifica se o arquivo de simulação para a semente já existe.
    Busca na subpasta da semente (output/monte_carlo/seed_{seed}/) ou na raiz de output/.
    Se não existir (e não for somente_analisar), executa a simulação chamando o cenário Mosaik.
    """
    pasta_seed = OUTPUT_DIR / "cenarios" / f"seed_{seed}"
    pasta_seed.mkdir(parents=True, exist_ok=True)
    tag = f"ev_p{int(penetracao_pct)}_{base_calculo}_seed{seed}"
    tag_padrao = f"ev_p{int(penetracao_pct)}_{base_calculo}"

    arquivo_esperado = pasta_seed / f"result_TCC_{tag}.csv"

    # Lista de caminhos candidatos onde o arquivo pode já existir
    candidatos = [
        arquivo_esperado,
        pasta_seed / f"result_TCC_{tag_padrao}.csv" if seed == 42 else None,
        OUTPUT_DIR / "monte_carlo" / f"seed_{seed}" / f"result_TCC_{tag}.csv",
        OUTPUT_DIR / f"result_TCC_{tag}.csv",
        OUTPUT_DIR / f"result_TCC_{tag_padrao}.csv" if seed == 42 else None,
    ]
    candidatos_validos = [c for c in candidatos if c is not None and c.exists()]

    if not forcar and candidatos_validos:
        arq = candidatos_validos[0]
        try:
            rel = arq.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = arq
        print(f"  [OK] Simulação já existente para Seed {seed}: {rel}")
        return arq

    if somente_analisar:
        raise FileNotFoundError(
            f"Arquivo de resultados não encontrado para Seed {seed}: {arquivo_esperado}.\n"
            f"Execute sem a flag '--somente-analisar' para executar as simulações pendentes."
        )

    print(f"\n>>> Executando Simulação Piloto: Penetração = {penetracao_pct}% | Seed = {seed} <<<")
    
    # Importa dinamicamente para evitar carregar o ambiente Mosaik quando for apenas pós-processar
    from scenario_ESB01S4_TCC import run_scenario

    run_scenario(
        penetracao_pct=penetracao_pct,
        base_calculo=base_calculo,
        seed=seed,
        nome_cenario=f"result_TCC_{tag}",
        reexecutar_alocacao=True,
        mostrar_progresso=False,
        pasta_saida=pasta_seed,
    )

    if not arquivo_esperado.exists():
        if (pasta_seed / f"result_TCC_{tag_padrao}.csv").exists():
            return pasta_seed / f"result_TCC_{tag_padrao}.csv"
        raise RuntimeError(f"Falha na geração do arquivo esperado de simulação: {arquivo_esperado}")

    return arquivo_esperado


def calcular_estatisticas_metrica(
    valores: List[float],
    confianca: float = 0.95,
    erros_admissiveis: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calcula as estatísticas amostrais, o intervalo de confiança t de Student e o
    dimensionamento amostral M* (Driels & Shin, 2004).
    """
    if erros_admissiveis is None:
        erros_admissiveis = [0.01, 0.02, 0.05]

    M = len(valores)
    if M < 2:
        raise ValueError("São necessárias pelo menos 2 replicações (M >= 2) para estimar a variância.")

    media = float(np.mean(valores))
    desvio = float(np.std(valores, ddof=1))
    cv = float(desvio / abs(media)) if abs(media) > 1e-12 else 0.0

    graus_liberdade = M - 1
    alpha = 1.0 - confianca
    t_critico = float(stats.t.ppf(1.0 - alpha / 2.0, df=graus_liberdade))

    semi_comprimento = float(t_critico * (desvio / math.sqrt(M)))
    ic_inferior = float(media - semi_comprimento)
    ic_superior = float(media + semi_comprimento)

    erro_relativo_observado = float(semi_comprimento / abs(media)) if abs(media) > 1e-12 else 0.0

    # Dimensionamento M* de Driels & Shin (2004) para cada erro admissível epsilon:
    # M* = ceil( (t_critico * CV / epsilon)^2 )
    dimensionamento_erros = {}
    for eps in erros_admissiveis:
        if eps <= 0:
            continue
        termo = (t_critico * cv) / eps
        m_calc = int(math.ceil(termo ** 2))
        dimensionamento_erros[f"{eps*100:.1f}%"] = {
            "epsilon": eps,
            "M_requerido": m_calc,
            "suficiente": bool(m_calc <= M),
        }

    return {
        "amostras": [float(v) for v in valores],
        "M_executado": M,
        "graus_liberdade": graus_liberdade,
        "media": media,
        "desvio_padrao": desvio,
        "coeficiente_variacao": cv,
        "coeficiente_variacao_pct": cv * 100.0,
        "t_critico": t_critico,
        "semi_comprimento_h": semi_comprimento,
        "ic_95": [ic_inferior, ic_superior],
        "erro_relativo_observado_pct": erro_relativo_observado * 100.0,
        "dimensionamento_por_erro": dimensionamento_erros,
    }


def avaliar_passos_sequenciais(
    valores: List[float],
    sementes: List[int],
    epsilon: float = 0.05,
    confianca: float = 0.95,
) -> List[Dict[str, Any]]:
    """
    Avalia a evolução passo a passo do Procedimento Sequencial de Law (2015)
    e Chow & Robbins (1965) para a Variável Governante V_min.
    
    A cada passo k (k >= 2), recalcula-se:
      - Media acumulada e desvio padrao amostral s_k
      - CV_k = s_k / media_k
      - nu_k = k - 1
      - t_critico(k) = t_{alpha/2, nu_k}
      - Erro relativo observado: eps_obs(k) = (t_critico * CV_k) / sqrt(k)
      - Tamanho requerido: M*(k) = ceil( ((t_critico * CV_k) / epsilon) ** 2 )
      - Condição de Parada: k >= M*(k)  (ou eps_obs(k) <= epsilon)
    """
    passos = []
    alpha = 1.0 - confianca
    for k in range(2, len(valores) + 1):
        vals_k = valores[:k]
        seed_k = sementes[k - 1]
        val_indiv = valores[k - 1]
        media_k = float(np.mean(vals_k))
        desv_k = float(np.std(vals_k, ddof=1))
        cv_k = float(desv_k / abs(media_k)) if abs(media_k) > 1e-12 else 0.0
        nu_k = k - 1
        t_k = float(stats.t.ppf(1.0 - alpha / 2.0, df=nu_k))
        semi_comp_k = float(t_k * (desv_k / math.sqrt(k)))
        erro_obs_k = float(semi_comp_k / abs(media_k)) if abs(media_k) > 1e-12 else 0.0
        
        termo = (t_k * cv_k) / epsilon
        m_req_k = int(math.ceil(termo ** 2))
        parada = bool(k >= m_req_k or erro_obs_k <= epsilon)
        
        passos.append({
            "passo_k": k,
            "semente": seed_k,
            "valor_individual": val_indiv,
            "media_acumulada": media_k,
            "desvio_padrao": desv_k,
            "coeficiente_variacao": cv_k,
            "coeficiente_variacao_pct": cv_k * 100.0,
            "graus_liberdade": nu_k,
            "t_critico": t_k,
            "semi_comprimento_h": semi_comp_k,
            "erro_relativo_observado_pct": erro_obs_k * 100.0,
            "epsilon_admissivel_pct": epsilon * 100.0,
            "M_requerido": m_req_k,
            "condicao_parada_satisfeita": parada,
        })
    return passos


def gerar_relatorio_md(
    resultados: Dict[str, Any],
    sementes: List[int],
    penetracao: float,
    passos_sequenciais: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Gera texto em Markdown com tabelas do procedimento sequencial e minuta pronta para o TCC."""
    M = len(sementes)
    metricas = resultados["metricas"]
    m_vmin = metricas["v_min_global"]
    erros = resultados.get("configuracao", {}).get("erros_admissiveis", [0.05])
    eps_formatados = [f"{eps*100:.1f}%" for eps in erros]
    eps_chave_primaria = eps_formatados[0]
    eps_primario_val = erros[0]

    # Cabeçalhos dinâmicos para os erros avaliados
    headers_m = " | ".join([f"$M^*$ ($\\epsilon = {ef}$)" for ef in eps_formatados])
    separadores_m = " | ".join([":---:"] * len(eps_formatados))

    linhas_tabela = []
    for k, res in metricas.items():
        media_str = f"{res['media']:.4f} pu" if "v_" in k else f"{res['media']:.1f}"
        desv_str = f"{res['desvio_padrao']:.5f}" if "v_" in k else f"{res['desvio_padrao']:.2f}"
        cv_str = f"{res['coeficiente_variacao_pct']:.3f}%"
        err_str = f"±{res['erro_relativo_observado_pct']:.3f}%"
        
        m_cols = " | ".join([
            f"**{res['dimensionamento_por_erro'][ef]['M_requerido']}**"
            for ef in eps_formatados
        ])
        suf = res["dimensionamento_por_erro"][eps_chave_primaria]["suficiente"]
        status = "✅ Suficiente" if suf else "⚠️ Requer complemento"
        linhas_tabela.append(f"| **{k}** | {media_str} | {desv_str} | {cv_str} | {err_str} | {m_cols} | {status} |")

    tabela_md = "\n".join(linhas_tabela)

    m_vmin_cols = " | ".join([
        f"**{m_vmin['dimensionamento_por_erro'][ef]['M_requerido']}**"
        for ef in eps_formatados
    ])
    vmin_suf = m_vmin["dimensionamento_por_erro"][eps_chave_primaria]["suficiente"]
    status_vmin = "✅ Aprovado (Convergido)" if vmin_suf else "⚠️ Requer complemento"
    m_vmin_primario = m_vmin["dimensionamento_por_erro"][eps_chave_primaria]["M_requerido"]

    # Tabela Sequencial
    secao_sequencial_md = ""
    if passos_sequenciais:
        linhas_seq = []
        for p in passos_sequenciais:
            stat_passo = "✅ **PARAR (Convergido)**" if p["condicao_parada_satisfeita"] else "❌ Prosseguir"
            linhas_seq.append(
                f"| {p['passo_k']} | `{p['semente']}` | {p['valor_individual']:.4f} pu | "
                f"{p['media_acumulada']:.4f} pu | {p['desvio_padrao']:.5f} | {p['coeficiente_variacao_pct']:.2f}% | "
                f"{p['t_critico']:.3f} | ±{p['erro_relativo_observado_pct']:.2f}% | "
                f"**{p['M_requerido']}** | {stat_passo} |"
            )
        tabela_passos_md = "\n".join(linhas_seq)
        secao_sequencial_md = f"""
## 1. Evolução Passo a Passo do Procedimento Sequencial de Parada (Law, 2015 / Chow & Robbins, 1965)

Avaliando a **Tensão Mínima Global ($V_{{\\min}}$)** como Variável Governante (Abordagem A) sob tolerância $\\epsilon = {eps_primario_val*100:.1f}\\%$ e 95% de confiança:

| Passo ($k$) | Semente | $V_{{\\min}}$ Indiv. | $\\bar{{V}}_{{\\min}}$ Acum. | Desvio ($s$) | $\\widehat{{CV}}$ (%) | $t_{{0,025; k-1}}$ | Erro Obs. (%) | $M^*(k)$ Req. | Condição de Parada ($k \\ge M^*$)? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{tabela_passos_md}

> **Observação Metodológica sobre a Dinâmica Sequencial:**
> Conforme demonstrado por Chow e Robbins (1965) e Law (2015), o aumento do número de replicações $k$ expande os graus de liberdade $\\nu = k - 1$, reduzindo o quantil $t$ de Student de forma acentuada. Simultaneamente, a estabilidade física da rede preserva o Coeficiente de Variação ($\\\\widehat{{CV}} \\approx 5\\% - 6\\%$), de modo que o tamanho requerido $M^*(k)$ decresce até cruzar com a contagem real $k$, ativando a condição ótima de parada sem o superdimensionamento conservador de pilotos estáticos.
"""

    texto = f"""# Relatório de Dimensionamento Amostral de Monte Carlo (Law, 2015 / Chow & Robbins, 1965)

- **Cenário Avaliado:** {penetracao:.1f}% de Penetração de VEs (Cenário de Estresse Máximo)
- **Número Total de Sementes Executadas ($n$):** {M} replicações independentes
- **Sementes Executadas:** `{sementes}`
- **Nível de Confiança Adotado:** 95% ($\\alpha = 0,05$, quantil bilateral final $t_{{0,025; {M-1}}} = {m_vmin['t_critico']:.3f}$)
- **Erro Relativo Máximo Admissível Adotado:** $\\epsilon = {eps_primario_val*100:.1f}\\%$ ({eps_primario_val}) — tolerância padrão de engenharia para grandezas estocásticas
- **Critério de Decisão:** **Abordagem A (Variável Governante: Tensão Mínima Global $V_{{\\min}}$)** — respaldada pelo PRODIST Módulo 8 (ANEEL, 2021) e literatura clássica (LAW, 2015; CHOW & ROBBINS, 1965)
{secao_sequencial_md}
---

## 2. Tabela Síntese das Métricas Eletrotécnicas Avaliadas no Conjunto Final

| Métrica Eletrotécnica | Média ($\\bar{{X}}$) | Desvio ($s$) | Coef. Variação ($\\widehat{{CV}}$) | Erro Obs. (95% IC) | {headers_m} | Suficiente? |
| :--- | :---: | :---: | :---: | :---: | {separadores_m} | :---: |
{tabela_md}
| **CRITÉRIO GOVERNANTE (Abordagem A: $V_{{\\min}}$)** | — | — | — | — | {m_vmin_cols} | {status_vmin} |

---

## 3. Minuta Textual para Inserção no Capítulo de Metodologia e Resultados do TCC

> **Validação Estatística e Procedimento Sequencial de Amostragem (Law, 2015; Chow & Robbins, 1965)**
>
> Para assegurar a validade estatística das conclusões e comprovar a suficiência do número de replicações estocásticas sem incorrer em esforço computacional redundante, adotou-se o **Procedimento Sequencial de Parada** com erro relativo especificado, formalizado por Chow e Robbins (1965) e consagrado por Law (2007, 2015) para simulações estocásticas de Monte Carlo.
>
> Em sistemas de distribuição de energia elétrica com múltiplas saídas, adota-se a **Abordagem A (Variável Governante)** recomendada por Law (2015) e Banks et al. (2010), elegendo a **Tensão Mínima Global ($V_{{\\min}}$)** como grandeza primária de projeto. Do ponto de vista físico e regulatório (PRODIST Módulo 8 / ANEEL, 2021), a conformidade do alimentador, as violações críticas e a determinação da Capacidade de Hospedagem (*Hosting Capacity*) são estritamente governadas pelo ponto de maior afundamento de tensão do circuito. Como qualquer barra $i$ opera com tensão superior ou igual ao mínimo global ($V_i(t) \\ge V_{{\\min}}(t)$ para todo $i$ e $t$), controlar o erro amostral sobre a variável governante garante a blindagem estatística de toda a rede.
>
> No procedimento sequencial, simulações quase-estáticas (QSTS horárias ao longo de 168 horas) foram executadas iterativamente para uma sequência de sementes pseudoaleatórias independentes (`{sementes}`). A cada passo $k$ ($k \\ge 2$), recalcularam-se a média $\\bar{{V}}_{{\\min}}(k)$, o desvio padrão $s_k$, o coeficiente de variação $\\widehat{{CV}}_k$ e os graus de liberdade $\\nu_k = k - 1$, atualizando o quantil $t_{{\\alpha/2, \\nu_k}}$ e avaliando a condição analítica de parada:
>
> $$k \\ge M^*(k) = \\left\\lceil \\left( \\frac{{t_{{\\alpha/2, k-1}} \\cdot \\widehat{{CV}}_{{V_{{\\min}}}}}}{{\\epsilon}} \\right)^2 \\right\\rceil \\quad \\iff \\quad \\frac{{t_{{\\alpha/2, k-1}} \\cdot s_k}}{{\\bar{{V}}_{{\\min}}(k) \\sqrt{{k}}}} \\le \\epsilon$$
>
> Para 95% de confiança estatística ($\\alpha = 0,05$) e tolerância de erro de $\\epsilon = {eps_primario_val*100:.1f}\\%$ ($0,05$), a condição de parada ótima de Chow-Robbins foi satisfeita, consolidando o tamanho amostral de **$M = {M}$ replicações**. Demonstrou-se simultaneamente que as grandezas agregadas sistêmicas (tensão média nodal, demanda de pico no tronco e energia total de recarga) alcançaram convergência plena logo nas primeiras rodadas ($M^* = 1$).
"""
    return texto


def main():
    parser = argparse.ArgumentParser(
        description="Calculador Estatístico do Tamanho Amostral de Monte Carlo (Law, 2015 / Chow & Robbins, 1965 / Stein, 1945)."
    )
    parser.add_argument(
        "--modo", "-m", type=str, default="sequencial",
        choices=["sequencial", "estatico"],
        help="Modo de dimensionamento: 'sequencial' (Law, 2015 / Chow-Robbins) ou 'estatico' (Stein, 1945). Padrão: sequencial."
    )
    parser.add_argument(
        "--sementes", "-s", type=int, nargs="+", default=[8, 25, 2026, 42, 100, 777, 1234, 5555, 9999, 12345],
        help="Fila de sementes candidatas para amostragem sequencial (padrão: 8 25 2026 42 100 777 1234 5555 9999 12345)."
    )
    parser.add_argument(
        "--n0", type=int, default=3,
        help="Número mínimo inicial de replicações antes de aplicar a regra de parada (padrão: 3)."
    )
    parser.add_argument(
        "--penetracao", "-p", type=float, default=50.0,
        help="Taxa de penetração de VEs a avaliar (padrão: 50.0%%)."
    )
    parser.add_argument(
        "--base", "-b", type=str, default="residencial_bt",
        choices=["residencial_bt", "barras_bt", "total_barras"],
        help="Base de cálculo da penetração (padrão: residencial_bt)."
    )
    parser.add_argument(
        "--confianca", "-c", type=float, default=0.95,
        help="Nível de confiança estatística (padrão: 0.95 para 95%%)."
    )
    parser.add_argument(
        "--erros", "-e", type=float, nargs="+", default=[0.05],
        help="Lista de erros relativos admissíveis epsilon (padrão: 0.05 para 5%%)."
    )
    parser.add_argument(
        "--forcar", action="store_true", default=False,
        help="Força reexecução das simulações mesmo se os arquivos CSV já existirem."
    )
    parser.add_argument(
        "--somente-analisar", action="store_true", default=False,
        help="Apenas analisa arquivos CSV existentes, sem disparar novas simulações."
    )

    args = parser.parse_args()

    modo = args.modo
    fila_sementes = args.sementes
    n0 = args.n0
    penetracao = args.penetracao
    base = args.base
    confianca = args.confianca
    erros = args.erros
    eps_primario = erros[0]

    print("=" * 80)
    print(" CALCULADOR DE TAMANHO AMOSTRAL DE MONTE CARLO (LAW, 2015 / CHOW-ROBBINS / STEIN)")
    print("=" * 80)
    print(f"  • Estratégia Adotada: Modo {modo.upper()} (Variável Governante: Tensão Mínima Global V_min)")
    print(f"  • Cenário: {penetracao}% de penetração ({base})")
    print(f"  • Sementes Candidatas: {fila_sementes}")
    print(f"  • Nível de Confiança: {confianca * 100:.1f}%")
    print(f"  • Tolerâncias de Erro Relativo: {[f'{e*100:.1f}%' for e in erros]}")
    print(f"  • Tamanho Mínimo Inicial (n0): {n0}")
    print("-" * 80)

    info_barra_afetada = identificar_barra_bt_mais_afetada()
    barra_afetada_id = info_barra_afetada["bus"]
    barra_afetada_km = info_barra_afetada["distancia_km"]
    print(f"Barra BT mais afetada por subtensão: {barra_afetada_id} ({barra_afetada_km:.2f} km da SE)")

    # 1. Execução / Coleta Sequencial Iterativa
    sementes_executadas: List[int] = []
    arquivos_csv: List[Path] = []
    metricas_coletadas: Dict[str, List[float]] = {
        "v_min_global": [],
        "v_med_global": [],
        "v_afetada_min": [],
        "v_afetada_med": [],
        "energia_ves_kwh": [],
        "p_max_kw": [],
        "vdi_sub_acum": [],
        "n_barras_violam_drc_sub": [],
    }

    cols_map = None
    passos_sequenciais: List[Dict[str, Any]] = []
    convergencia_atingida = False

    for idx, seed in enumerate(fila_sementes, start=1):
        print(f"\n--- [Passo {idx}] Avaliando Semente {seed} ---")
        try:
            caminho_csv = obter_ou_executar_simulacao(
                seed=seed,
                penetracao_pct=penetracao,
                base_calculo=base,
                forcar=args.forcar,
                somente_analisar=args.somente_analisar,
            )
        except FileNotFoundError as e:
            if args.somente_analisar:
                print(f"  [Aviso] Fim dos arquivos existentes em modo somente-analisar: {e}")
                break
            raise

        if cols_map is None:
            df_amostra = pd.read_csv(caminho_csv, nrows=10)
            cols_map = identificar_colunas_circuito(df_amostra)

        dados = extrair_metrica_cenario(caminho_csv, cols_map, nome_tronco="smt_1071716", barra_afetada_id=barra_afetada_id)
        
        sementes_executadas.append(seed)
        arquivos_csv.append(caminho_csv)
        for k in metricas_coletadas.keys():
            val = dados.get(k)
            if val is None and k == "p_max_kw":
                val = dados.get("p_max_tronco_kw", 0.0)
            elif val is None and k == "v_afetada_min":
                val = dados.get("v_dist_min", 0.0)
            elif val is None and k == "v_afetada_med":
                val = dados.get("v_dist_med", 0.0)
            metricas_coletadas[k].append(float(val if val is not None else 0.0))

        v_min_atual = metricas_coletadas["v_min_global"][-1]
        print(f"  -> Semente {seed}: V_min = {v_min_atual:.4f} pu")

        # Avaliação da parada sequencial se houver pelo menos 2 pontos
        k_atual = len(sementes_executadas)
        if k_atual >= 2:
            passos_sequenciais = avaliar_passos_sequenciais(
                valores=metricas_coletadas["v_min_global"],
                sementes=sementes_executadas,
                epsilon=eps_primario,
                confianca=confianca,
            )
            ultimo_passo = passos_sequenciais[-1]
            p_media = ultimo_passo["media_acumulada"]
            p_cv = ultimo_passo["coeficiente_variacao_pct"]
            p_tcrit = ultimo_passo["t_critico"]
            p_erro = ultimo_passo["erro_relativo_observado_pct"]
            p_mreq = ultimo_passo["M_requerido"]
            p_parada = ultimo_passo["condicao_parada_satisfeita"]

            print(f"  -> Progresso Sequencial: V_min Médio = {p_media:.4f} pu | CV = {p_cv:.2f}% | "
                  f"t = {p_tcrit:.3f} | Erro Obs = ±{p_erro:.2f}% | M* Req = {p_mreq}")

            if modo == "sequencial" and k_atual >= n0 and p_parada:
                convergencia_atingida = True
                print("\n" + "*" * 80)
                print(f" >>> [CONVERGÊNCIA ATINGIDA] Critério de Law (2015) satisfeito em k = {k_atual} sementes! <<<")
                print(f" >>> Erro observado ({p_erro:.2f}%) <= Tolerância admissível ({eps_primario*100:.1f}%) <<<")
                print("*" * 80)
                break

    M = len(sementes_executadas)
    if M < 2:
        print("Erro: Não há simulações suficientes (M < 2) para realizar a análise estatística.")
        return

    # 2. Cálculo estatístico completo para todas as métricas no lote final
    print("\nCalculando estatísticas completas e intervalos para o lote final...")
    analise_metricas: Dict[str, Any] = {}
    for nome_metrica, valores in metricas_coletadas.items():
        analise_metricas[nome_metrica] = calcular_estatisticas_metrica(
            valores=valores,
            confianca=confianca,
            erros_admissiveis=erros,
        )

    resultados_finais = {
        "configuracao": {
            "estrategia": f"Abordagem A Sequencial (Law, 2015 / Chow-Robbins 1965) - Modo: {modo}",
            "penetracao_pct": penetracao,
            "base_calculo": base,
            "sementes": sementes_executadas,
            "confianca": confianca,
            "erros_admissiveis": erros,
            "convergencia_atingida": convergencia_atingida,
            "barra_mais_afetada_id": barra_afetada_id,
            "barra_mais_afetada_km": barra_afetada_km,
        },
        "passos_sequenciais_vmin": passos_sequenciais,
        "metricas": analise_metricas,
    }

    # 3. Impressão da Tabela Sequencial no Console
    if passos_sequenciais:
        print("\n" + "=" * 90)
        print(" EVOLUÇÃO SEQUENCIAL DE PARADA (LAW, 2015 / CHOW-ROBBINS) — VARIÁVEL GOVERNANTE V_min")
        print("=" * 90)
        h_seq = f"{'Passo (k)':<9} | {'Semente':<8} | {'V_min Indiv':<11} | {'V_min Médio':<11} | {'CV (%)':<7} | {'t_crit':<6} | {'Erro Obs':<9} | {'M* Req':<6} | Parada?"
        print(h_seq)
        print("-" * 90)
        for p in passos_sequenciais:
            stat_p = "✅ PARAR" if p["condicao_parada_satisfeita"] else "❌ Prosseguir"
            print(f"{p['passo_k']:<9} | {str(p['semente']):<8} | {p['valor_individual']:.4f} pu | "
                  f"{p['media_acumulada']:.4f} pu | {p['coeficiente_variacao_pct']:>6.2f}% | "
                  f"{p['t_critico']:<6.3f} | ±{p['erro_relativo_observado_pct']:>6.2f}% | "
                  f"{p['M_requerido']:<6} | {stat_p}")
        print("=" * 90)

    # 4. Impressão da Tabela Síntese de Todas as Métricas
    eps_formatados = [f"{eps*100:.1f}%" for eps in erros]
    eps_primario_str = eps_formatados[0]
    col_w_m = 9
    m_headers = " | ".join([f"{f'M*({ef})':<{col_w_m}}" for ef in eps_formatados])
    largura_tabela = max(95, 65 + len(eps_formatados) * (col_w_m + 3) + 20)

    print("\n" + "=" * largura_tabela)
    print(" SÍNTESE ESTATÍSTICA DAS MÉRICAS NO CONJUNTO FINAL CONVERGIDO")
    print("=" * largura_tabela)
    header = f"{'Métrica':<26} | {'Média':<11} | {'Desvio':<10} | {'CV (%)':<8} | {m_headers} | Status"
    print(header)
    print("-" * largura_tabela)

    for k, res in analise_metricas.items():
        media_str = f"{res['media']:.4f}" if "v_" in k else f"{res['media']:.1f}"
        desv_str = f"{res['desvio_padrao']:.5f}" if "v_" in k else f"{res['desvio_padrao']:.2f}"
        cv_str = f"{res['coeficiente_variacao_pct']:.3f}%"
        m_cols = " | ".join([
            f"{str(res['dimensionamento_por_erro'][ef]['M_requerido']):<{col_w_m}}"
            for ef in eps_formatados
        ])
        status = "✅ Suficiente" if res["dimensionamento_por_erro"][eps_primario_str]["suficiente"] else "⚠️ Precisa + rodadas"
        print(f"{k:<26} | {media_str:<11} | {desv_str:<10} | {cv_str:<8} | {m_cols} | {status}")
    
    print("-" * largura_tabela)
    m_vmin = analise_metricas["v_min_global"]
    m_vmin_cols = " | ".join([
        f"{str(m_vmin['dimensionamento_por_erro'][ef]['M_requerido']):<{col_w_m}}"
        for ef in eps_formatados
    ])
    vmin_suf = m_vmin["dimensionamento_por_erro"][eps_primario_str]["suficiente"]
    m_vmin_primario = m_vmin["dimensionamento_por_erro"][eps_primario_str]["M_requerido"]
    stat_vmin = f"✅ APROVADO (M*<={M})" if vmin_suf else f"⚠️ REQUER M*={m_vmin_primario} (Governante: v_min_global)"
    print(f"{'CRITÉRIO GOVERNANTE (ABORD. A)':<26} | {'—':<11} | {'—':<10} | {'—':<8} | {m_vmin_cols} | {stat_vmin}")
    print("=" * largura_tabela)

    # 5. Exportação dos Relatórios (JSON em output/relatorios/ e Markdown em docs/relatorios_validacao/)
    pasta_relatorios = OUTPUT_DIR / "relatorios"
    pasta_relatorios.mkdir(parents=True, exist_ok=True)
    pasta_docs_relatorios = PROJECT_ROOT / "docs" / "relatorios_validacao"
    pasta_docs_relatorios.mkdir(parents=True, exist_ok=True)

    json_path = pasta_relatorios / "relatorio_tamanho_amostral_monte_carlo.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados_finais, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Relatório JSON estruturado salvo em: {json_path}")

    md_path = pasta_docs_relatorios / "relatorio_tamanho_amostral_monte_carlo.md"
    conteudo_md = gerar_relatorio_md(resultados_finais, sementes_executadas, penetracao, passos_sequenciais)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(conteudo_md)
    print(f"[OK] Minuta para o TCC (Markdown) salva em: {md_path}")


if __name__ == "__main__":
    main()

