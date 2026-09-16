#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para processar as curvas de carga do OpenDSS, agrupando os perfis diários
(DU - Dia Útil, SA - Sábado, DO - Domingo) em uma curva semanal contínua de 7 dias (168 horas).
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def extrair_dados_linha(linha: str) -> Tuple[str, str, List[float]]:
    """
    Extrai o nome base da curva, o tipo de dia (DU, SA, DO) e os multiplicadores de uma linha do OpenDSS.
    Exemplo: New "Loadshape.A3-Tipo01_DU" 24 1 mult=(0.9051, 0.8946, ...)
    """
    linha = linha.strip()
    if not linha or linha.startswith("!"):
        return "", "", []

    padrao = re.compile(
        r'New\s+["\']?Loadshape\.([a-zA-Z0-9\-_]+)_(DU|SA|DO)["\']?\s+.*mult=\(([^)]+)\)',
        re.IGNORECASE,
    )
    match = padrao.search(linha)
    if not match:
        return "", "", []

    nome_base = match.group(1)
    tipo_dia = match.group(2).upper()
    valores_str = match.group(3)

    multiplicadores = [float(v.strip()) for v in valores_str.split(",") if v.strip()]
    return nome_base, tipo_dia, multiplicadores


def carregar_curvas_dss(caminho_arquivo: Path) -> Dict[str, Dict[str, List[float]]]:
    """
    Lê o arquivo .dss e agrupa os multiplicadores por nome base e tipo de dia.
    """
    curvas: Dict[str, Dict[str, List[float]]] = {}
    with open(caminho_arquivo, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            nome_base, tipo_dia, mults = extrair_dados_linha(linha)
            if not nome_base:
                continue
            if nome_base not in curvas:
                curvas[nome_base] = {}
            curvas[nome_base][tipo_dia] = mults
    return curvas


def construir_curva_semanal(
    dados_curva: Dict[str, List[float]],
    ordem_dias: Optional[List[str]] = None
) -> List[float]:
    """
    Gera a sequência de multiplicadores para 7 dias (168 horas).
    Padrão de ordem: ['DO', 'DU', 'DU', 'DU', 'DU', 'DU', 'SA'] (1 Domingo, 5 Dias Úteis, 1 Sábado)
    """
    if ordem_dias is None:
        ordem_dias = ["DO", "DU", "DU", "DU", "DU", "DU", "SA"]

    mult_semana: List[float] = []
    for dia in ordem_dias:
        if dia in dados_curva:
            mult_semana.extend(dados_curva[dia])
        elif "DU" in dados_curva:
            mult_semana.extend(dados_curva["DU"])
        else:
            primeiro_tipo = next(iter(dados_curva))
            mult_semana.extend(dados_curva[primeiro_tipo])

    return mult_semana


def gerar_arquivo_dss_semanal(
    curvas: Dict[str, Dict[str, List[float]]],
    caminho_saida: Path,
    sufixo_nome: str = "",
    ordem_dias: Optional[List[str]] = None
) -> Path:
    """
    Gera o novo arquivo .dss com as curvas de carga semanais de 168 pontos (intervalo de 1h).
    """
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    linhas_dss = []

    for nome_base in sorted(curvas.keys()):
        dados_dia = curvas[nome_base]
        mult_semana = construir_curva_semanal(dados_dia, ordem_dias=ordem_dias)
        mult_str = ", ".join(f"{val:.9g}" if isinstance(val, float) else str(val) for val in mult_semana)
        nome_loadshape = f"{nome_base}{sufixo_nome}"
        npts = len(mult_semana)
        interval = 1.0

        linha = f'New "Loadshape.{nome_loadshape}" npts={npts} interval={interval} mult=({mult_str})'
        linhas_dss.append(linha)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_dss) + "\n")

    print(f"✅ Arquivo semanal gerado com sucesso: {caminho_saida.name}")
    print(f"📊 Total de curvas semanais criadas: {len(curvas)} (cada uma com {len(mult_semana)} pontos)")
    return caminho_saida


def processar_curvas_carga_alimentador(
    dir_origem: Path,
    dir_destino: Path,
    ano_cod_alim: str,
    sufixo_nome: str = "",
    ordem_dias: Optional[List[str]] = None
) -> Optional[Path]:
    """
    Método de alto nível para orquestração:
    Busca o arquivo de curvas do alimentador em dir_origem, unifica as curvas para 168h e salva em dir_destino.
    """
    arquivos_curva = list(dir_origem.glob("CurvaCarga*.dss"))
    if not arquivos_curva:
        print(f"⚠️ Nenhum arquivo CurvaCarga*.dss encontrado em {dir_origem}")
        return None

    arq_curva_orig = arquivos_curva[0]
    print(f"📖 Carregando curvas de carga de: {arq_curva_orig.name}")

    curvas = carregar_curvas_dss(arq_curva_orig)
    if not curvas:
        print(f"❌ Nenhuma curva válida encontrada no arquivo {arq_curva_orig.name}")
        return None

    caminho_saida = dir_destino / f"CurvaCarga_{ano_cod_alim}.dss"
    return gerar_arquivo_dss_semanal(curvas, caminho_saida, sufixo_nome=sufixo_nome, ordem_dias=ordem_dias)


def main():
    import argparse

    pasta_rede = Path(__file__).resolve().parents[4]
    arquivo_entrada_padrao = pasta_rede / "dados-rede" / "sub__ADT" / "ADT01C2" / "CurvaCarga_20250139_ADT01C2_------1-----.dss"
    diretorio_saida_padrao = pasta_rede / "dados-rede" / "ADT01C2-ajustada"
    arquivo_saida_padrao = diretorio_saida_padrao / "CurvaCarga_20250139_ADT01C2.dss"

    parser = argparse.ArgumentParser(
        description="Agrupa curvas de carga diárias (DU, SA, DO) do OpenDSS em curvas semanais de 7 dias (168h)."
    )
    parser.add_argument("--entrada", "-i", type=Path, default=arquivo_entrada_padrao, help="Arquivo .dss de entrada.")
    parser.add_argument("--saida", "-o", type=Path, default=arquivo_saida_padrao, help="Arquivo .dss de saída.")
    parser.add_argument("--sufixo", "-s", type=str, default="", help="Sufixo opcional para o nome do Loadshape.")
    parser.add_argument("--ordem", nargs="+", default=["DO", "DU", "DU", "DU", "DU", "DU", "SA"], help="Ordem dos 7 dias.")

    args = parser.parse_args()

    if not args.entrada.exists():
        print(f"❌ Erro: Arquivo de entrada não encontrado em {args.entrada}")
        return

    curvas = carregar_curvas_dss(args.entrada)
    gerar_arquivo_dss_semanal(curvas=curvas, caminho_saida=args.saida, sufixo_nome=args.sufixo, ordem_dias=args.ordem)


if __name__ == "__main__":
    main()
