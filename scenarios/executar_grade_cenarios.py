"""Orquestrador em Lote de Cenários de Penetração de VEs (ESB01S4)
================================================================

Este script executa sequencialmente a grade paramétrica de cenários de penetração
de Veículos Elétricos (0% a 50% em passos de 5%) sobre os 1.914 domicílios BT
do alimentador real ESB01S4 da Neoenergia Cosern.

Recursos:
---------
1. Execução automatizada e sequencial dos cenários (5%, 10%, 15%, ..., 50%).
2. Pula automaticamente cenários cujos arquivos de resultados já existam (a menos
   que a flag `--forcar` seja especificada).
3. Cronometra o tempo de execução individual e total.
4. Gera um relatório consolidado em JSON (`output/resumo_grade_cenarios.json`)
   e uma tabela formatada no console.

Uso:
----
    # Executar toda a grade padrão (5% a 50% de 5 em 5%):
    uv run python scenarios/executar_grade_cenarios.py

    # Executar apenas cenários específicos:
    uv run python scenarios/executar_grade_cenarios.py --cenarios 5 15 30 50

    # Forçar re-execução de todos os cenários existentes:
    uv run python scenarios/executar_grade_cenarios.py --forcar
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Garante que a raiz do projeto e 'src/' estejam no path de importação
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for p in [str(PROJECT_ROOT), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scenarios.scenario_ESB01S4_TCC import OUTPUT_DIR, run_scenario

# Grade padrão de simulações (10 cenários de VEs; Caso Base 0% é tratado como baseline)
CENARIOS_PADRAO = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
DOMICILIOS_BT_TOTAL = 947  # 947 Unidades Consumidoras únicas mapeadas a partir das 1.914 cargas _M1/_M2 no OpenDSS



def obter_nome_arquivo_cenario(penetracao_pct: float, base_calculo: str) -> Path:
    """Retorna o caminho padrão do arquivo CSV de saída para a taxa dada."""
    if penetracao_pct == 0.0:
        return OUTPUT_DIR / "result_TCC_baseline.csv"
    tag = f"ev_p{int(penetracao_pct)}_{base_calculo}"
    return OUTPUT_DIR / f"result_TCC_{tag}.csv"


def calcular_qtd_evs(penetracao_pct: float, total_domicilios: int = DOMICILIOS_BT_TOTAL) -> int:
    """Calcula o número inteiro exato de VEs para o percentual residencial dado."""
    return round(total_domicilios * (penetracao_pct / 100.0))


def executar_grade(
    cenarios: List[float],
    base_calculo: str = "residencial_bt",
    seed: int = 42,
    forcar: bool = False,
    mostrar_progresso: bool = False,
) -> Dict:
    """
    Executa em lote a lista de cenários de penetração especificados.
    """
    inicio_total = time.perf_counter()
    data_inicio_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 78)
    print(" ORQUESTRADOR EM LOTE: GRADE PARAMÉTRICA DE PENETRAÇÃO DE VEs (ESB01S4)")
    print("=" * 78)
    print(f" Data/Hora de Início : {data_inicio_str}")
    print(f" Base de Cálculo     : {base_calculo} ({DOMICILIOS_BT_TOTAL} domicílios)")
    print(f" Semente Aleatória   : {seed}")
    print(f" Cenários Alvo       : {cenarios} %")
    print(f" Forçar Re-execução  : {'Sim' if forcar else 'Não (Pula existentes)'}")
    print(f" Diretório de Saída  : {OUTPUT_DIR}")
    print("=" * 78 + "\n")

    relatorio_cenarios = []

    for i, p in enumerate(cenarios, start=1):
        qtd_evs = calcular_qtd_evs(p, DOMICILIOS_BT_TOTAL)
        arquivo_csv = obter_nome_arquivo_cenario(p, base_calculo)
        ja_existe = arquivo_csv.exists() and arquivo_csv.stat().st_size > 1024

        cabecalho_cenario = f"[{i:02d}/{len(cenarios):02d}] CENÁRIO {p:02d}% ({qtd_evs} VEs em {DOMICILIOS_BT_TOTAL} domicílios)"
        print("\n" + "-" * 78)
        print(f" {cabecalho_cenario}")
        print(f" Arquivo Alvo: {arquivo_csv.name}")
        print("-" * 78)

        if ja_existe and not forcar:
            tamanho_mb = arquivo_csv.stat().st_size / (1024 * 1024)
            print(f"  [PULADO]: Arquivo de resultados já existe ({tamanho_mb:.1f} MB).")
            relatorio_cenarios.append({
                "indice": i,
                "penetracao_pct": p,
                "qtd_evs": qtd_evs,
                "arquivo_csv": str(arquivo_csv.name),
                "tamanho_mb": round(tamanho_mb, 2),
                "status": "PULADO_EXISTENTE",
                "duracao_segundos": 0.0,
            })
            continue

        # Execução do cenário de co-simulação
        t0 = time.perf_counter()
        status = "SUCESSO"
        erro_msg = None

        try:
            run_scenario(
                penetracao_pct=float(p),
                base_calculo=base_calculo,
                seed=seed,
                usar_pv_mosaik=False,
                reexecutar_alocacao=True,
                mostrar_progresso=mostrar_progresso,
            )
        except Exception as e:
            status = "ERRO"
            erro_msg = str(e)
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

        relatorio_cenarios.append({
            "indice": i,
            "penetracao_pct": p,
            "qtd_evs": qtd_evs,
            "arquivo_csv": str(arquivo_csv.name),
            "tamanho_mb": tamanho_mb,
            "status": status,
            "erro": erro_msg,
            "duracao_segundos": round(duracao, 2),
        })

    duracao_total = time.perf_counter() - inicio_total
    data_fim_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Resumo Final em Tabela
    print("\n" + "=" * 78)
    print(" RESUMO DA EXECUÇÃO DA GRADE DE CENÁRIOS")
    print("=" * 78)
    print(f" Início : {data_inicio_str}")
    print(f" Término: {data_fim_str}")
    print(f" Tempo Total: {duracao_total / 60:.2f} min ({duracao_total:.1f} s)\n")

    formato_linha = "{:<4} | {:<14} | {:<9} | {:<32} | {:<9} | {:<10}"
    print(formato_linha.format("#", "Penetração", "Qtd VEs", "Arquivo CSV", "Tam (MB)", "Status"))
    print("-" * 88)

    for item in relatorio_cenarios:
        print(formato_linha.format(
            item["indice"],
            f"{item['penetracao_pct']}%",
            f"{item['qtd_evs']} VEs",
            item["arquivo_csv"],
            f"{item['tamanho_mb']:.1f}",
            item["status"],
        ))
    print("=" * 88 + "\n")

    # Salva relatório JSON consolidado
    caminho_json = OUTPUT_DIR / "resumo_grade_cenarios.json"
    dados_resumo = {
        "projeto": "ESB01S4 - TCC Co-simulação VEs",
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "tempo_total_minutos": round(duracao_total / 60, 2),
        "base_calculo": base_calculo,
        "domicilios_bt": DOMICILIOS_BT_TOTAL,
        "seed": seed,
        "cenarios": relatorio_cenarios,
    }
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados_resumo, f, indent=2, ensure_ascii=False)
    print(f"Relatório consolidado salvo em: {caminho_json}")

    return dados_resumo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa a Grade Paramétrica de Cenários de VEs (0% a 50% de 5 em 5%) no ESB01S4."
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
        "--seed", "-s", type=int, default=42,
        help="Semente pseudoaleatória para alocação dos VEs (padrão: 42)."
    )
    parser.add_argument(
        "--forcar", "-f", action="store_true", default=False,
        help="Força re-execução de cenários mesmo se o arquivo CSV de saída já existir."
    )
    parser.add_argument(
        "--progresso", action="store_true", default=False,
        help="Exibe a barra de progresso do Mosaik durante a simulação."
    )

    args = parser.parse_args()

    executar_grade(
        cenarios=args.cenarios,
        base_calculo=args.base,
        seed=args.seed,
        forcar=args.forcar,
        mostrar_progresso=args.progresso,
    )

