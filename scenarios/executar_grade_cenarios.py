"""Execução em Lote da Grade Paramétrica de Penetração de VEs (ESB01S4)
=====================================================================

Executa sequencialmente a simulação temporal da grade de penetração de Veículos
Elétricos (0% a 50%, passos de 5%) sobre os domicílios de Baixa Tensão (BT) do
alimentador real ESB01S4 da Enel Distribuição Ceará.

O script oferece:
1. Execução automatizada de cenários para uma ou múltiplas sementes pseudoaleatórias.
2. Isolamento de cada simulação em subprocesso independente, garantindo liberação
   de memória e reset do estado interno das bibliotecas C (OpenDSS e Caldera).
3. Verificação de arquivos pré-existentes para evitar simulações redundantes (com
   opção de re-execução forçada via flag --forcar).
4. Consolidação de métricas de execução e tempos em relatório JSON e tabela em console.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Inclusão da raiz do projeto e do diretório src no sys.path
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for p in [str(PROJECT_ROOT), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scenarios.scenario_ESB01S4_TCC import OUTPUT_DIR

# Grade padrão de simulações (10 cenários de VEs; Caso Base 0% é tratado como baseline)
CENARIOS_PADRAO = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
DOMICILIOS_BT_TOTAL = 670  # 670 UCs BT elegíveis mapeadas no OpenDSS (1.340 objetos _M1/_M2, excluindo IPIP)



def obter_nome_arquivo_cenario(penetracao_pct: float, base_calculo: str, seed: int = 42) -> Path:
    """Retorna o caminho do arquivo CSV de resultados para o cenário e semente informados.

    Verifica locais onde simulações prévias possam ter sido gravadas antes de
    retornar o caminho padrão de destino.
    """
    if penetracao_pct == 0.0:
        pasta_base = OUTPUT_DIR / "cenarios" / "caso_base"
        pasta_base.mkdir(parents=True, exist_ok=True)
        candidatos = [
            pasta_base / "result_TCC_baseline.csv",
            OUTPUT_DIR / "cenarios" / f"seed_{seed}" / f"result_TCC_baseline_seed{seed}.csv",
            OUTPUT_DIR / "cenarios" / f"seed_{seed}" / "result_TCC_baseline.csv",
            OUTPUT_DIR / "cenarios" / "seed_42" / "result_TCC_baseline_seed42.csv",
            OUTPUT_DIR / "monte_carlo" / "caso_base" / "result_TCC_baseline.csv",
            OUTPUT_DIR / "result_TCC_baseline.csv",
        ]
        return next((c for c in candidatos if c.exists()), pasta_base / "result_TCC_baseline.csv")
    
    pasta_seed = OUTPUT_DIR / "cenarios" / f"seed_{seed}"
    pasta_seed.mkdir(parents=True, exist_ok=True)
    tag = f"ev_p{int(penetracao_pct)}_{base_calculo}"
    candidatos = [
        pasta_seed / f"result_TCC_{tag}_seed{seed}.csv",
        pasta_seed / f"result_TCC_{tag}.csv",
        OUTPUT_DIR / "monte_carlo" / f"seed_{seed}" / f"result_TCC_{tag}_seed{seed}.csv",
        OUTPUT_DIR / f"result_TCC_{tag}_seed{seed}.csv",
        OUTPUT_DIR / f"result_TCC_{tag}.csv",
    ]
    arquivo_encontrado = next((c for c in candidatos if c.exists()), None)
    if arquivo_encontrado:
        return arquivo_encontrado
    
    return pasta_seed / f"result_TCC_{tag}_seed{seed}.csv"


def calcular_qtd_evs(penetracao_pct: float, total_domicilios: int = DOMICILIOS_BT_TOTAL) -> int:
    """Calcula o número de veículos elétricos correspondente à taxa de penetração."""
    return round(total_domicilios * (penetracao_pct / 100.0))


def executar_simulacao_subprocesso(
    qtd_evs: Optional[int] = None,
    penetracao_pct: Optional[float] = None,
    base_calculo: str = "residencial_bt",
    seed: int = 42,
    usar_pv_mosaik: bool = True,
    nome_cenario: Optional[str] = None,
    pasta_saida: Optional[Path] = None,
    mostrar_progresso: bool = False,
) -> None:
    """Executa um cenário em subprocesso Python isolado.

    O isolamento em subprocesso assegura que o estado global das bibliotecas
    OpenDSS (Direct-DLL) e Caldera C++ seja limpo pelo sistema operacional ao
    término da rodada, evitando acúmulo de memória e vazamento de ponteiros entre passos.
    """
    script_cenario = CURRENT_DIR / "scenario_ESB01S4_TCC.py"
    cmd = [
        sys.executable,
        str(script_cenario),
        "--base", str(base_calculo),
        "--seed", str(seed),
    ]
    if penetracao_pct is not None:
        cmd.extend(["--penetracao", str(penetracao_pct)])
    if qtd_evs is not None:
        cmd.extend(["--qtd-evs", str(qtd_evs)])
    if not usar_pv_mosaik:
        cmd.append("--sem-pv-mosaik")
    if nome_cenario:
        cmd.extend(["--cenario-nome", str(nome_cenario)])
    if pasta_saida:
        cmd.extend(["--pasta-saida", str(pasta_saida)])
    if mostrar_progresso:
        cmd.append("--progresso")

    subprocess.run(cmd, check=True)


def executar_grade(
    cenarios: List[float],
    base_calculo: str = "residencial_bt",
    sementes: Optional[List[int]] = None,
    seed: Optional[int] = None,
    forcar: bool = False,
    mostrar_progresso: bool = False,
    executar_baseline: bool = True,
    apenas_baseline: bool = False,
    usar_pv_mosaik: bool = True,
) -> Dict:
    """Executa a grade de cenários de penetração de VEs para as sementes especificadas.

    Parâmetros:
    -----------
    cenarios: Lista de percentuais de penetração a simular (ex: [5, 10, ..., 50]).
    base_calculo: Base de referência para cálculo da quantidade de VEs ("residencial_bt").
    sementes: Lista de sementes pseudoaleatórias para simulações de Monte Carlo.
    seed: Semente única (quando fornecida, substitui a lista de sementes).
    forcar: Se True, reexecuta cenários mesmo que o arquivo CSV já exista no disco.
    mostrar_progresso: Se True, habilita exibição do progresso temporal do Mosaik.
    executar_baseline: Se True, executa preliminarmente o Caso Base (0% de VEs).
    apenas_baseline: Se True, encerra o fluxo logo após executar o Caso Base.
    usar_pv_mosaik: Se True, utiliza os modelos de inversor e painel fotovoltaico via Mosaik;
                    se False, utiliza a modelagem nativa de PVSystem do OpenDSS.

    Retorna:
    --------
    Dicionário com o sumário de execução de todos os cenários e tempos registrados.
    """
    if seed is not None:
        lista_sementes = [seed]
    elif sementes is not None:
        lista_sementes = sementes
    else:
        lista_sementes = [8, 25, 42, 100, 777, 2026]

    inicio_total = time.perf_counter()
    data_inicio_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pasta_cenarios = OUTPUT_DIR / "cenarios"
    pasta_cenarios.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print(" EXECUÇÃO EM LOTE: GRADE DE CENÁRIOS DE VEs MULTISSEMENTES (ESB01S4)")
    print("=" * 80)
    print(f" Data/Hora de Início : {data_inicio_str}")
    print(f" Base de Cálculo     : {base_calculo} ({DOMICILIOS_BT_TOTAL} domicílios)")
    print(f" Sementes Alvo       : {lista_sementes} (Total: {len(lista_sementes)} sementes)")
    print(f" Cenários Alvo       : {cenarios} % (Total: {len(cenarios)} cenários por semente)")
    print(f" Total de Simulações : {len(lista_sementes) * len(cenarios) + (1 if executar_baseline else 0)}")
    print(f" Forçar Re-execução  : {'Sim' if forcar else 'Não (Pula arquivos já existentes)'}")
    print(f" Modo PV             : {'Simuladores Mosaik (Smart Inverter)' if usar_pv_mosaik else 'OpenDSS Nativo'}")
    print(f" Diretório Raiz      : {pasta_cenarios}")
    print("=" * 80 + "\n")

    relatorio_geral = []
    total_executadas = 0
    total_puladas = 0
    total_erros = 0

    # -------------------------------------------------------------------------
    # ETAPA 0: CASO BASE (0% VEs / Baseline do Alimentador)
    # -------------------------------------------------------------------------
    if executar_baseline or apenas_baseline:
        pasta_base = pasta_cenarios / "caso_base"
        pasta_base.mkdir(parents=True, exist_ok=True)
        arquivo_base = pasta_base / "result_TCC_baseline.csv"
        ja_existe_base = arquivo_base.exists() and arquivo_base.stat().st_size > 1024

        print("\n" + "#" * 80)
        print(" >>> [ETAPA 0: CASO BASE (0% VEs / BASELINE)] <<<")
        print(f" Pasta de Destino: {pasta_base.relative_to(PROJECT_ROOT)}")
        print(f" Arquivo Alvo    : {arquivo_base.name}")
        print("#" * 80)

        if ja_existe_base and not forcar:
            tam_mb = arquivo_base.stat().st_size / (1024 * 1024)
            print(f"  [PULADO]: Arquivo do Caso Base já existe ({tam_mb:.1f} MB).")
            relatorio_geral.append({
                "indice_global": 0,
                "seed": "baseline",
                "penetracao_pct": 0.0,
                "qtd_evs": 0,
                "arquivo_csv": str(arquivo_base.name),
                "caminho_relativo": str(arquivo_base.relative_to(PROJECT_ROOT)),
                "tamanho_mb": round(tam_mb, 2),
                "status": "PULADO_EXISTENTE",
                "duracao_segundos": 0.0,
            })
            total_puladas += 1
        else:
            t0_b = time.perf_counter()
            status_b = "SUCESSO"
            erro_b = None
            try:
                executar_simulacao_subprocesso(
                    qtd_evs=0,
                    penetracao_pct=0.0,
                    base_calculo=base_calculo,
                    nome_cenario="result_TCC_baseline",
                    usar_pv_mosaik=usar_pv_mosaik,
                    mostrar_progresso=mostrar_progresso,
                    pasta_saida=pasta_base,
                )
                total_executadas += 1
            except Exception as e:
                status_b = "ERRO"
                erro_b = str(e)
                total_erros += 1
                print(f"  [ERRO NO CASO BASE]: {e}")

            dur_b = time.perf_counter() - t0_b
            tam_mb = round(arquivo_base.stat().st_size / (1024 * 1024), 2) if arquivo_base.exists() else 0.0
            print(f"  Status do Cenário  : {status_b}")
            print(f"  Duração do Passo   : {dur_b:.1f} s ({dur_b / 60:.2f} min)")
            relatorio_geral.append({
                "indice_global": 0,
                "seed": "baseline",
                "penetracao_pct": 0.0,
                "qtd_evs": 0,
                "arquivo_csv": str(arquivo_base.name),
                "caminho_relativo": str(arquivo_base.relative_to(PROJECT_ROOT)),
                "tamanho_mb": tam_mb,
                "status": status_b,
                "erro": erro_b,
                "duracao_segundos": round(dur_b, 2),
            })

        if apenas_baseline:
            duracao_total = time.perf_counter() - inicio_total
            print("\n" + "=" * 80)
            print(f" SIMULAÇÃO ISOLADA DO CASO BASE CONCLUÍDA ({duracao_total / 60:.2f} min)")
            print("=" * 80)
            return {"status": "baseline_concluido", "cenarios": relatorio_geral}

    idx_global = 1
    total_tarefas = len(lista_sementes) * len(cenarios)

    for idx_s, s in enumerate(lista_sementes, start=1):
        pasta_seed = pasta_cenarios / f"seed_{s}"
        pasta_seed.mkdir(parents=True, exist_ok=True)
        
        print("\n" + "#" * 80)
        print(f" >>> [SEMENTE {idx_s}/{len(lista_sementes)}: SEED {s}] <<<")
        print(f" Pasta de Destino: {pasta_seed.relative_to(PROJECT_ROOT)}")
        print("#" * 80)

        for i, p in enumerate(cenarios, start=1):
            qtd_evs = calcular_qtd_evs(p, DOMICILIOS_BT_TOTAL)
            arquivo_csv = obter_nome_arquivo_cenario(p, base_calculo, seed=s)
            ja_existe = arquivo_csv.exists() and arquivo_csv.stat().st_size > 1024

            progresso_str = f"[{idx_global:02d}/{total_tarefas:02d}] Seed {s} | Cenário {p:02d}% ({qtd_evs} VEs)"
            print("\n" + "-" * 80)
            print(f" {progresso_str}")
            print(f" Arquivo Alvo: {arquivo_csv.name}")
            print("-" * 80)

            if ja_existe and not forcar:
                tamanho_mb = arquivo_csv.stat().st_size / (1024 * 1024)
                print(f"  [PULADO]: Arquivo de resultados já existe ({tamanho_mb:.1f} MB).")
                relatorio_geral.append({
                    "indice_global": idx_global,
                    "seed": s,
                    "penetracao_pct": p,
                    "qtd_evs": qtd_evs,
                    "arquivo_csv": str(arquivo_csv.name),
                    "caminho_relativo": str(arquivo_csv.relative_to(PROJECT_ROOT)),
                    "tamanho_mb": round(tamanho_mb, 2),
                    "status": "PULADO_EXISTENTE",
                    "duracao_segundos": 0.0,
                })
                total_puladas += 1
                idx_global += 1
                continue

            t0 = time.perf_counter()
            status = "SUCESSO"
            erro_msg = None

            try:
                tag = f"ev_p{int(p)}_{base_calculo}"
                nome_cen = f"result_TCC_{tag}_seed{s}"
                executar_simulacao_subprocesso(
                    penetracao_pct=float(p),
                    base_calculo=base_calculo,
                    seed=s,
                    nome_cenario=nome_cen,
                    usar_pv_mosaik=usar_pv_mosaik,
                    mostrar_progresso=mostrar_progresso,
                    pasta_saida=pasta_seed,
                )
                total_executadas += 1
            except Exception as e:
                status = "ERRO"
                erro_msg = str(e)
                total_erros += 1
                print(f"  [ERRO NA SIMULAÇÃO]: {e}")

            duracao = time.perf_counter() - t0
            tamanho_mb = (
                round(arquivo_csv.stat().st_size / (1024 * 1024), 2)
                if arquivo_csv.exists()
                else 0.0
            )

            print(f"  Status do Cenário  : {status}")
            print(f"  Duração do Passo   : {duracao:.1f} s ({duracao / 60:.2f} min)")
            if arquivo_csv.exists():
                print(f"  Tamanho do Arquivo : {tamanho_mb:.1f} MB")

            relatorio_geral.append({
                "indice_global": idx_global,
                "seed": s,
                "penetracao_pct": p,
                "qtd_evs": qtd_evs,
                "arquivo_csv": str(arquivo_csv.name),
                "caminho_relativo": str(arquivo_csv.relative_to(PROJECT_ROOT)) if arquivo_csv.exists() else "",
                "tamanho_mb": tamanho_mb,
                "status": status,
                "erro": erro_msg,
                "duracao_segundos": round(duracao, 2),
            })
            idx_global += 1

    duracao_total = time.perf_counter() - inicio_total
    data_fim_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Resumo Final em Tabela
    print("\n" + "=" * 92)
    print(" RESUMO DA EXECUÇÃO MULTISSEMENTES DA GRADE DE CENÁRIOS")
    print("=" * 92)
    print(f" Início        : {data_inicio_str}")
    print(f" Término       : {data_fim_str}")
    print(f" Tempo Total   : {duracao_total / 60:.2f} min ({duracao_total:.1f} s)")
    print(f" Total Tarefas : {total_tarefas} | Executadas: {total_executadas} | Puladas (Cache): {total_puladas} | Erros: {total_erros}\n")

    formato_linha = "{:<4} | {:<7} | {:<12} | {:<9} | {:<32} | {:<9} | {:<10}"
    print(formato_linha.format("#", "Seed", "Penetração", "Qtd VEs", "Arquivo CSV", "Tam (MB)", "Status"))
    print("-" * 92)

    for item in relatorio_geral:
        print(formato_linha.format(
            item["indice_global"],
            str(item["seed"]),
            f"{item['penetracao_pct']}%",
            f"{item['qtd_evs']} VEs",
            item["arquivo_csv"],
            f"{item['tamanho_mb']:.1f}",
            item["status"],
        ))
    print("=" * 92 + "\n")

    # Salva relatório JSON consolidado em output/relatorios/
    pasta_relatorios = OUTPUT_DIR / "relatorios"
    pasta_relatorios.mkdir(parents=True, exist_ok=True)
    caminho_json = pasta_relatorios / "resumo_grade_cenarios.json"
    dados_resumo = {
        "projeto": "ESB01S4 - TCC Co-simulação VEs Multissementes",
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "tempo_total_minutos": round(duracao_total / 60, 2),
        "base_calculo": base_calculo,
        "domicilios_bt": DOMICILIOS_BT_TOTAL,
        "sementes": lista_sementes,
        "total_tarefas": total_tarefas,
        "total_executadas": total_executadas,
        "total_puladas": total_puladas,
        "total_erros": total_erros,
        "cenarios": relatorio_geral,
    }
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados_resumo, f, indent=2, ensure_ascii=False)
    with open(pasta_relatorios / "resumo_grade_multissementes.json", "w", encoding="utf-8") as f:
        json.dump(dados_resumo, f, indent=2, ensure_ascii=False)
    print(f"Relatório consolidado salvo em: {caminho_json}")

    return dados_resumo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa a Grade Paramétrica de Cenários de VEs (0% a 50% de 5 em 5%) Multissementes no ESB01S4."
    )
    parser.add_argument(
        "--cenarios", "-c", nargs="+", type=float, default=CENARIOS_PADRAO,
        help="Lista de porcentagens de penetração a simular (padrão: 5 10 15 20 25 30 35 40 45 50)."
    )
    parser.add_argument(
        "--base", "-b", type=str, default="residencial_bt",
        choices=["residencial_bt", "barras_bt", "total_barras"],
        help="Base de cálculo da penetração (padrão: residencial_bt)."
    )
    parser.add_argument(
        "--sementes", "--seeds", "-s", nargs="+", type=int, default=[8, 25, 42, 100, 777, 2026],
        help="Lista de sementes pseudoaleatórias a executar (padrão: 8 25 42 100 777 2026)."
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Semente única (sobrescreve --sementes se especificado, ex: --seed 42)."
    )
    parser.add_argument(
        "--forcar", "-f", action="store_true", default=False,
        help="Força re-execução de cenários mesmo se o arquivo CSV de saída já existir."
    )
    parser.add_argument(
        "--progresso", action="store_true", default=False,
        help="Exibe a barra de progresso do Mosaik durante a simulação."
    )
    parser.add_argument(
        "--sem-baseline", action="store_true", default=False,
        help="Não executa a etapa preliminar do Caso Base (0%% VEs), simulando apenas a grade de penetração."
    )
    parser.add_argument(
        "--apenas-baseline", "--baseline-only", action="store_true", default=False,
        help="Executa exclusivamente o Caso Base (0%% VEs) na subpasta caso_base/ e encerra."
    )
    parser.add_argument(
        "--sem-pv-mosaik", action="store_true", default=False,
        help="Desativa os simuladores PVSimulator e InverterSim via Mosaik, usando PVSystem nativo do OpenDSS."
    )

    args = parser.parse_args()

    executar_grade(
        cenarios=args.cenarios,
        base_calculo=args.base,
        sementes=args.sementes,
        seed=args.seed,
        forcar=args.forcar,
        mostrar_progresso=args.progresso,
        executar_baseline=not args.sem_baseline,
        apenas_baseline=args.apenas_baseline,
        usar_pv_mosaik=not args.sem_pv_mosaik,
    )

