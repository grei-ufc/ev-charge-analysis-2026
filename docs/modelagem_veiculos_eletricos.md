# Modelagem e Simulação de Veículos Elétricos (Integração Caldera ICM)

Este documento centraliza a metodologia, as decisões arquiteturais e as bases teóricas utilizadas na modelagem dos Veículos Elétricos (VEs) no projeto. Ele detalha a migração de blocos de potência ideais (retangulares) para um modelo eletroquímico de alta fidelidade compilado em C++, utilizando o **Caldera ICM** (Infrastructure Charging Models) desenvolvido pelo *Idaho National Laboratory (INL)*.

---

## 1. O Problema Original vs. A Solução Caldera

**Modelagem Legada (Injeção Ideal):**
Originalmente, os VEs eram representados por blocos constantes e ideais de potência. Ou seja, um veículo plugado demandava exatamente 7,2 kW de forma ininterrupta do instante da conexão até atingir a energia total necessária, desligando abruptamente (em degrau). Essa modelagem, embora comum em estudos simplificados, ignora a complexidade eletroquímica do lítio.

**Solução Caldera (Eletroquímica Realista):**
O Caldera simula fisicamente o circuito elétrico equivalente (Equivalent Circuit Model - ECM) das baterias de íons de lítio e a resposta dos conversores *AC/DC* operando em *CC-CV* (Corrente Constante seguida de Tensão Constante). O impacto central dessa melhoria é a reprodução do **tapering** — a queda gradativa, quase exponencial, da potência de carregamento conforme a bateria se aproxima de 80% a 100% de seu Estado de Carga (SoC). Essa rampa realista amortece picos de demanda durante a madrugada, tornando a análise de afundamento de tensão e perdas elétricas no OpenDSS consideravelmente mais rigorosas e ancoradas no mundo físico.

---

## 2. Contexto Científico e Processamento da Base de Dados

Os eventos estocásticos que ditam quando um veículo chega ou sai da tomada advêm de *smart meters* reais, cujo comportamento precisou ser processado e adaptado para refletir a realidade sociodemográfica e de tráfego brasileira.

### 2.1. A Origem dos Dados (Noruega)
A base empírica adotada provém do estudo *"Residential electric vehicle charging datasets from apartment buildings"* (Sørensen et al., 2021), coletado em um complexo habitacional em Trondheim, Noruega. O *dataset* fornece o carimbo exato de *plug-in* (`t_connect`), *plug-out* (`t_disconnect`) e a energia bruta transferida na sessão (`El_kWh`), contemplando tanto finais de semana quanto dias úteis para milhares de sessões reais.

### 2.2. O Deslocamento Temporal (Time-Shift Brasileiro)
O comportamento norueguês diverge do brasileiro. Lá, expedientes terminam mais cedo (ex: 16h00) e os deslocamentos curtos causam um pico de conexões residenciais por volta das 16h15. Para transpor esse comportamento à realidade brasileira — onde o expediente padrão vai até às 18h00 e o tráfego pesado posterga a chegada —, o algoritmo aplicou um **Time-Shift estático de +2,5 horas** nas conexões. 
Com o deslocamento temporal, o pico global de carregamentos concentra-se cirurgicamente na faixa das **18h30 – 19h00**. A genialidade técnica dessa abordagem é forçar o motor do OpenDSS a operar sob estresse térmico máximo, sobrepondo o surto de pluge veicular à ponta de carga residencial padrão do alimentador brasileiro.

### 2.3. Agrupamento Semanal e Integridade Cronológica
Sessões avulsas não funcionam bem em co-simulações dinâmicas. As semanas do mês de Setembro (típicas de meia-estação) foram agrupadas em malhas contínuas de 10.080 minutos (7 dias). Isso garante que veículos que dormem plugados na transição de domingo para segunda-feira não sofram interrupções artificiais nos cálculos físicos do fluxo de potência.

### 2.4. A Arquitetura do Pipeline de Processamento
Todo o tratamento massivo e minucioso da base de dados estocástica é executado de forma estruturada dentro do diretório **`src/ajuste-dados/codigos-evs/`**. O processo é gerenciado pelo script orquestrador `pipeline_ev.py`, que executa 4 módulos sequenciais em RAM (evitando *I/O* em disco intermediário desnecessário):

* **Passo 1 (`passo1_limpeza_dados_ev.py`):** Realiza a sanitização tipográfica e adequação de *datetimes* para padrão ISO, eliminando dezenas de metadados textuais inúteis. 
* **Passo 2 (`passo2_filtragem_setembro_ev.py`):** Módulo sociodemográfico. É aqui que ocorre a injeção do Time-Shift brasileiro (+2,5h) e extrai-se exclusivamente semanas completas do mês de Setembro.
* **Passo 3 (`passo3_agrupamento_semanal_ev.py`):** Módulo de *clustering*. Aplica funções lógicas (`dt.floor('D')`) para atrelar cada evento linearmente ao índice da semana inicial, contornando o "Problema da Meia-Noite".
* **Passo 4 (`passo4_geracao_sessoes_ev.py`):** Módulo Matemático. Aplica as heurísticas de $t_{idle}$ e *Memória de Estado* para extrair o SoC inicial reverso (detalhado no Capítulo 4). O produto final é despejado no arquivo alvo otimizado **`ev_sessions_caldera.csv`**.

---

## 3. A Frota Nacional, Infraestrutura de Carregadores e Alocação Física

A co-simulação no Caldera não permite "cargas fantasmas". Ela exige não apenas os tempos de pluge, mas um mapeamento claro e estrito do veículo (banco de baterias) e da infraestrutura de recarga (inversor/EVSE). Optou-se por utilizar parâmetros fidedignos dos modelos mais vendidos no Brasil.

### 3.1. Inventário de Veículos (Top 10 ABVE)
A simulação engloba BEVs (100% elétricos) e PHEVs (Híbridos Plug-in). Embora os BEVs possuam baterias maiores, os PHEVs carregam frequentemente em residências e impactam o transformador da mesma forma.

| Ranking | Modelo | Fabricante | Capacidade da Bateria | Tipo | Qtd. Vendida (Jan/22-Ago/26) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | BYD DOLPHIN MINI GS5EV | BYD | 38,88 kWh | BEV | 80.820 |
| 2 | BYD DOLPHIN GS 180EV | BYD | 44,90 kWh | BEV | 58.259 |
| 3 | BYD SONG PLUS GS DM | BYD | 18,30 kWh | PHEV | 57.821 |
| 4 | BYD SONG PRO GS DM | BYD | 18,30 kWh | PHEV | 40.565 |
| 5 | BYD KING GS DM | BYD | 18,30 kWh | PHEV | 22.091 |
| 6 | GEELY EX2 MAX | GEELY | 39,40 kWh | BEV | 17.966 |
| 7 | GWM HAVAL H6 PHEV 19 | GWM | 19,00 kWh | PHEV | 16.980 |
| 8 | BYD SONG PRO GL DM | BYD | 12,96 kWh | PHEV | 15.848 |
| 9 | BYD DOLPHIN MINI GS EV | BYD | 38,88 kWh | BEV | 15.827 |
| 10 | GWM HAVAL H6 GT | GWM | 35,00 kWh | PHEV | 14.576 |

### 3.2. Inventário de Carregadores Residenciais (EVSE / Wallboxes)
Em conjunto com a bateria do carro (que recebe energia DC), o Caldera precisa da modelagem do equipamento retificador AC (o EVSE - *Electric Vehicle Supply Equipment*). Em vez de curvas teóricas, adotamos as potências reais das *Wallboxes* frequentemente instaladas nas residências brasileiras (geralmente enviadas como cortesia pela BYD e GWM na compra).

| Fabricante | Equipamento (EVSE) | Potência Máxima | Corrente (Max) | Tensão AC de Operação |
| --- | --- | --- | --- | --- |
| **BYD** | BYD Wallbox AC | 7,0 kW | 32 A | 220 V (Fase-Neutro) |
| **GWM** | GWM Wallbox Série G | 7,0 kW | 32 A | 220 V (Fase-Neutro) |
| **GEELY** | Geely Wallbox AC | 6,6 kW | 32 A | 220 V (Fase-Neutro) |
| **Padrão** | Carregador Portátil Emergência | 3,6 kW | 16 A | 220 V (Fase-Neutro) |

**Implicação Topológica (Desbalanceamento Fase-Neutro):** 
No estado do Ceará, a distribuição opera em 220/380V. Esses carregadores de 7 kW atingem sua tensão e corrente nominais sendo conectados entre **Fase e Neutro**. Portanto, na simulação, cada usuário que possui um EVSE representará uma carga de pico drástica ($32\text{A}$) pendurada em uma única fase do transformador trifásico, tornando-se o agente crítico de desbalanceamento de corrente do sistema elétrico.

### 3.3. Lógica de Atribuição de Frota (Monte Carlo Físico)
Ao processar uma casa do *dataset* norueguês para injetar um veículo brasileiro, o algoritmo usa uma roleta de probabilidades (*Monte Carlo*) baseada no *market-share* de vendas. Porém, existe uma restrição fundamental: **A capacidade real da bateria sorteada ($C_{bateria}$) deve ser maior ou igual ao maior evento de recarga registrado daquele morador na semana ($E_{max}$)**. 
Se um morador consumiu 30 kWh da rede de uma só vez, o algoritmo bloqueia o sorteio de um *BYD Song Plus* (que possui apenas 18,3 kWh) e refaz o sorteio. Isso impede violações termodinâmicas no Caldera, garantindo consistência estrita.

---

## 4. Determinação do SoC Inicial e Retro-propagação da Memória

Como dados empíricos de medidores residenciais (smart meters) apenas reportam consumo bruto e horários de conexão, o **Estado de Carga Inicial ($SoC_{0}$)** de cada sessão — parâmetro vital para o C++ iniciar a integração eletroquímica — é misteriosamente oculto. Resolvemos isso com um arcabouço matemático algorítmico baseado na literatura técnica (El-Hendawi et al., 2022).

### 4.1. Equacionamento Matemático pelo Tempo Ocioso ($t_{idle}$)
O cerne do modelo repousa na avaliação do tempo em que o veículo passa dormindo na garagem. Se subtrairmos o tempo que ele demoraria na teoria para absorver toda a energia ($E / P_{nom}$) do tempo em que ele de fato permaneceu plugado, temos o tempo ocioso ($t_{idle}$).

* **Sessão Longa ($t_{idle} > 0$):**
  Se houve folga temporal de madrugada, matematicamente o usuário completou sua meta (bateria chegou a 100%). A equação para rastrear o SoC inicial ($SoC_0$) em que ele chegou na garagem é simplesmente a engenharia reversa do "tanque cheio":
  $$SoC_{0} = \left( 1.0 - \frac{E_{gasta}}{C_{bateria}} \right)$$
  Sob essa condição matemática, o modelo Caldera se encaixa de forma majestosa, exibindo claramente o achatamento e a curva lenta do *tapering* quando a energia atinge as frações finais.

* **Sessão Interrompida / Rápida ($t_{idle} \approx 0$):**
  Aquele morador que deu uma carga rápida ao meio-dia e desplugou. Aqui, a premissa de alcançar 100% quebra. Nessas raras exceções, o algoritmo impõe um $SoC_{0}$ muito baixo, segurando propositalmente a eletroquímica na fase de **Corrente Constante (CC)** para que a absorção de energia do veículo seja mantida reta em potência máxima (sem tapering), imitando fielmente o corte estocástico das cargas parciais dos medidores originais.

### 4.2. A "Memória" da Bateria (Retro-propagação)
Sessões de recarga residenciais podem exibir falhas de "pluge rápido" (quando o motorista desliga e religa o carro na tomada logo depois para manobrar o veículo). Tratar essas sessões como coisas distintas causaria um reset irreal da bateria no Caldera.
A solução aplicada foi a **Retro-propagação Temporal**: o pipeline junta conexões separadas por menos de 30 minutos em um *cluster*. O cálculo do SoC roda do futuro para o passado, amarrando forçadamente o *SoC Inicial* da segunda micro-sessão para que seja idêntico ao *SoC Final* em que a primeira havia sido abandonada. Isso dota a co-simulação de memória e persistência de dados ao longo de todo o mês.

---

## 5. Arquitetura de Co-Simulação e Fluxo Ciberfísico (Mosaik + C++)

Uma co-simulação dessa magnitude não roda em um único arquivo. A arquitetura foi bipartida. 

```mermaid
flowchart TB
    %% Estilos limpos e compativeis
    classDef python fill:#ffd43b,stroke:#306998,stroke-width:2px,color:#111,rx:8,ry:8;
    classDef cpp fill:#00599C,stroke:#002244,stroke-width:2px,color:#fff,rx:8,ry:8;
    classDef grid fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff,rx:8,ry:8;
    classDef data fill:#f1f3f5,stroke:#495057,stroke-width:2px,color:#111,rx:8,ry:8;
    classDef cache fill:#e8590c,stroke:#d9480f,stroke-width:2px,color:#fff,rx:8,ry:8;

    subgraph Caldera["⚙️ Motor Fisico Caldera ICM (C++ em Lote)"]
        direction TB
        CSV_INV[("Inventarios Fisicos<br>EV e EVSE (CSVs)")]
        WRAP["caldera_wrapper.py<br>(Camada Fisica)"]
        
        EVSE["EVSE (Wallbox AC)"]
        BMS["Vehicle Charge Model (BMS)"]
        BAT[("Battery Model (ECM)")]
        CONV["AC/DC Converter"]
        
        LIB[("Biblioteca de Perfis em RAM<br>(Pre-calculo CC-CV)")]
        
        CSV_INV --> WRAP
        WRAP --> EVSE
        EVSE -- "P_max (AC)" --> BMS
        BAT -. "SoC e V_oc" .-> BMS
        BMS -- "Fase CC/CV" --> BAT
        BAT -- "Atualiza SoC" --> BAT
        BMS -- "Demanda DC" --> CONV
        CONV -- "Compilacao de Perfil" --> LIB
    end

    subgraph Mosaik["🐍 Orquestrador Mosaik (Python)"]
        direction TB
        SESS[("ev_sessions_caldera.csv<br>(Sessoes Estocasticas)")]
        SIM(["caldera_ev_sim.py<br>(Simulador Mosaik)"])
        DECISOR{"EV conectado<br>no minuto t?"}
        CALC["Calculo P(t) e Q(t)<br>com FP IEC 61000"]
        
        SESS -- "Agenda (Start, End)" --> SIM
        SIM -- "step(t)" --> DECISOR
        DECISOR -- "Sim" --> CALC
    end

    subgraph Grid["⚡ Rede Eletrica Distribuicao"]
        DSS[("OpenDSS<br>(Newton-Raphson BT)")]
    end

    %% Conexoes cruzadas
    SESS -- "Vetor SoC_0 e Alvo" --> WRAP
    LIB -- "Curva P Fisica Tapering" --> SIM
    CALC -- "Injeta P (kW) e Q (kVAr)" --> DSS

    %% Classes
    class CSV_INV,SESS data;
    class WRAP,SIM,DECISOR,CALC python;
    class EVSE,BMS,BAT,CONV cpp;
    class LIB cache;
    class DSS grid;
```

### 5.1. Engenharia Reversa da API do Caldera (PyBind11)
Uma das maiores barreiras de desenvolvimento enfrentadas na integração foi a total ausência de documentação Python para a biblioteca do Caldera ICM. O motor do *Idaho National Laboratory* é puramente construído em *C++* e exposto ao Python como um binário compilado (Shared Object `.so`) através da biblioteca `pybind11`. 

Isso significa que o código-fonte legível fica oculto; IDEs não conseguem inferir tipos, métodos ou assinaturas, e a biblioteca se comporta como uma "caixa preta". Para viabilizar a arquitetura, procedeu-se com uma autêntica **Engenharia Reversa da Interface**:
1. **Inspeção de Memória em Tempo de Execução:** Desenvolvemos scripts temporários exploratórios (`dir()`, `getattr`) para varrer e listar ativamente os objetos carregados em memória ao importar os módulos `Caldera_models` e `Caldera_ICM_Aux`.
2. **Extração de Assinaturas (Help Dumps):** Capturamos o fluxo de saída da função nativa `help()` do Python e o redirecionamos para arquivos de texto, gerando o artefato `src/simulators/ev/caldera_api_docs_full.txt`. Esse "Dicionário" revelou a existência e as exigências contratuais da classe mestra `CP_interface_v2`.
3. **Mapeamento de Enumeradores Estritos:** Foi vasculhando o atributo de baixo nível `.__members__` das classes C++ que descobrimos restrições vitais que não constavam em manual algum, como a descoberta de que o motor limitava as químicas de bateria (`battery_chemistry`) exclusivamente a três opções internas: `LTO`, `LMO` e `NMC`, o que forçou a próxima decisão arquitetural de *proxy* detalhada abaixo.

### 5.2. A Camada C++ e a Química NMC (O Proxy para LFP)
A modelagem C++ exige informar a química das células galvânicas da bateria. Os carros líderes do Brasil (BYD/GWM) dominam o uso da tecnologia *Blade Battery* ou químicas de **LFP** (Lítio-Ferro-Fosfato) pela segurança e resistência térmica. Entretanto, o motor compilado do Caldera possui classes pré-moldadas estritas apenas para LTO, LMO e **NMC**. 

A solução de engenharia adotada foi forçar todas as baterias LFP como baterias **NMC** (*Níquel-Manganês-Cobalto*). O pretexto científico se baseia em que o BMS (Sistema de Gerenciamento da Bateria) atua nas LFP de forma quase idêntica às NMC para salvaguarda: uma pesada carga em Corrente Constante (CC) em tensões nominais que sobem, e no final, grampeamento em Tensão Constante (CV) fazendo o *tapering*. O "erro" do proxy é puramente interno, pois, olhando macroscopicamente do lado da rede elétrica AC (OpenDSS), a demanda temporal desenhada se mostra excepcional para ambas tecnologias.

### 5.3. Cálculo Dinâmico do Fator de Potência e Injeção de Reativos (Normas IEC)
Outro diferencial desta modelagem é não tratar VEs como cargas inteiramente resistivas (como lâmpadas incandescentes onde a potência reativa $Q = 0$).

Os circuitos AC/DC dos carregadores automotivos (on-board e off-board) possuem retificadores com pontes de diodos e capacitores. Para impedir a poluição com altas taxas de THDi (Distorção Harmônica), eles empregam a técnica de Correção Ativa do Fator de Potência (*Active PFC*), exigida pelas normas globais **IEC 61000-3-2** (para portáteis de 16A) e **IEC 61000-3-12** (para Wallboxes pesadas >16A).

Ainda que o PFC esforce a corrente a imitar o formato senoidal da tensão — mantendo o Fator de Potência (FP) extremamente próximo de 1,0 —, os filtros passivos EMI da entrada causam defasagem residual, tornando o conjunto **ligeiramente indutivo** ou **capacitivo** na perspectiva da concessionária. 

A nossa simulação emula rigorosamente este fenômeno:
1. **Sorteio do Fator de Potência Estocástico:** Na inicialização da simulação, toda residência que possua um VE sorteia um fator inalterável entre 0,98 e 1,00 para aquela semana. $\text{FP}_i \sim \mathcal{U}(0{,}98;\, 1{,}00)$
2. **Cálculo de Deslocamento Angular:** A partir de trigonometria de potência fundamental (onde $\text{FP} = \cos \varphi$), achamos o fator multíplice de injeção reativa:
   $$\tan \varphi = \frac{\sin \varphi}{\cos \varphi} = \frac{\sqrt{1 - \text{FP}_i^2}}{\text{FP}_i}$$
3. **Injeção em Tempo de Execução:** Em cada milissegundo de passo simulado (`step(t)`), se o carro do morador puxar exatos $6,8\text{ kW}$ da matriz física C++, a camada Python Mosaik aplica simultaneamente um puxão reativo correspondente (ex: $Q = 6,8 \cdot \tan \varphi \approx 1,38\text{ kVAr}$ indutivos).
Isso pune a tensão do transformador da rua tanto pelo lado ativo quanto reativo, aumentando o desbalanceamento real.

---

## 6. Override Dinâmico no OpenDSS (Portas Abertas)

No ambiente nativo, o motor de fluxo de potência da EPRI (OpenDSS) costuma operar sozinho: você escreve um perfil longo `.dss`, liga e espera o fim. Contudo, em uma co-simulação de rede elétrico-computacional acoplada, quem detém a inteligência do que a casa consome é o *Mosaik* e o *Caldera*, não mais o arquivo estático.

Para impor isso sem ter de reconstruir o núcleo C++ do OpenDSS, escrevemos uma "cláusula de *Override*" na API COM (a ponte Python `dss_wrapper` e no `element_specs.py`). 

A rotina reclassifica a variável nativa `Load` e declara que suas propriedades `P_kw` e `Q_kvar` são **Inputs Públicos Bidirecionais**. 
Quando a função `write_load` escuta o vetor do Caldera chegando a cada *step* (ex: aos 12 minutos e 40 segundos da simulação), ela emite um comando COM direto para a engine do OpenDSS: 
```python
sim.dss_wrapper.set_power(name="Load.casa_1", p=7.0, q=1.38, element="Load")
```
Essa invasão na memória permite que a rede de distribuição responda em malha instantânea à estocástica norueguesa, processando e avaliando o comportamento do afundamento nodal de modo 100% dinâmico.

---

## 7. Fontes e Referências Técnicas Referidas

1. **Dataset Original de Comportamento e Telemetria:** 
   SØRENSEN, A. L., *et al*. "Residential electric vehicle charging datasets from apartment buildings". *Data in Brief*, v. 36, p. 107105, 2021. Disponível em repositório acadêmico livre. (Alicerçou a base estocástica para transpor os 10.080 minutos de pluge/despluge de 2.300 residentes).
2. **Engenharia Reversa Estocástica do SoC ($t_{idle}$):** 
   EL-HENDAWI, M., *et al*. "Electric Vehicle Charging Model in the Urban Residential Sector". *Energies*, v. 15, n. 21, p. 7979, 2022. (Metodologia analítica e matemática adotada para derivar o SoC ignorado pelo dataset via limitação da janela ociosa na madrugada).
3. **Engine Física de Baterias (Caldera ICM):**
   *Idaho National Laboratory (INL)*. Caldera Infrastructure Charging Models (ICM). Biblioteca Open-source em C++ para termodinâmica, degradação química, L2, DCFC e controle vetorial CC-CV no domínio do tempo. [idaholab/Caldera_ICM](https://github.com/idaholab/Caldera_ICM).
4. **Normativas Técnicas de Despacho Reativo e Limites THDi:** 
   INTERNATIONAL ELECTROTECHNICAL COMMISSION (IEC). *IEC 61000-3-2 (Ate 16A) / IEC 61000-3-12 (Até 75A)*: Electromagnetic compatibility (EMC). Normas globais mandatórias aplicadas na justificação matemática do ruído capacitivo/indutivo nas pontes retificadoras e *Active PFC* dos carregadores em baixa tensão AC.
5. **Inventário Oficial da Frota ABVE (Jan/2022 a Ago/2026):** 
   Associação Brasileira do Veículo Elétrico (ABVE) - Catálogo e *market-share* de eletrificados brasileiro. Fichas técnicas das montadoras *Build Your Dreams (BYD)*, *Great Wall Motors (GWM)* e *Geely*. Usadas para validar nominalidade de baterias e Wallboxes monofásicas de $7\text{ kW}$ e $6,6\text{ kW}$ aplicadas no método *Monte Carlo*.

