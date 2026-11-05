# Documentação Técnica do Pipeline Estocástico de Cargas

Este documento detalha pormenorizadamente a engenharia matemática, algorítmica e de software implementada no diretório `src/ajuste-dados/codigos-cargas`. O objetivo central desta metodologia é elevar a modelagem elétrica estática, exigida pela regulação brasileira (PRODIST/ANEEL), para um patamar dinâmico (estocástico), estabelecendo as bases necessárias para simulações avançadas de Redes Inteligentes (*Smart Grids*) e Co-simulação.

---

## 1. Tratamento Avançado da Rede Original (BDGD)

Os dados brutos fornecidos pelas concessionárias brasileiras (BDGD) possuem uma formatação engessada voltada à entrega de relatórios estáticos de planejamento. A transposição dessa rede original para o diretório de simulação (`data/rede/...`) exigiu reestruturações topológicas e sistêmicas rigorosas:

* **Conversão Temporal Contínua (Fim da Fragmentação BDGD):**
  * *O gargalo regulatório:* O padrão ANEEL modela o ano exportando arquivos individuais para cada mês, e subdivide o comportamento elétrico em arquivos isolados para Dias Úteis (DU), Sábados (SA) e Domingos (DO). Essa pulverização impossibilita o estudo de transientes e comportamentos que atravessam os dias operacionais.
  * *A solução estrutural:* O pipeline sintetiza essa pulverização criando **Semanas Contínuas Estocásticas**. O modelo passa a operar com matrizes exatas de 168 horas contínuas em um passo de 10 minutos (1008 pontos). Essa mudança unifica o tecido temporal, permitindo que o simulador avalie a evolução do fluxo de potência passando de uma sexta-feira chuvosa para um sábado ensolarado de forma orgânica.

* **Fidelidade Física do Modelo ZIP (M1 e M2):**
  * *A exigência regulatória:* Para simular a sensibilidade da carga à variação de tensão da rede (Modelo ZIP), a concessionária divide um mesmo cliente de Baixa Tensão em duas parcelas paralelas: uma declarada com `model=2` (Impedância Constante) e outra com `model=1` ou `3` (Potência Constante). 
  * *O problema matemático:* Se o gerador de variáveis aleatórias tratasse as parcelas isoladamente, um mesmo imóvel sortearia duas curvas estatísticas divergentes. Fisicamente, a mesma casa estaria operando sob dois padrões de comportamento humano simultâneos e conflitantes.
  * *A correção algorítmica:* O código utiliza Expressões Regulares (`RegEx`) para varrer o arquivo DSS, isolando sufixos `_M1` e `_M2`. A "identidade base" do cliente é extraída, e uma **única curva estocástica mestre** é gerada na RAM. Ambas as parcelas ZIP da casa são forçadas a herdar a exata mesma assinatura temporal, reagindo unicamente pela física elétrica (tensão) e não mais por discrepâncias estatísticas.

* **Reestruturação do *Master* e da Geração Distribuída (PVSystem):** 
  * As usinas solares na BDGD costumam ser representadas por geradores simplificados (`Generator`) injetando potência fixa negativa (uma "carga invertida"). Esse modelo não respeita curvas de eficiência, inversores ou o sombreamento de nuvens. 
  * Essa estrutura primitiva foi completamente removida do arquivo `Master`. Em seu lugar, injetou-se uma modelagem baseada no elemento `PVSystem`. Este elemento calcula a potência CC baseada em Irradiância ($W/m^2$) e Temperatura, processa a curva do inversor para CA, reproduz limites de *Clipping* (quando os painéis geram mais do que o inversor suporta) e destrava o uso de *Smart Inverters* (ex: funções Volt-Var). 
  * Como resultado, o `Master` tornou-se um arquivo topológico puramente passivo, transferindo toda a dinâmica do tempo, clima e controle para o orquestrador `run_ESB01S4.dss`.

---

## 2. O Pipeline na Memória RAM (Orquestração de Alta Performance)

O fluxo metodológico é disparado pelo orquestrador **`pipeline_cargas.py`**. A arquitetura foi otimizada para executar o processamento matricial (Passos 1 a 3) estritamente na Memória RAM utilizando a biblioteca *Pandas*, sem o gargalo de operações de gravação e leitura em Disco (I/O). 

### Passo 1: Interpolação Hermitiana das Referências (`passo1_dss_para_csv_cargas.py`)
* **A Matemática da Interpolação:** A BDGD fornece curvas rudimentares com $N = 24$ pontos (resolução de 1 hora). O objetivo é refinar o passo para 10 minutos (144 pontos).
  * *Por que não usar Splines Cúbicos tradicionais?* O Spline Cúbico minimiza a curvatura global da função, mas sofre do Fenômeno de Runge (*overshoots*). Ele criaria picos ou vales irrealistas entre os pontos fixos das horas, levando ocasionalmente a consumos artificialmente negativos ou exagerados.
  * *A escolha do PCHIP:* O método **PCHIP** (*Piecewise Cubic Hermite Interpolating Polynomial*) preserva estritamente a monotonicidade local. Se o consumo das 14h às 15h está subindo, os valores interpolados de 10 minutos estarão matematicamente forçados a subir progressivamente, contidos nos limites físicos originais.
* **Condição de Contorno de Meia-Noite:** Polinômios sofrem de instabilidade de derivada nos extremos da série (pontas soltas). Para garantir que a curva se comporte de forma cíclica (periódica), o código clona explicitamente a coordenada de $T=00:00$ no índice temporal $T=24:00$. Isso "amarra" a derivada, forçando a inclinação da curva ao entrar na meia-noite a ser matematicamente idêntica à inclinação de saída no início do dia. Após a interpolação PCHIP, esse ponto fantasma é descartado, legando uma série perfeita de 144 pontos.

### Passo 2: Extração e Rigor Estatístico da Telemetria (`passo2_processar_telemetria_cargas.py`)
* **Alinhamento Geoclimático:** Os dados brutos provenientes de medidores inteligentes (*Smart Meters*) instalados na Austrália (registrados em *Epoch Unix UTC*) sofrem adequação de fuso horário via `tz_convert('Australia/Canberra')`. Isso é vital para que os padrões de comportamento humano (horário de acordar, pico do jantar) se alinhem adequadamente ao sol e aos dias do calendário.
* **Rigoroso Filtro de Qualidade:** O fluxo contínuo é fatiado em blocos diários de 144 passos de 10 minutos. Para evitar o envenenamento da base de dados, estabeleceu-se um funil de qualidade extremo: a presença de um único ponto `NaN` (falha de comunicação do medidor) ou valor negativo (ruído de *hardware*) leva ao **descarte total do dia**. 
  * *Justificativa:* Interpolar dados ausentes criaria anomalias geométricas arbitrárias que destruiriam o critério de similaridade espacial exigido pelo algoritmo Gale-Shapley no Passo 3. Apenas matrizes imaculadas são aprovadas.
* **Classificação Discreta:** Os dados saudáveis são ramificados por dia da semana (`dayofweek`), originando as bibliotecas independentes de Dias Úteis (DU), Sábados (SA) e Domingos (DO).

### Passo 3: Clusterização e Distância RMSE (`passo3_clusterizar_curvas.py`)
Nesta fase, as curvas empíricas australianas são emparelhadas e associadas estritamente às assinaturas regulatórias teóricas do Brasil (BDGD).

#### A. A Matemática da Distância e do RMSE

A alocação das curvas não avalia a grandeza de potência (kW), mas sim a morfologia geométrica do consumo. Portanto, cada array orgânico e de referência sofre normalização individual para P.U. (Por Unidade), onde o eixo $Y$ assume limites rigorosos de $0.0$ a $1.0$ ($p.u. = x_i / \max(x)$).

**A Relação entre Distância Euclidiana e RMSE:**
No código, utiliza-se a função vetorizada do SciPy (`scipy.spatial.distance.cdist`) que extrai a **Distância Euclidiana ($d$)** entre a curva real ($x$) e a teórica ($y$). A fórmula para um vetor de $N$ pontos é:
$$d = \sqrt{ \sum_{i=1}^{N} (x_i - y_i)^2 }$$

A fórmula do **RMSE** (*Root Mean Square Error* ou Raiz do Erro Quadrático Médio) é:
$$RMSE = \sqrt{ \frac{\sum_{i=1}^{N} (x_i - y_i)^2}{N} }$$

Observando as duas equações, nota-se que o numerador do RMSE é exatamente $d^2$. Logo, o código simplifica a computação dividindo a distância por $\sqrt{N}$:
$$RMSE = \sqrt{ \frac{d^2}{N} } = \frac{d}{\sqrt{N}}$$

**O Problema da Distância Euclidiana:**
A Distância Euclidiana pura é inadequada para a avaliação de similaridade de curvas de carga, pois o seu valor é cumulativo e cresce com o tamanho do vetor ($N$). 
Se compararmos duas curvas com 24 pontos, o erro se acumulará 24 vezes, resultando em um valor $d$ arbitrário (ex: `0.4`). Ao comparar as mesmíssimas curvas interpoladas para 144 pontos, o erro se somará 144 vezes, gerando um $d$ muito maior (ex: `1.5`). O valor numérico de $d$ não possui limite pré-estabelecido, consistindo em uma grandeza abstrata que inviabiliza estipular o que é uma "boa similaridade".

**A Grande Sacada (Métrica Universal):**
O **RMSE** neutraliza o efeito da dimensão, dividindo o erro acumulado por $N$. A pergunta matemática que ele responde é simples: *"Em média, qual é a distância entre a curva A e a curva B em um instante de tempo qualquer?"*
Como as curvas de consumo foram normalizadas para P.U. (eixo variando de 0.0 a 1.0), o maior erro possível entre dois instantes isolados seria $1.0$ (um medidor no pico máximo enquanto o outro está no zero absoluto). Consequentemente, o limite estatístico do RMSE estará matematicamente confinado entre $0.0$ e $1.0$.

*Exemplo prático de interpretação:* Se o algoritmo calcular um **RMSE de 0.10**, isso carrega um significado físico irrefutável: significa que, a cada 10 minutos do dia, a curva da telemetria real desvia da referência teórica da ANEEL, em média, em **10%** do seu valor de pico diário.

Para otimizar o ranking de alocação (onde "maior é melhor"), a métrica de erro é invertida em uma métrica de **Similaridade ($Score$)**:
$$Score = 1.0 - RMSE$$
No cenário prático acima, $1.0 - 0.10 = 0.90$. O algoritmo determina que os perfis possuem **90% de Similaridade Média**. 
Essa é uma métrica universal e legível para qualquer analista: independentemente de a curva possuir 24, 144 ou 1008 amostras, uma similaridade de 90% atestará de forma absoluta o mesmo grau de fidelidade geométrica.

#### B. Mecânica do Algoritmo Gale-Shapley (Propositor-Rejeitador)
Evitou-se o uso de notas de corte fixas (*thresholds*) ou metodologias gulosas (*Greedy Algorithms*), as quais tendem a convergir para ótimos locais e abandonar classes sem preenchimento. A alocação ocorre pelo algoritmo de estabilidade global (Gale-Shapley).

**Isolamento por Tipo de Dia:** É fundamental ressaltar que o algoritmo não mistura o calendário. A alocação é executada em três instâncias (arenas) rigorosamente isoladas, respeitando a separação feita no Passo 2. Um dia útil real australiano compete única e exclusivamente contra as referências teóricas BDGD de Dias Úteis. O mesmo isolamento absoluto ocorre para os Sábados e para os Domingos.

A execução de cada arena ocorre da seguinte forma:
1. *Listas de Preferências Pré-calculadas e Fila:* Antes da competição começar, dentro de sua respectiva categoria (ex: Dias Úteis), cada dia australiano calcula sua Similaridade ($Score$) contra *todas* as tipologias BDGD de uma única vez. Com isso, a curva cria uma "lista pessoal" rigorosamente ordenada da sua 1º opção (melhor similaridade) até a última. Em seguida, os dias reais entram na Fila de espera FIFO (`collections.deque`). **FIFO** (*First-In, First-Out*) significa "o primeiro a entrar é o primeiro a sair". Caso uma curva venha a ser ejetada de um balde no futuro, ela será enviada para o final dessa fila para aguardar um novo turno.
2. *Capacidade Restrita (Buckets):* Cada perfil de referência BDGD comporta estritamente um número $K$ máximo de amostras reais associadas ($K=10$ para DU, $K=5$ para SA/DO). A limitação dessas vagas é o motor que **garante a boa semelhança geométrica**. Se os baldes fossem ilimitados, todas as curvas seriam aceitas de imediato no seu primeiro perfil preferido, o que poderia deixar algumas tipologias superlotadas com curvas medíocres e outras tipologias completamente vazias. O gargalo do limite $K$ força a competição e garante a rejeição das curvas divergentes. A diferença de tamanho das vagas ($10$ contra $5$) existe para acomodar a discrepância de volume no calendário real: a base de dados de telemetria possui um volume absoluto muito maior de curvas de Dias Úteis (5 ocorrências semanais) do que Sábados e Domingos.
3. *A Proposta (Confronto):* O dia orgânico sai da fila e solicita vaga na sua Referência de maior preferência atual (ex: sua 1º opção).
4. *Combate, Ejeção e a Próxima Opção:* Se o *bucket* referencial não atingiu seu limite $K$, a curva é aceita. Se estiver lotado, o novato entra em confronto direto com a curva que possui o **pior Score** lá dentro. Se o novato for geometricamente superior (menor RMSE), a curva fraca é sumariamente expulsa do grupo. **A grande eficiência algorítmica ocorre aqui:** a curva ejetada não recalcula as distâncias. Ela simplesmente "risca" o balde atual da sua lista de preferências, consulta qual é a sua *próxima* melhor opção (ex: sua 2º opção) e retorna ao final da Fila FIFO. Em seu próximo turno, ela baterá direto na porta dessa próxima opção.

**Condição de Parada (Convergência Matemática):** O algoritmo iterativo continua rodando estritamente enquanto houver qualquer curva aguardando na Fila FIFO. O processo só para quando a fila chega exatamente a **zero**. Isso ocorre no momento em que absolutamente todas as curvas da telemetria encontraram uma vaga definitiva em algum balde referencial, ou esgotaram a tentativa em todas as tipologias possíveis da sua lista. É uma propriedade fundamental do Teorema de Gale-Shapley garantir que essa convergência ocorra em tempo finito. Quando a fila zera, o sistema atinge a "Estabilidade Global": um cenário perfeito onde não existem mais trocas geométricas vantajosas a serem feitas entre nenhuma curva e nenhum balde.

### Passo 4: Combinação Estocástica e Suavização de Contorno (`passo4_montar_semanas.py`)
A etapa final injeta todo o cruzamento estocástico dentro da topologia do OpenDSS.

* **Sorteio Estocástico via Distribuição Hipergeométrica:**
  * O algoritmo processa as declarações `Load` usando Expressões Regulares (`re.compile`). 
  * Ao reconhecer a base da casa (ex: `RES-Tipo05`), ele acessa o *Bucket* formado no Passo 3. A extração dos 5 Dias Úteis para a semana obedece a um sorteio estritamente **sem reposição** (`random.sample(k=5)`). Isso assegura que um mesmo comportamento australiano não apareça duplicado na semana da mesma residência, forçando o aparecimento de toda a variância intraday e intrawide-week no modelo.
* **A Matemática da Suavização PCHIP de Divisas:**
  * Quando as *Arrays* avulsas (Dias Úteis, Sábados, Domingos) são postas lado a lado via `numpy.concatenate`, formam-se fraturas severas nas emendas da meia-noite (índices múltiplos de 144). Se injetados no OpenDSS, esses "degraus" instantâneos levariam o *Solver* Newton-Raphson à não-convergência, devido a saltos de potência ilógicos para a física de transformadores e cabos.
  * Para solucionar o impasse, o código aplica um "remendo local": uma janela delimitada por $t_{divisa}-2$ a $t_{divisa}+2$ (40 minutos totais de abrangência) é convertida para ausência de dados (`np.nan`).
  * Uma vez que a quina foi apagada, o ambiente convoca a re-interpolação local `pd.interpolate(method='pchip')`. Munido dos pontos saudáveis de trás (23:40) e da frente (00:20), o PCHIP elabora polinômios de Hermite microscópicos atravessando o buraco temporal vazio, garantindo que a conexão entre os dois dias sorteados seja geometricamente ininterrupta, preservando a derivada da carga e a convergência elétrica da simulação.
* **Exportação Definitiva:** O arranjo final unificado é salvo no disco rígido (`Curvas_Semanas_Sinteticas.csv`), hospedando milhares de cronologias independentes com 1008 pontos cada. Simultaneamente, três novos arquivos DSS topológicos são recriados e exportados: `CargasBT_Sintetico`, `CargasMT_Sintetico` e a folha de definições `CurvaCarga_Sintetica`.
* **Integração Final ao Orquestrador (Run):** O corolário lógico desse pipeline reflete diretamente no arquivo de execução principal da simulação (`run_ESB01S4.dss`). Este script foi fundamentalmente reescrito para consumar o novo modelo estocástico:
  1. Ele agora redireciona (`Redirect`) a leitura estritamente para os novos arquivos `_Sintetico.dss`, abandonando as cargas antigas estáticas.
  2. Acopla a modelagem de Geração Distribuída detalhada (`ESB01S4_pv.dss`).
  3. Altera a malha temporal do Solver: o comando de simulação foi ajustado para `Set mode=Daily stepsize=10m number=1008`. Essa exata calibração garante que o OpenDSS varra perfeitamente a resolução de 10 minutos construída nos Passos 1 e 2, executando o fluxo de potência ao longo das 168 horas completas da semana sintética costurada no Passo 4.
