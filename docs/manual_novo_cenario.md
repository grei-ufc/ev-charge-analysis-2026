# Guia de Criação de Novos Projetos e Cenários (Mosaik + OpenDSS/Pandapower)

Este documento descreve os passos necessários para iniciar um novo cenário ou um projeto totalmente novo em outra pasta, aproveitando a arquitetura de co-simulação existente.

## 1. Arquivos e Pastas para Copiar (Obrigatórios)
Ao criar um projeto em uma nova pasta, você precisa levar a infraestrutura base (o "motor" da simulação):

- **`src/simulators/`**: Copie esta pasta inteira. Ela contém todos os adaptadores Mosaik utilizados no projeto (OpenDSS via `py-dss-interface`, simuladores PV, baterias, controladores, coletores de dados, etc).
- **Gerenciadores de dependência**: Copie o `requirements.txt`, `pyproject.toml` e/ou `uv.lock`. Isso garante que o novo ambiente tenha as mesmas versões das bibliotecas.
- **`src/main.py`**: Serve como ponto de entrada padrão.
- **Cenário Base (Opcional, mas recomendado)**: Copie um cenário existente de `src/scenarios/` (ex: `base_scenario.py` ou `opendss_scenario.py`) para usar como esqueleto (template).

## 2. Estrutura a ser Criada no Novo Projeto
Você deve criar a pasta para organizar os dados da simulação:

- **`src/data/`**: Coloque aqui os arquivos específicos da sua nova rede elétrica (arquivos `.dss` do OpenDSS ou `.json` do Pandapower), assim como os perfis de carga e irradiação solar em `.csv`.
- **`src/scenarios/`**: Salve aqui o seu novo script de cenário (ex: `meu_novo_cenario.py`).

## 3. O que deve ser Editado
A maior parte do trabalho estará no arquivo do novo cenário (`src/scenarios/meu_novo_cenario.py`):

1. **Caminhos de Arquivos**: Atualize as variáveis que apontam para a rede (ex: `GRID_FILE`) e dados tabulares (ex: `PV_DATA`) para apontar para a pasta `src/data/`.
2. **Topologia e Conexões (`world.connect()`)**:
   - Atualize os índices das barras (nodes) onde cargas, geradores, painéis e controladores estão alocados (ex: `indices_nodes_gen`). As barras na nova rede provavelmente terão nomes ou índices diferentes.
3. **Coleta de Resultados**: Altere as instâncias do `monitor` / `Collector` para coletar dados apenas dos componentes relevantes para a nova análise (ex: tensão em barras específicas, carregamento de linhas específicas).
4. **`src/main.py`**: Edite a importação no arquivo principal para chamar a função do novo cenário:
   ```python
   from scenarios.meu_novo_cenario import run_cosimul
   ```


