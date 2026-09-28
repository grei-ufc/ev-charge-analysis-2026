# Diário de Implementação: Caldera ICM

Este documento serve como um registro vivo do progresso de implementação da metodologia física de recarga de EVs (Caldera ICM). Ele será atualizado gradativamente conforme avançamos pelas 4 fases propostas no documento conceitual (`proposta_caldera_icm.md`).

---

## 🟢 Fase 1: Compilação e Configuração do Motor C++ (Concluída)

**Objetivo:** Trazer o motor físico do laboratório de Idaho (escrito em C++) para dentro do ecossistema do projeto gerenciado pelo `uv` (Python 3.12).

### Desafios Técnicos Superados:
1. **Ausência de empacotamento padrão:** O repositório oficial do Caldera ICM não utiliza os padrões modernos do Python (`pyproject.toml` ou `setup.py`), inviabilizando a instalação direta via `uv add git+...`. Foi necessário realizar a compilação "nua" via CMake.
2. **Conflito de Versões do Python:** O CMake, ao rodar em nível de sistema, tentou linkar as bibliotecas usando a versão global do Ubuntu (Python 3.14). Como extensões `.so` são estritamente atreladas à versão do compilador, o Python 3.12 do ambiente virtual recusou a importação.
3. **Resolução:** Instalação global dos cabeçalhos do `pybind11` e injeção forçada do caminho do executável Python do ambiente virtual para dentro do CMake.

### Passos Reproduzíveis da Execução:
Para compilar novamente o projeto do zero (ex: em uma nova máquina ou conteinerização final), o fluxo executado foi:

```bash
# 1. Instalação das dependências e headers no sistema (WSL/Ubuntu)
sudo apt-get update
sudo apt-get install -y pybind11-dev python3-dev build-essential cmake git

# 2. Clonagem do repositório em diretório externo ao projeto
cd /mnt/c/Users/pvict/OneDrive/TCC/
git clone https://github.com/idaholab/Caldera_ICM.git
cd Caldera_ICM
mkdir build && cd build

# 3. Compilação forçada apontando para o Python 3.12 do 'uv'
cmake -DPYTHON_EXECUTABLE=/mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/.venv/bin/python ..
make -j4

# 4. Transplante dos arquivos compilados (.so) para o ambiente de simuladores
find . -name "*.so" -exec cp {} /mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/src/simulators/ev/ \;
```

**Resultado:** Sucesso. O script de teste no Python (`import Caldera_ICM`) retornou sem erros, comprovando a integração nativa dos modelos físicos da bateria.

### Fundamentação Tecnológica: Integração C++ e Python (`pybind11`)
Para fins de registro e defesa acadêmica, é importante documentar como ocorre a interoperabilidade entre as linguagens neste projeto:
* **A Necessidade do C++:** Simular a eletroquímica (tensão, corrente, aquecimento e *tapering*) de milhares de veículos elétricos a cada passo de tempo é computacionalmente exaustivo. O motor Caldera ICM foi escrito em C++ para garantir a velocidade e o acesso direto à memória (alta performance), inviáveis em Python puro.
* **A Ponte (`pybind11`):** Para aliar a velocidade do C++ com a facilidade de orquestração do Python (Mosaik), os engenheiros de Idaho utilizaram a biblioteca `pybind11`. Ela atua como um "tradutor simultâneo".
* **O Arquivo Binário (`.so`):** O processo de compilação (CMake/Make) derrete o código C++ bruto e os mapeamentos do `pybind11` em um bloco de código de máquina chamado *Shared Object* (arquivo `.so`, o equivalente a uma `.dll` no Windows). 
* **Em Tempo de Execução:** Ao executar `import Caldera_ICM` no Mosaik, o interpretador Python não procura um arquivo `.py`. Ele carrega o arquivo `.so` compilado. O Python aciona as funções como se fossem nativas, mas o `pybind11` intercepta os parâmetros, entrega para o processamento ultrarrápido do C++, e devolve o resultado final para o Python.

---

## 🟡 Fase 2: Refatoração do Pipeline de Dados (Concluída)

**Objetivo Atual:** Substituir a geração determinística de "blocos quadrados de potência" do antigo script por um **Gerador de Eventos Físicos** baseado no dataset norueguês.

**Lógica a ser implementada (`pipeline_ev.py`):**
1. O pipeline varrerá os dados identificando sessões de recarga por residência.
2. Calculará o **Tempo Ocioso ($t_{idle}$)** para classificar se o carro encheu a bateria ou não.
3. Utilizará a engenharia reversa (Equação 3 de El-Hendawi et al., 2022) para definir o SoC Inicial das sessões completas.
4. Implementará a **Retro-propagação Temporal** para "micro-sessões" com $\Delta t \le 30$ min, garantindo que o SoC Inicial da segunda sessão seja amarrado matematicamente ao SoC Final da primeira.
5. Exportará uma "Tabela de Sessões" (contendo `Hora Início`, `Hora Fim`, e `SoC Inicial`) para ser consumida pelo Mosaik.

---

## ⚪ Fase 3: Criação do Wrapper do Simulador (Pendente)
*Espaço reservado para a documentação da implementação da classe Mosaik-API que controlará o pacote Caldera_ICM em tempo de execução.*

---

## ⚪ Fase 4: Orquestração no Cenário Principal (Pendente)
*Espaço reservado para documentar a fiação das portas (connects) do Caldera injetando a curva P/Q realista no OpenDSS (`scenario_ESB01S4_EVs.py`).*

---

## Anexo: Parametrização da Frota Brasileira (Capacidade de Baterias)
Para garantir a aderência da simulação à realidade da rede de Baixa Tensão brasileira, a capacidade das baterias virtuais será distribuída com base nos **10 veículos eletrificados plug-in mais vendidos no Brasil entre janeiro de 2022 e agosto de 2026**. 
A inclusão conjunta de modelos 100% elétricos (BEV) e híbridos plug-in (PHEV) é fundamental, pois ambos são equipados com carregadores de bordo e conectam-se à rede elétrica (grid) para realizar a recarga de seus bancos de baterias, impactando diretamente o fluxo de carga do cenário simulado.

**Relatório Técnico: Capacidade de Bateria - Top 10 Veículos Eletrificados plug-in mais vendidos (Jan/2022 a Ago/2026)**

| Ranking | Modelo | Fabricante | Capacidade da Bateria | Tipo | Qtd. Vendida | Fonte Técnica / Link |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | BYD DOLPHIN MINI GS5EV | BYD | 38,88 kWh | BEV | 80820 | Ficha técnica BYD |
| 2 | BYD DOLPHIN GS 180EV | BYD | 44,9 kWh | BEV | 58259 | Ficha técnica BYD |
| 3 | BYD SONG PLUS GS DM | BYD | 18,3 kWh | PHEV | 57821 | Ficha técnica BYD |
| 4 | BYD SONG PRO GS DM | BYD | 18,3 kWh | PHEV | 40565 | Ficha técnica BYD |
| 5 | BYD KING GS DM | BYD | 18,3 kWh | PHEV | 22091 | Ficha técnica BYD |
| 6 | GEELY EX2 MAX | GEELY | 39,4 kWh | BEV | 17966 | Ficha técnica GEELY |
| 7 | GWM HAVAL H6 PHEV 19 | GWM | 19,0 kWh | PHEV | 16980 | Ficha técnica GWM |
| 8 | BYD SONG PRO GL DM | BYD | 12,96 kWh | PHEV | 15848 | Ficha técnica BYD |
| 9 | BYD DOLPHIN MINI GS EV | BYD | 38,88 kWh | BEV | 15827 | Ficha técnica BYD |
| 10 | GWM HAVAL H6 GT | GWM | 35,00 kWh | PHEV | 14576 | Ficha técnica GWM |

### Lógica de Atribuição de Frota (Monte Carlo e Restrição Física)
Para alocar os veículos da tabela acima aos perfis virtuais do dataset, o algoritmo utiliza uma dupla camada matemática de seleção:

1. **Filtro Físico de Viabilidade:**
   A energia consumida em uma única sessão ($E_{sessao}$) não pode violar a capacidade máxima da bateria ($C_{bateria}$). O algoritmo identifica a sessão mais extrema da semana ($E_{max}$) e descarta todos os veículos comerciais cuja bateria seja menor que $E_{max}$.
   *Matematicamente:* $C_{bateria} \ge E_{max}$

2. **Distribuição de Probabilidade de Mercado (Roleta Viciada):**
   Dentre os veículos que sobrevivem ao filtro físico, a alocação não é aleatória uniforme. Aplica-se um sorteio ponderado (Distribuição de Probabilidade Discreta) baseado no volume de vendas (Market Share). 
   Sendo $V_i$ as vendas do veículo $i$, o total de vendas do grupo filtrado é $S_{total} = \sum V_i$. A probabilidade de um carro ser atribuído a uma residência é dada por $P_i = \frac{V_i}{S_{total}}$.
