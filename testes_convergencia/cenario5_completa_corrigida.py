#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cenário 5: Rede MT + BT Completa Corrigida (PVs Corrigidos + Cargas com vminpu=0.80)
Aplica todas as correções identificadas no diagnóstico:
- 23 PVSystems convertidos para monofásicos (.1.4 ou .3.4 com kV=0.22 e conn=Wye);
- Inclusão explícita de conn=Delta nos 274 PVSystems trifásicos de BT;
- Ajuste de Vminpu=0.80 e Vmaxpu=1.20 nos PVSystems;
- Ajuste de vminpu=0.80 em todas as 3.238 cargas de Baixa Tensão;
- Reordenação da chamada de CalcVoltageBases antes de Set mode=Daily.
Resultado esperado: 100% de convergência nos 144 passos diários, média de ~5.6 iterações
e tensões estabilizadas entre 0.59 e 1.055 pu.
"""

from pathlib import Path
import json
from utils import inicializar_dss, executar_simulacao_diaria, imprimir_tabela_resumo, REDE_DIR

OUTPUT_JSON = Path(__file__).resolve().parent / "resultado_cenario5.json"


def rodar_cenario5(salvar_json=True):
    print("\n⚡ [Cenário 5] Inicializando simulação: Rede MT + BT Completa Corrigida...")
    dss = inicializar_dss()

    comandos = [
        "Clear",
        f'Compile "{REDE_DIR / "Master_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CurvaCarga_Sintetica_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CargasBT_Sintetico_20250139_ESB01S4.dss"}"',
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
    res["cenario"] = "Cenário 5: Rede MT + BT Completa Corrigida"
    res["descricao"] = "Master + CargasBT (vminpu=0.80) + PVs corrigidos (monofásicos + conn=Delta) + EVs"

    imprimir_tabela_resumo(res["cenario"], res)

    if salvar_json:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {OUTPUT_JSON.name}")

    return res


if __name__ == "__main__":
    rodar_cenario5()

