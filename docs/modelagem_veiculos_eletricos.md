# Modelagem e Simulação de Veículos Elétricos (Integração Caldera ICM)

Este documento centraliza a metodologia, as decisões arquiteturais e as bases teóricas utilizadas na modelagem dos Veículos Elétricos (VEs) no projeto. Ele detalha a migração de blocos de potência ideais (retangulares) para um modelo eletroquímico de alta fidelidade compilado em C++, utilizando o **Caldera ICM** (Infrastructure Charging Models) desenvolvido pelo *Idaho National Laboratory (INL)*.

---

## 1. O Problema Original vs. A Solução Caldera

**Modelagem Legada:**
Originalmente, os VEs eram representados por blocos constantes e ideais de potência (ex: consumindo exatamente 7.2 kW do instante da conexão até atingir a energia total necessária e, então, desligando abruptamente).

**Solução Caldera:**
O Caldera simula a eletroquímica real das baterias e a resposta dos conversores *CC-CV* (Corrente Constante - Tensão Constante). O impacto central dessa melhoria é a representação fiel do **tapering** (a queda gradativa da potência de carregamento conforme a bateria se aproxima de 80-100% do Estado de Carga - SoC). Essa rampa realista amortece picos de demanda durante a madrugada e eleva a precisão técnica ao calcular perdas na rede de distribuição (via OpenDSS).

---

## 2. Contexto Científico e Processamento da Base de Dados

Os dados estocásticos que guiam os veículos advêm de *smart meters* reais, cujo comportamento precisou ser adaptado para a realidade sociodemográfica brasileira.

### 2.1. A Origem dos Dados
A base de dados empírica advém do estudo *"Residential electric vehicle charging datasets from apartment buildings"* (Sørensen et al., 2021), coletado em Trondheim, Noruega. O *dataset* abriga milhares de sessões reais de recarga contendo o horário de pluge (`t_connect`), desplugue (`t_disconnect`) e a energia consumida (`El_kWh`). 

### 2.2. O Deslocamento Temporal (Time-Shift)
Para transpor o comportamento norueguês para a rede brasileira, o algoritmo de pré-processamento aplicou um **Time-Shift estático de +2,5 horas** nas conexões. Enquanto o motorista europeu tende a chegar em casa e iniciar a recarga por volta das 16h15, o trabalhador brasileiro (somado ao expediente estendido e tráfego) o faz mais tarde. Com o shift, o pico global de carregamentos é concentrado na faixa das **18h30 – 19h00**, forçando a co-simulação no OpenDSS a operar sob estresse térmico máximo, sobrepondo o carregamento veicular à ponta de carga residencial padrão.

### 2.3. Agrupamento Semanal Contínuo
Para não quebrar curvas no meio da noite (ex: um carro plugado domingo às 23h terminando a carga segunda-feira às 02h), as recargas foram serializadas em uma malha contínua. As semanas do mês de Setembro (meia-estação) foram agrupadas mantendo a cronologia fluída dos 10.080 minutos, respeitando o histórico do veículo.

---

## 3. Determinação de SoC e Encadeamento de Sessões

Bases reais de *smart meters* não fornecem a telemetria do painel do carro, logo, o **SoC Inicial** de cada sessão é desconhecido, mas absolutamente obrigatório para dar a ignição na simulação física do Caldera. Para resolver esse obstáculo, implementou-se uma heurística algorítmica matemática baseada na literatura.

### 3.1. O Princípio Matemático
Adotou-se o modelo conceitual validado por **El-Hendawi et al. (2022)**, assumindo que carregamentos residenciais em sua maioria são recargas de destino (buscando encher o tanque a 100%). O SoC Inicial é derivado de forma reversa através da razão entre a energia gasta da rede pela capacidade total da bateria alocada para aquele usuário.

### 3.2. A Regra do Tempo Ocioso ($t_{idle}$) e Sessões Interrompidas
Para evitar falhas na equação quando um motorista realiza carregamentos parciais no meio do dia, o algoritmo monitora o **Tempo Ocioso ($t_{idle}$)** (a janela em que o carro fica conectado subtraída do tempo que ele levaria para carregar em potência nominal).
* Se $t_{idle} > 0$: O carro dormiu na garagem. Ele completou os 100%. A equação de regressão funciona perfeitamente.
* Se $t_{idle} \approx 0$: A sessão foi interrompida de forma abrupta antes de encher o tanque. O algoritmo impõe um SoC Inicial forçado ou herdado para que o Caldera opere estritamente em *Corrente Constante (CC)*, segurando a potência no talo, mimetizando a assinatura estocástica abrupta do *smart meter*.

### 3.3. Memória de Estado (Micro-sessões)
Caso o motorista tire o carro da tomada e reconecte minutos depois, o script de agrupamento implementa uma **Retro-propagação Temporal**. As sessões com gap muito curto (ex: $\le 30$ min) são consideradas eventos sequenciais. O algoritmo retro-calcula o fluxo, obrigando o Caldera a iniciar a Sessão 2 com o exato *SoC Final* que havia sido abandonado na Sessão 1, mantendo o controle termodinâmico contínuo na co-simulação.

---

## 4. Arquitetura de Co-Simulação (Mosaik + C++)

Para garantir o desacoplamento, a ponte entre o motor físico compilado em C++ e a plataforma de coordenação do Mosaik (Python) se divide em duas camadas (*Adapter Pattern*):

### 4.1. Camada de Física de Baterias (`caldera_wrapper.py`)
Encapsula as chamadas diretas ao pacote gerado pelo PyBind11 (`Caldera_ICM_Aux`).
* Inicializa a fábrica de perfis de recarga com discretização de 1 em 1 minuto.
* É a responsável por interpolar o consumo em *Corrente Constante* e as rampas de *Tensão Constante* (fase final da carga).
* Executa o mapeamento da topologia monofásica brasileira (220V Fase-Neutro / 32A), onde as Wallboxes populares (como da BYD, GWM e Geely de $7\text{ kW}$) atuam como carga crítica concentrada.

**Proxy de Química de Bateria:**
Como as gigantes chinesas (BYD e GWM) utilizam massivamente baterias de íon de Lítio-Ferro-Fosfato (LFP) e o Caldera oferece nativamente suporte para perfis *LTO, LMO e NMC*, optou-se por utilizar o inventário **NMC** (Níquel-Manganês-Cobalto) parametrizado no C++. Ambas (NMC e LFP) empregam estratégias de *Battery Management System* análogas de CC/CV, entregando a representação térmica e rampa mais robusta possível para macro-análises de fluxo no OpenDSS.

### 4.2. Camada de Co-simulação no Mosaik (`caldera_ev_sim.py`)
Implementa a interface vital do orquestrador (`mosaik_api_v3.Simulator`).
* No avanço do relógio (`step`), ela acopla as matrizes físicas calculadas pelo Wrapper aos nós elétricos (barramentos) definidos no OpenDSS.
* Modela, minuto a minuto, não apenas o vetor ativo em kW, mas também o **vetor reativo (kVAr)**.

**Modelagem de Fator de Potência (Normas IEC 61000-3):**
Em respeito às exigências internacionais de distorção e injeção harmônica das Wallboxes modernas, o carregador abandona a premissa de um $FP=1,0$.
Para cada Wallbox, um fator de potência permanente é instanciado aleatoriamente $\text{FP}_i \sim \mathcal{U}(0{,}98;\, 1{,}00)$.
Sempre que há afluxo de corrente ativa superior a 50W, a camada deriva o vetor reativo pela trigonometria intrínseca de deslocamento ($\tan \varphi$), despachando para o alimentador do OpenDSS a combinação fiel da potência aparente, simulando com máxima acurácia o estresse reativo no transformador da rua e o desbalanceamento fasorial da rede de distribuição.

---

## 5. Abertura de Portas no Simulador OpenDSS (Override Dinâmico)

No ecossistema OpenDSS/Mosaik tradicional, os elementos de carga (`Load`) são entidades "fechadas" que seguem perfis estáticos nativos do motor (`.dss`). Para permitir o controle externo sem alterar o código-fonte C++ do simulador elétrico, interveio-se no *Wrapper* em Python (especificamente no `element_specs.py`).

### 5.1. A Função Escritora (`write_load`)
Foi injetada uma função customizada na camada de tradução do OpenDSS para o Mosaik:
```python
def write_load(sim, name: str, values: dict[str, Any]) -> None:
    if "P_kw" in values or "Q_kvar" in values:
        sim.dss_wrapper.set_power(name, p=values.get("P_kw"), q=values.get("Q_kvar"), element="Load")
```
Isso permite que os vetores de potência $P$ e $Q$ emitidos a cada minuto pelo simulador Caldera atinjam a API (COM) do OpenDSS e sobrescrevam momentaneamente a potência exigida daquela carga elétrica, bypassando as mecânicas nativas.

### 5.2. Exposição do Contrato (ModelSpec)
O elemento `Load` teve seu escopo alterado de um bloco puramente passivo para um elemento ativo bidirecional (`public=True`). As portas de comunicação `P_kw` e `Q_kvar` foram oficialmente cadastradas como **Inputs** no Mosaik, dizendo ao orquestrador que os nós de bateria do simulador de VE podem ser roteados diretamente (via arestas de grafo) para os barramentos residenciais da rede de distribuição.

---

## 6. O Fluxo de Dados Completo em Co-Simulação (Pipeline Ciberfísico)

O avanço e sincronia do sistema flui da seguinte maneira durante o *Runtime*:

1. **Leitura de Eventos (CSV):** O motor lê o arquivo de inventário estocástico de sessões (`ev_sessions_caldera.csv`), identificando IDs de usuário e timestamps de chegada e partida.
2. **Processamento Físico (Caldera em C++):** A camada `caldera_wrapper.py` recebe esses eventos e projeta o SoC. Instancia digitalmente o equipamento (ex: Wallbox 7kW Monofásica, bateria NMC 50kWh). Calcula eletroquimicamente a demanda minuto a minuto, devolvendo a curva pronta com rampa/tapering (*Corrente Constante / Tensão Constante*).
3. **Simulador de VE (Mosaik - `caldera_ev_sim.py`):** Recebe o fluxo ativo (W) da camada C++. Calcula a porção Reativa Indutiva baseada no Fator de Potência estocástico fixado do nó (Normas IEC).
4. **Simulador OpenDSS (Mosaik - `api_opendss.py`):** Recebe os valores pontuais em $P_{kw}$ e $Q_{kvar}$. Atualiza a matriz de admitância (Fluxo de Carga) incorporando a demanda veicular e devolve as tensões nodais resultantes (perdas, afundamentos de tensão e desbalanceamentos fasoriais).
