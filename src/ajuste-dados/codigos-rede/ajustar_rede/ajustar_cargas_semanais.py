#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para processar os arquivos de definição de cargas (CargasBT e CargasMT) do OpenDSS.
O objetivo é selecionar as cargas do mês desejado e remover os sufixos _DU, _SA e _DO do parâmetro 'daily',
de forma que passem a apontar para as curvas de carga semanais unificadas.
"""

import os
import re
import glob
from pathlib import Path
from typing import List, Optional


def processar_arquivo_carga(caminho_entrada: Path, caminho_saida: Path) -> int:
    """
    Lê o arquivo de cargas (usaremos o _DU como base para os valores de potência),
    substitui os sufixos diários das curvas (removendo _DU, _SA, _DO) e salva no destino.
    Retorna a quantidade de alterações realizadas.
    """
    if not caminho_entrada.exists():
        print(f"⚠️ Aviso: Arquivo não encontrado - {caminho_entrada}")
        return 0

    # Padrão regex para remover o _DU, _SA ou _DO do atributo 'daily'
    padrao = re.compile(r'(daily=["\'][a-zA-Z0-9\-_]+)_(DU|SA|DO)(["\'])', re.IGNORECASE)

    linhas_ajustadas = []
    modificacoes = 0

    with open(caminho_entrada, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            linha_nova, num_subs = padrao.subn(r'\1\3', linha)
            linhas_ajustadas.append(linha_nova)
            modificacoes += num_subs

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.writelines(linhas_ajustadas)

    print(f"✅ Arquivo final criado: {caminho_saida.name} ({modificacoes} referências 'daily' ajustadas)")
    return modificacoes


def processar_cargas_alimentador(
    dir_origem: Path,
    dir_destino: Path,
    mes: int = 1,
    ano_cod_alim: str = ""
) -> List[Path]:
    """
    Método de alto nível para orquestração:
    Busca os arquivos CargasBT e CargasMT para o mês especificado, ajusta o campo daily e salva no destino.
    """
    arquivos_gerados: List[Path] = []

    for tipo in ["BT", "MT"]:
        # Tenta buscar pelo mês formatado com 2 dígitos ou 1 dígito
        padroes = [
            f"Cargas{tipo}_DU{mes:02d}_*.dss",
            f"Cargas{tipo}_DU{mes}_*.dss"
        ]
        
        encontrados = []
        for p in padroes:
            encontrados.extend(list(dir_origem.glob(p)))

        # Fallback: se não achar com o mês exato, procura qualquer arquivo DU
        if not encontrados:
            encontrados = list(dir_origem.glob(f"Cargas{tipo}_DU*.dss"))
            if encontrados:
                print(f"ℹ️ Cargas{tipo} para mês {mes} não encontrado diretamente. Usando arquivo base: {encontrados[0].name}")
            else:
                encontrados = list(dir_origem.glob(f"Cargas{tipo}*.dss"))

        if not encontrados:
            print(f"⚠️ Nenhum arquivo Cargas{tipo} encontrado em {dir_origem}")
            continue

        caminho_base = encontrados[0]
        nome_saida = f"Cargas{tipo}_{ano_cod_alim}.dss" if ano_cod_alim else f"Cargas{tipo}.dss"
        caminho_saida = dir_destino / nome_saida

        processar_arquivo_carga(caminho_base, caminho_saida)
        arquivos_gerados.append(caminho_saida)

    return arquivos_gerados


def main():
    import argparse

    pasta_rede = Path(__file__).resolve().parents[4]
    dir_entrada_padrao = pasta_rede / "dados-rede" / "sub__ADT" / "ADT01C2"
    dir_saida_padrao = pasta_rede / "dados-rede" / "ADT01C2-ajustada"

    parser = argparse.ArgumentParser(
        description="Ajusta os arquivos CargasBT e CargasMT gerando apenas um de cada tipo para simulação semanal."
    )
    parser.add_argument("--entrada", "-i", type=Path, default=dir_entrada_padrao, help="Diretório de entrada.")
    parser.add_argument("--saida", "-o", type=Path, default=dir_saida_padrao, help="Diretório de saída.")
    parser.add_argument("--mes", "-m", type=int, default=1, help="Mês do ano (1 a 12).")

    args = parser.parse_args()

    processar_cargas_alimentador(dir_origem=args.entrada, dir_destino=args.saida, mes=args.mes)


if __name__ == "__main__":
    main()
