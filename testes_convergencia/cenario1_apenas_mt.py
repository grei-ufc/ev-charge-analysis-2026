#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cenário 1: Apenas Rede MT (Média Tensão)
Isola completamente a rede de Média Tensão, excluindo todos os transformadores MT/BT,
linhas secundárias e cargas de BT.
Comprova a estabilidade intrínseca da topologia de Média Tensão.
"""

from pathlib import Path
import json
from utils import inicializar_dss, executar_simulacao_diaria, imprimir_tabela_resumo, REDE_DIR

OUTPUT_JSON = Path(__file__).resolve().parent / "resultado_cenario1.json"


def rodar_cenario1(salvar_json=True):
    print("\n⚡ [Cenário 1] Inicializando simulação: Apenas Rede MT (13.8 kV)...")
    dss = inicializar_dss()

    comandos = [
        "Clear",
        f'Redirect "{REDE_DIR / "CircuitoMT_20250139_ESB01S4_------1-----.dss"}"',
        f'Redirect "{REDE_DIR / "CodCondutor_20250139_ESB01S4_------1-----.dss"}"',
        f'Redirect "{REDE_DIR / "SegmentosMT_20250139_ESB01S4_------1-----.dss"}"',
        f'Redirect "{REDE_DIR / "ChavesMT_20250139_ESB01S4_------1-----.dss"}"',
        f'Redirect "{REDE_DIR / "ReguladorMT_20250139_ESB01S4_------1-----.dss"}"',
        f'Redirect "{REDE_DIR / "CurvaCarga_Sintetica_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "CargasMT_Sintetico_20250139_ESB01S4.dss"}"',
        f'Redirect "{REDE_DIR / "GD_MT_20250139_ESB01S4_------1-----.dss"}"',
        "Set Voltagebases=[13.8]",
        "CalcVoltageBases",
        "Set ControlMode=Time",
        "Set Maxiterations=150",
        "Set MaxControlIter=50",
    ]

    for cmd in comandos:
        dss.text(cmd)

    res = executar_simulacao_diaria(dss, n_passos=144, step_size="10m")
    res["cenario"] = "Cenário 1: Apenas Rede MT"
    res["descricao"] = "SegmentosMT, ChavesMT, ReguladorMT, CargasMT_Sintetico, GD_MT"

    imprimir_tabela_resumo(res["cenario"], res)

    if salvar_json:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {OUTPUT_JSON.name}")

    return res


if __name__ == "__main__":
    rodar_cenario1()

