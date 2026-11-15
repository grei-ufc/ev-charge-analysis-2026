"""Extração e Exportação da Topologia de Redes Elétricas do OpenDSS
====================================================================

Compila o circuito elétrico no OpenDSS, extrai o grafo direcionado da rede
(nós, barras, condutores, linhas, transformadores e níveis de tensão) e
serializa a estrutura topológica em formato JSON para análise e plotagem.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Union

import py_dss_interface

from ..opendss.topology_builder import build_graph


def exportar_topologia(dss_path: Union[str, Path], caminho_json_saida: Union[str, Path]) -> None:
    """Compila o circuito no OpenDSS e exporta os dados do grafo da rede para JSON.

    Parâmetros:
    -----------
    dss_path: Caminho para o arquivo principal de definição do circuito (.dss).
    caminho_json_saida: Caminho do arquivo JSON de destino onde o grafo será salvo.
    """
    dss_path = Path(dss_path)
    caminho_json_saida = Path(caminho_json_saida)
    caminho_json_saida.parent.mkdir(parents=True, exist_ok=True)

    print(f"Compilando circuito OpenDSS: {dss_path.name}...")
    dss = py_dss_interface.DSS()
    dss.text("Clear")
    dss.text(f"compile [{dss_path}]")

    print("Construindo grafo da rede e classificando barramentos...")
    grafo = build_graph(dss)
    print(f"Grafo gerado: {grafo.total_nodes} nós e {grafo.total_edges} arestas.")

    # Converte os nós e arestas (dataclasses) para dicionários serializáveis em JSON
    grafo_dict = {
        "nodes": [asdict(node) for node in grafo.nodes.values()],
        "edges": [asdict(edge) for edge in grafo.edges.values()],
    }

    print(f"Salvando topologia em JSON: {caminho_json_saida.name}")
    with open(caminho_json_saida, "w", encoding="utf-8") as f:
        json.dump(grafo_dict, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        exportar_topologia(sys.argv[1], sys.argv[2])
    else:
        print("Uso: python topologia.py <circuito.dss> <saida.json>")
