#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cenário 3: Rede MT + BT Completa (Original / Não Corrigida)
Reproduz as condições originais com falhas de convergência:
- 23 PVSystems trifásicos conectados a barras monofásicas (nós flutuantes com Vminpu=0.001);
- Omissão de conn=Delta nos PVs trifásicos (deslocamento severo do condutor neutro);
- Cargas BT configuradas com vminpu=0.5 (oscilação numérica no TRF_TOK5079A).
"""

from pathlib import Path
import json
from utils import inicializar_dss, executar_simulacao_diaria, imprimir_tabela_resumo, REDE_DIR

OUTPUT_JSON = Path(__file__).resolve().parent / "resultado_cenario3.json"


def rodar_cenario3(salvar_json=True):
    print("\n⚡ [Cenário 3] Inicializando simulação: Rede MT + BT Original (Com Falhas)...")
    dss = inicializar_dss()

    comandos = [
        "Clear",
        f'Compile "{REDE_DIR / "Master_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CurvaCarga_Sintetica_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4_vmin05.dss"}"',
        f'Redirect "{REDE_DIR / "CargasMT_Sintetico_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "ESB01S4_pv_original.dss"}"',
        f'Redirect "{REDE_DIR / "ESB01S4_evs.dss"}"',
        "Set ControlMode=Time",
        "Set Maxiterations=150",
        "Set MaxControlIter=50",
        "Batchedit RegControl..* maxtapchange=0",
        # Ordem original do run_ESB01S4.dss anterior às correções (Daily antes de CalcVoltageBases)
        "Set mode=Daily",
        "Set stepsize=10m",
        "Set number=1008",
        "Set Voltagebases=[13.8 0.38 0.22]",
        "CalcVoltageBases",
    ]

    for cmd in comandos:
        dss.text(cmd)

    res = executar_simulacao_diaria(dss, n_passos=144, step_size="10m")
    res["cenario"] = "Cenário 3: Rede MT + BT Completa (Original)"
    res["descricao"] = "Master + CargasBT (vminpu=0.5) + PVs originais (com nós flutuantes e sem conn=Delta) + EVs"

    imprimir_tabela_resumo(res["cenario"], res)

    if salvar_json:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {OUTPUT_JSON.name}")

    return res


if __name__ == "__main__":
    rodar_cenario3()

