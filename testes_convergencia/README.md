# Bateria de Testes de Convergência — Alimentador `ESB01S4`

Este diretório contém os scripts modulares em Python que implementam e reproduzem fielmente os **5 cenários experimentais** documentados no [relatorio_diagnostico_ESB01S4.md](../relatorio_diagnostico_ESB01S4.md).

---

## Estrutura dos Arquivos

- `utils.py`: Módulo utilitário compartilhado que inicializa o `py_dss_interface`, gerencia a simulação em modo Daily passo a passo (144 passos de 10 min) e coleta métricas de iterações, convergência, tensões nodais e potência na subestação.
- `cenario1_apenas_mt.py`: Executa o fluxo de potência isolando a rede de Média Tensão (13.8 kV).
- `cenario2_mt_bt_vazio.py`: Executa a topologia completa (MT + BT) em vazio (linhas e transformadores sem cargas/geradores).
- `cenario3_mt_bt_completa_original.py`: Reproduz a rede completa com os problemas originais não corrigidos (nós flutuantes nos 23 PVs, omissão de `conn=Delta` e cargas com `vminpu=0.5`).
- `cenario4_pvs_corrigidos_cargas_originais.py`: Testa a rede com os PVs corrigidos, mas mantendo `vminpu=0.5` nas cargas BT para demonstrar o colapso por oscilação no `TRF_TOK5079A`.
- `cenario5_completa_corrigida.py`: Executa a rede completa com todas as correções aplicadas (100% de convergência).
- `executar_todos_cenarios.py`: Script mestre que roda os cenários 1 a 5 sequencialmente, gera a tabela comparativa e salva os resultados em `resultados_comparativos.json`.

---

## Como Executar

Utilizando o `uv`:

```bash
# Executar todos os cenários de uma vez
uv run python testes_convergencia/executar_todos_cenarios.py

# Ou executar um cenário específico:
uv run python testes_convergencia/cenario1_apenas_mt.py
uv run python testes_convergencia/cenario5_completa_corrigida.py
```

