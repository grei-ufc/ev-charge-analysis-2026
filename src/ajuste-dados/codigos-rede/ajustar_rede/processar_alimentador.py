#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Orquestrador para preparação e ajuste completo da rede de um alimentador para simulação semanal no OpenDSS.

Este script integra e coordena os módulos:
- juntar_curvas_carga_semanal.py (Unificação das curvas de carga diárias em 168h semanais)
- ajustar_cargas_semanais.py (Seleção das cargas do mês e adequação dos parâmetros 'daily')

Uso:
- Edite as variáveis no bloco de CONFIGURAÇÃO abaixo, ou
- Execute via terminal passando os argumentos:
  uv run python rede/codigos-rede/ajustar_rede/processar_alimentador.py --sub /caminho/sub__ESB --alim ESB01C1 --mes 1
"""

import os
import re
import sys
import shutil
import argparse
from pathlib import Path
from typing import Optional

# Importando os métodos especializados dos módulos irmãos
from juntar_curvas_carga_semanal import processar_curvas_carga_alimentador
from ajustar_cargas_semanais import processar_cargas_alimentador


# ==============================================================================
# CONFIGURAÇÃO PADRÃO (Altere aqui para executar direto sem argumentos)
# ==============================================================================
_BASE_PROJETO = Path(__file__).resolve().parents[4]  # Raiz do projeto (ev-analysis-2026)
CAMINHO_SUBESTACAO_PADRAO = _BASE_PROJETO.parent / "dados-da-rede" / "sub__ESB"
ALIMENTADOR_PADRAO = "ESB01S4"
MES_PADRAO = 9  # Mês de 1 a 12 (1 = Janeiro, ..., 12 = Dezembro)
# ==============================================================================


def extrair_identificador_rede(dir_origem: Path, alimentador: str) -> str:
    """
    Identifica o código completo do alimentador (ex: 20250139_ESB01C1) a partir dos arquivos DSS.
    """
    for arq in dir_origem.glob("*.dss"):
        match = re.search(rf'(\d+_{re.escape(alimentador)})', arq.name, re.IGNORECASE)
        if match:
            return match.group(1)
        prefix_match = re.search(r'([A-Za-z0-9]+)_([A-Za-z0-9]+)_' + re.escape(alimentador), arq.name)
        if prefix_match:
            return f"{prefix_match.group(2)}_{alimentador}"

    return alimentador


def copiar_arquivos_estaticos(dir_origem: Path, dir_destino: Path):
    """
    Copia todos os arquivos e pastas estáticos da rede (independentes de data/mês).
    Exclui curvas de carga, cargas e master que serão processados pelos módulos específicos.
    """
    padroes_ignorados = [
        re.compile(r'^CurvaCarga.*\.dss$', re.IGNORECASE),
        re.compile(r'^CargasBT.*\.dss$', re.IGNORECASE),
        re.compile(r'^CargasMT.*\.dss$', re.IGNORECASE),
        re.compile(r'^Master.*\.dss$', re.IGNORECASE),
    ]

    total_copiados = 0
    for item in dir_origem.iterdir():
        if item.is_file():
            if any(p.match(item.name) for p in padroes_ignorados):
                continue
            destino_item = dir_destino / item.name
            shutil.copy2(item, destino_item)
            total_copiados += 1
        elif item.is_dir():
            destino_pasta = dir_destino / item.name
            if not destino_pasta.exists():
                shutil.copytree(item, destino_pasta)
                total_copiados += 1

    print(f"📁 Arquivos estáticos copiados: {total_copiados} (chaves, ramais, trafos, condutores, coordenadas, etc.)")


def ajustar_arquivo_master(dir_origem: Path, dir_destino: Path, ano_cod_alim: str):
    """
    Gera o Master_*.dss ajustado para apontar para as cargas e curvas semanais sem sufixos diários.
    """
    masters = list(dir_origem.glob("Master*.dss"))
    if not masters:
        print(f"⚠️ Nenhum Master*.dss encontrado em {dir_origem}")
        return

    arq_master_orig = masters[0]
    caminho_saida = dir_destino / f"Master_{ano_cod_alim}.dss"

    linhas_master = []
    with open(arq_master_orig, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            if re.search(r'Redirect\s+["\']?CurvaCarga', linha, re.IGNORECASE):
                linhas_master.append(f'Redirect "CurvaCarga_{ano_cod_alim}.dss"\n')
            elif re.search(r'Redirect\s+["\']?CargasBT', linha, re.IGNORECASE):
                linhas_master.append(f'Redirect "CargasBT_{ano_cod_alim}.dss"\n')
            elif re.search(r'Redirect\s+["\']?CargasMT', linha, re.IGNORECASE):
                linhas_master.append(f'Redirect "CargasMT_{ano_cod_alim}.dss"\n')
            elif re.search(r'Set\s+mode\s*=', linha, re.IGNORECASE):
                linhas_master.append('Set mode = daily stepsize=1h number=168\n')
            else:
                linhas_master.append(linha)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.writelines(linhas_master)

    print(f"✅ Master semanal gerado: {caminho_saida.name}")


def gerar_arquivo_run(dir_destino: Path, alimentador: str, ano_cod_alim: str):
    """
    Gera o arquivo run_<alimentador>.dss para facilitar a execução da simulação no OpenDSS.
    """
    caminho_saida = dir_destino / f"run_{alimentador}.dss"
    conteudo = f"""Clear

! Compila o arquivo Master ajustado com a curva de 168h
Compile (Master_{ano_cod_alim}.dss)

Set ControlMode=Time

! Desabilita tap changes se houver reguladores para agilizar a convergência (opcional)
Batchedit RegControl..* maxtapchange=0

! Monitor na fonte principal (saída da subestação) para observar tensões e potências
New Monitor.Feeder_output_vi element=Vsource.SOURCE Terminal=1 mode=0
New Monitor.Feeder_output_pq element=Vsource.SOURCE Terminal=1 mode=1 ppolar=no

! O modo daily (168h, step de 1h) já vem setado no Master, mas reforçamos aqui para a execução
Set mode=Daily
Set stepsize=1h
Set number=168

Set MaxControlIter=30

! Executa a simulação ao longo do tempo (168 horas)
Solve
"""
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"▶️ Script de execução gerado: {caminho_saida.name}")


def executar_ajuste_alimentador(
    caminho_subestacao: Path,
    alimentador: str,
    mes: int,
    dir_saida_base: Optional[Path] = None
):
    """
    Função orquestradora principal.
    """
    # 1. Localização da pasta do alimentador
    if (caminho_subestacao / alimentador).is_dir():
        dir_origem = caminho_subestacao / alimentador
    elif caminho_subestacao.name.upper() == alimentador.upper() and caminho_subestacao.is_dir():
        dir_origem = caminho_subestacao
    else:
        subpastas = [d for d in caminho_subestacao.iterdir() if d.is_dir() and d.name.upper() == alimentador.upper()]
        if subpastas:
            dir_origem = subpastas[0]
        else:
            print(f"❌ Erro: Pasta do alimentador '{alimentador}' não encontrada em {caminho_subestacao}")
            return

    # 2. Definição do diretório de destino: rede/dados-rede/<ALIMENTADOR>-ajustada
    if dir_saida_base is None:
        pasta_rede = Path(__file__).resolve().parents[4]
        dir_destino = pasta_rede / "dados-rede" / f"{alimentador}-ajustada"
    else:
        dir_destino = dir_saida_base / f"{alimentador}-ajustada"

    dir_destino.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"🚀 INICIANDO PROCESSAMENTO DO ALIMENTADOR: {alimentador}")
    print(f"📅 Mês Selecionado: {mes:02d}")
    print(f"📂 Diretório de Origem:  {dir_origem}")
    print(f"🎯 Diretório de Destino: {dir_destino}")
    print("=" * 65)

    ano_cod_alim = extrair_identificador_rede(dir_origem, alimentador)

    # 1. Cópia de arquivos estáticos
    copiar_arquivos_estaticos(dir_origem, dir_destino)

    # 2. Processamento das Curvas de Carga (chamando método do módulo juntar_curvas_carga_semanal)
    processar_curvas_carga_alimentador(
        dir_origem=dir_origem,
        dir_destino=dir_destino,
        ano_cod_alim=ano_cod_alim
    )

    # 3. Processamento das Cargas BT/MT (chamando método do módulo ajustar_cargas_semanais)
    processar_cargas_alimentador(
        dir_origem=dir_origem,
        dir_destino=dir_destino,
        mes=mes,
        ano_cod_alim=ano_cod_alim
    )

    # 4. Ajuste do arquivo Master
    ajustar_arquivo_master(dir_origem, dir_destino, ano_cod_alim)

    # 5. Geração do arquivo run
    gerar_arquivo_run(dir_destino, alimentador, ano_cod_alim)

    print("=" * 65)
    print(f"🎉 Alimentador {alimentador} ajustado com sucesso!")
    print(f"👉 Localização final: {dir_destino}")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Orquestrador: Ajusta alimentadores para simulação semanal no OpenDSS."
    )
    parser.add_argument(
        "--sub",
        "-s",
        type=Path,
        default=Path(CAMINHO_SUBESTACAO_PADRAO),
        help="Caminho da subestação ou do alimentador.",
    )
    parser.add_argument(
        "--alim",
        "-a",
        type=str,
        default=ALIMENTADOR_PADRAO,
        help="Código do alimentador (ex: ESB01C1).",
    )
    parser.add_argument(
        "--mes",
        "-m",
        type=int,
        default=MES_PADRAO,
        help="Mês do ano (1 a 12).",
    )
    parser.add_argument(
        "--saida",
        "-o",
        type=Path,
        default=None,
        help="Diretório base de saída (opcional).",
    )

    args = parser.parse_args()

    if not (1 <= args.mes <= 12):
        print(f"❌ Erro: O mês deve ser de 1 a 12 (informado: {args.mes})")
        sys.exit(1)

    executar_ajuste_alimentador(
        caminho_subestacao=args.sub,
        alimentador=args.alim,
        mes=args.mes,
        dir_saida_base=args.saida
    )


if __name__ == "__main__":
    main()
