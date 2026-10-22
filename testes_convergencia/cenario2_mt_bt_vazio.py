#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cenário 2: Rede MT + BT em Vazio (Sem Cargas, sem PVs, sem EVs)
Compila a topologia completa do Master (linhas MT, transformadores MT/BT, ramais BT),
mas sem injetar cargas nem geradores.
Comprova a consistência topológica da rede elétrica sem solicitação de potência.
"""

from pathlib import Path
import json
from utils import inicializar_dss, executar_simulacao_diaria, executar_snapshot, imprimir_tabela_resumo, REDE_DIR

OUTPUT_JSON = Path(__file__).resolve().parent / "resultado_cenario2.json"


def rodar_cenario2(salvar_json=True):
    print("\n⚡ [Cenário 2] Inicializando simulação: Rede MT + BT em Vazio...")
    dss = inicializar_dss()

    comandos = [
        "Clear",
        f'Compile "{REDE_DIR / "Master_20250139_ESB01S4.dss"}"',
        "Set Voltagebases=[13.8 0.38 0.22]",
        "CalcVoltageBases",
        "Set ControlMode=Time",
        "Set Maxiterations=150",
        "Set MaxControlIter=50",
    ]

    for cmd in comandos:
        dss.text(cmd)

    # 1. Teste Snapshot em Vazio
    snap_res = executar_snapshot(dss)
    print(f"• Snapshot em Vazio -> Convergiu: {snap_res['converged']} | Iterações: {snap_res['iterations']} | Faixa pu: [{snap_res['vmin_pu']}, {snap_res['vmax_pu']}]")

    # 2. Teste Daily (144 passos)
    res = executar_simulacao_diaria(dss, n_passos=144, step_size="10m")
    res["cenario"] = "Cenário 2: Rede MT + BT em Vazio"
    res["descricao"] = "Master completo (linhas MT e BT + transformadores em vazio)"
    res["snapshot"] = snap_res

    imprimir_tabela_resumo(res["cenario"], res)

    if salvar_json:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {OUTPUT_JSON.name}")

    return res


if __name__ == "__main__":
    rodar_cenario2()

