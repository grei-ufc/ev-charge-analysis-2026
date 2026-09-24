# Proposta de Integração: Caldera ICM (Idaho National Laboratory)

Este documento registra a metodologia conceitual para substituir o modelo atual de injeção retangular ideal de potência dos Veículos Elétricos (EVs) por modelos físicos de altíssima fidelidade, utilizando o **Caldera ICM** (Infrastructure Charging Models). Esta proposta serve como guia de implementação futura para o projeto.

---

## 1. O Problema Atual vs. A Solução Caldera

**Modelagem Atual:**
Os EVs estão sendo representados por blocos constantes e retangulares de potência (ex: 3.6 kW do momento da conexão até atingir a energia total necessária, desligando abruptamente).

**Solução Caldera:**
O Caldera simula a eletroquímica real de baterias de íons de lítio e a resposta dos conversores *CC-CV* (Corrente Constante - Tensão Constante). O impacto central dessa melhoria é a representação do **tapering** (a queda gradativa da potência de carregamento conforme a bateria se aproxima de 80-100% do State of Charge - SoC). Isso amortece os picos de demanda nas madrugadas e melhora a precisão das perdas elétricas na rede (OpenDSS).

---

## 2. A Limitação dos Dados e a Determinação do SoC Inicial (Metodologia Híbrida)

Bases de dados reais oriundas de *smart meters* (como o *dataset* norueguês adotado) não registram o SoC (State of Charge) interno da bateria do veículo. Elas registram apenas o horário de *plug-in*, *plug-out* e a energia consumida em kWh. O Caldera, por ser um motor físico, exige obrigatoriamente o **SoC Inicial** para iniciar a simulação.

Para solucionar esta lacuna com rigor acadêmico, esta proposta adota uma **metodologia híbrida** fundamentada na literatura técnica recente.

### 2.1. O Modelo Base (El-Hendawi et al., 2022)
O estudo publicado em *Energies* ("Electric Vehicle Charging Model in the Urban Residential Sector", 2022) enfrentou o exato mesmo problema ao modelar cargas residenciais no Canadá. Para determinar o SoC Inicial ($SOC_{0}$), os autores adotaram a premissa de que os veículos sempre carregam até um alvo fixo (no caso deles, 90%). Através de engenharia reversa, o $SOC_{0}$ foi calculado algebricamente subtraindo a razão entre a energia gasta ($E_i$) e a capacidade da bateria ($C_i$):

> $SOC_{0,i} = \left( Target - \frac{E_i}{C_i} \right) \times 100\%$

Esta equação (Equação 3 do artigo) valida o princípio de retro-cálculo determinístico e fornece o embasamento bibliográfico perfeito para o projeto.

### 2.2. A Melhoria Proposta (Filtro de Tempo Ocioso - $t_{idle}$)
O modelo de El-Hendawi possui uma fragilidade: ele assume que *todas* as sessões chegam ao topo (Target), ignorando cargas rápidas interrompidas (comuns durante o dia). Para blindar o TCC contra essa falha física, o nosso algoritmo adiciona um filtro baseado no **Tempo Ocioso ($t_{idle}$)**:

> $t_{idle} = (t_{out} - t_{in}) - \frac{E_i}{P_{max}}$

Com isso, dividimos o tratamento dos dados em dois casos:

* **Caso 1: Sessões Longas ($t_{idle} > 0$)**
  Veículos que pernoitam e têm tempo de sobra. O modelo aplica rigorosamente a Equação de El-Hendawi et al. (2022), assumindo que alcançaram a carga máxima (ex: Target = 100%). O Caldera iniciará a simulação neste $SOC_{0}$ calculado e modelará fisicamente o *tapering* (queda de potência) até a bateria encher.
* **Caso 2: Sessões Interrompidas ($t_{idle} \approx 0$)**
  Veículos que puxaram potência máxima e foram desconectados antes de encher a bateria. A premissa de El-Hendawi falha aqui. O modelo descarta a equação matemática e adota um **SoC Inicial baixo sorteado aleatoriamente**, forçando o Caldera a operar na fase de Corrente Constante (CC), reproduzindo fielmente a potência sustentada observada nos *smart meters*.

### 2.3. Encadeamento Temporal de Sessões Fragmentadas (Memória de Estado)
Bases de dados reais frequentemente apresentam "micro-sessões": o usuário desconecta o veículo rapidamente (ex: para manobrar na garagem) e o reconecta minutos depois. Tratar estes registros como sessões independentes destruiria a continuidade física, fazendo o algoritmo recalcular o SoC inicial do zero para a segunda conexão.

Para adicionar uma dimensão temporal e dotar a simulação de "memória", o algoritmo implementará uma **Retro-propagação Temporal**:
1. **Filtro de Vizinhança:** O código varre os dados buscando sessões consecutivas de um mesmo usuário onde o intervalo $\Delta t = t_{in(\text{Sessão } N+1)} - t_{out(\text{Sessão } N)}$ seja menor que um limiar estipulado (ex: $\le 30$ minutos). Se verdadeiro, as sessões são "aglutinadas".
2. **Transferência de Estado:** O cálculo matemático de SoC é feito de trás para frente. Calcula-se primeiramente a última sessão da cadeia (Sessão 2). O SoC Inicial encontrado para a Sessão 2 torna-se, obrigatoriamente, o **SoC Final da Sessão 1** (assumindo perdas nulas no micro-intervalo).
3. **Recálculo do Elo Anterior:** Com o SoC Final da Sessão 1 travado matematicamente pelo estado seguinte, retro-calcula-se o SoC Inicial da Sessão 1.

Com essa restrição temporal, o Caldera assumirá a bateria no estado exato em que foi pausada na micro-sessão anterior, preservando o histórico físico da curva de decaimento (*tapering*).

---

## 3. Guia de Implementação (Roadmap Técnico)

A execução desta melhoria exigirá alterações em quatro eixos da arquitetura do projeto:

### Fase 1: Compilação do Contêiner
O Caldera ICM requer compilação C++. O `Dockerfile` do projeto precisará ser alterado para:
1. Instalar pacotes base (`cmake`, `g++`, `git`).
2. Clonar o repositório: `git clone https://github.com/idaholab/Caldera_ICM.git`.
3. Executar o build usando `pybind11` para gerar os módulos Python importáveis (`Caldera_ICM` e `Caldera_global`).

### Fase 2: Refatoração do `pipeline_ev.py`
O atual pipeline pré-calcula vetores de potência prontos. Ele deverá ser reescrito para exportar apenas uma **Tabela de Sessões**, contendo:
* ID da Casa
* Timestamps de *plug-in* e *plug-out*
* SoC Inicial (calculado via regras matemáticas de $t_{idle}$)
* Capacidade virtual atribuída àquela bateria (ex: 50 kWh)

### Fase 3: Criação do Simulador Mosaik (Wrapper)
Criação do script `src/simulators/ev/caldera_ev_sim.py` implementando a `mosaik_api_v3`. 
* **`init()`**: Inicializa as instâncias das baterias no ambiente Caldera.
* **`step()`**: Avança a simulação no tempo, consultando o Caldera qual é a potência instantânea demandada por cada EV ativo e repassa esses dados ao Mosaik.

### Fase 4: Orquestração no Cenário (`scenario_ESB01S4_EVs.py`)
No script mestre de co-simulação, o nó `ev_charger` deixará de ser um consumidor burro de CSV e será substituído pelo `caldera_ev_sim`, passando a calcular ativamente a física das baterias antes de enviar as injeções ($P_{kw}$ e $Q_{kvar}$) para as barras de Baixa Tensão do OpenDSS.

