#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cenário 4: Rede MT + BT com Apenas PVs Corrigidos (Cargas BT com vminpu=0.5)
Aplica a correção dos 23 PVSystems monofásicos e conn=Delta nos PVs trifásicos,
mas mantém as Cargas BT com vminpu=0.5.
Demonstra que a correção dos PVs elimina as sobretensões de 16 pu, mas o colapso
numérico por oscilação de vminpu=0.5 no transformador TRF_TOK5079A ainda causa divergência
nos horários de pico.
"""

from pathlib import Path
import json
from utils import inicializar_dss, executar_simulacao_diaria, imprimir_tabela_resumo, REDE_DIR

OUTPUT_JSON = Path(__file__).resolve().parent / "resultado_cenario4.json"


def rodar_cenario4(salvar_json=True):
    print("\n⚡ [Cenário 4] Inicializando simulação: Apenas PVs Corrigidos + Cargas vminpu=0.5...")
    dss = inicializar_dss()

    comandos = [
        "Clear",
        f'Compile "{REDE_DIR / "Master_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CurvaCarga_Sintetica_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4_vmin05.dss"}"',
        f'Redirect "{REDE_DIR / "CargasMT_Sintetico_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "ESB01S4_pv.dss"}"',
        f'Redirect "{REDE_DIR / "ESB01S4_evs.dss"}"',
        "Set ControlMode=Time",
        "Set Maxiterations=150",
        "Set MaxControlIter=50",
        "Batchedit RegControl..* maxtapchange=0",
        "Set Voltagebases=[13.8 0.38 0.22]",
        "CalcVoltageBases",
    ]

    for cmd in comandos:
        dss.text(cmd)

    res = executar_simulacao_diaria(dss, n_passos=144, step_size="10m")
    res["cenario"] = "Cenário 4: Apenas PVs Corrigidos (Cargas com vminpu=0.5)"
    res["descricao"] = "Master + CargasBT (vminpu=0.5) + PVs corrigidos (23 monofásicos + conn=Delta) + EVs"

    imprimir_tabela_resumo(res["cenario"], res)

    if salvar_json:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {OUTPUT_JSON.name}")

    return res


if __name__ == "__main__":
    rodar_cenario4()

