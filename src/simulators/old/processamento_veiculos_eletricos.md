# Documentação Técnica: Processamento de Perfis de Veículos Elétricos (EVs)

Este documento descreve a metodologia e as premissas matemáticas adotadas para transformar eventos brutos de recarga de Veículos Elétricos (arquivos com horários de pluge e energia consumida) em séries temporais discretizadas e normalizadas (LoadShapes), prontas para simulações de fluxo de potência no OpenDSS.

O pipeline completo é gerenciado pelo script `src/ajuste-dados/codigos-evs/orquestrador_ev.py`.

---

## 1. Contexto Científico do Dataset
* **Origem dos Dados:** Os dados brutos pertencem ao estudo *"Residential electric vehicle charging datasets from apartment buildings"* (Sørensen et al., 2021), coletados na cooperativa habitacional Risvollan, em Trondheim, Noruega. O complexo abriga 1.113 apartamentos e mais de 2.300 residentes.
* **Volume de Dados:** O dataset abrange o período de Dezembro de 2018 a Janeiro de 2020, registrando **6.878 sessões de recarga** reais provenientes de **97 usuários** únicos (utilizando carregadores privados e compartilhados).
* **Estrutura dos Eventos:** Os eventos estocásticos são descritos puramente por `t_connect` (horário do pluge), `t_disconnect` e `El_kWh` (energia demandada na sessão).
* **Objetivo do TCC:** O objetivo é transpor essa base real de comportamento estocástico norueguês para um alimentador de distribuição brasileiro (resolução de 10 minutos), focando no mês de Setembro (meia-estação), para análise de fluxo de carga no OpenDSS.

---

## 2. Passo 1: Limpeza e Otimização em Memória (`passo1_limpeza_dados_ev.py`)

A primeira etapa lida com a sanitização da base de dados e gestão de recursos.
* **Tratamento Tipográfico:** Conversão de separadores decimais (vírgulas para pontos) e adequação dos carimbos de tempo para o formato nativo `datetime` do Pandas.
* **Eficiência de RAM:** O orquestrador opera com uma flag de supressão (`manter_todas_colunas=False`). Isso impede o carregamento de dezenas de metadados textuais irrelevantes para o simulador, trafegando apenas o `User_ID` e os números puros de energia/tempo, impedindo sobrecarga de memória nos passos seguintes.
* **Localização (Standalone):** Quando executado isoladamente (fora do orquestrador), o código aplica rotinas de tradução baseadas em dicionários para gerar relatórios em português.

---

## 3. Passo 2: O Deslocamento Temporal (Time-Shift) (`passo2_filtragem_setembro_ev.py`)

Esta é a intervenção de maior impacto sociológico da arquitetura, resolvendo a divergência de comportamento entre motoristas noruegueses e brasileiros.

* **Premissa Norueguesa:** O expediente corporativo termina tipicamente às 16h00 e os deslocamentos são curtos. O pico de conexão dos carros na tomada do dataset original acontece por volta das 16h15.
* **Premissa Brasileira:** O expediente vai até as 18h00, somado ao trânsito pesado que atrasa a chegada em casa.
* **Ajuste Matemático:** Foi aplicado um **Time-Shift estático de +2.5 horas** em todos os horários (`Start_plugin` e `End_plugout`). 
* **Impacto:** O pico global das recargas é empurrado para a faixa das **18h30 – 19h00**, coincidindo brutalmente com a ponta de demanda residencial brasileira. Isso permite que a rede de distribuição simulada no OpenDSS sofra o estresse elétrico no pior cenário possível (simultaneidade máxima).
* **Recorte:** Após o shift temporal, o algoritmo vasculha e extrai apenas semanas fechadas de Setembro (Segunda a Domingo), preservando a continuidade dos dias úteis e finais de semana.

---

## 4. Passo 3: Agrupamento Estrutural (`passo3_agrupamento_semanal_ev.py`)

Para gerar curvas semanais contínuas, os eventos esporádicos precisavam ser vinculados ao seu usuário respectivo.

* **Dicionários Aninhados:** A estrutura em RAM passa de uma tabela linear para: `{Usuário -> {Semana_Index -> DataFrame_de_Sessões}}`.
* **Truncamento de Datas (O Problema da Meia-Noite):** Para evitar que uma sessão iniciada às *14h de segunda* recebesse um identificador semanal diferente de uma sessão às *09h de segunda*, foi aplicada a função `.dt.floor('D')`. Isso "zera" os relógios para a meia-noite, garantindo que qualquer sessão caindo na mesma semana seja aglutinada sob um único índice (ex: `semana_1` a `semana_4`).
* **Integridade Noturna:** Se um veículo for plugado no Domingo às 23h e terminar na Segunda-feira da semana seguinte, a sessão é atrelada à semana em que se iniciou (Domingo), respeitando a física da carga original sem criar quebras abruptas na curva.

---

## 5. Passo 4: O Motor Físico de Discretização (`passo4_geracao_curvas_ev.py`)

Esta etapa preenche a lacuna de "Eventos (Data/Hora)" para "Séries Temporais (LoadShapes)". A abordagem metodológica adotada espelha fielmente a lógica de criação de cargas sintéticas proposta pelos próprios autores do dataset (Sørensen et al., 2021). 
Assume-se o princípio da **Carga Imediata (Immediate Charging)**, onde o veículo passa a demandar potência máxima instantaneamente após o pluge. O orquestrador processa a matriz simulando dois equipamentos nominais testados no estudo original: **3.6 kW** e **7.2 kW**.

O motor resolve dois grandes problemas através de superamostragem (Oversampling):

### 5.1 Alocação em Malha Fina (1 Minuto)
Se operássemos diretamente em blocos de 10 minutos, um carro plugado às 18:07 distorceria o consumo do bloco das 18:00 às 18:10.
A solução foi criar um vetor inicial zerado com **10080 posições** (cada posição = 1 minuto da semana).
1. O algoritmo identifica o minuto exato da conexão (`Start_plugin`).
2. Uma rotina iterativa (`while`) injeta a potência nominal do carregador no vetor, minuto a minuto.
3. Isso ocorre até que a energia requerida (`El_kWh`) esgote, momento em que o carregador passa para estado de ociosidade ($0 kW$), mesmo que o carro permaneça plugado na tomada.

### 5.2 Resampling para o OpenDSS (10 Minutos) e Normalização
1. **A Média Física (Resample):** Após montar os 10080 minutos, aplica-se uma operação de quebra e média vetorial via Numpy: `malha_1min.reshape(-1, 10).mean(axis=1)`.
2. **Impacto:** Os minutos que continham potência nula (ex: 18:00 às 18:06) diluem termodinamicamente os minutos de carregamento em potência máxima (18:07 às 18:09). O resultado é uma potência média extremamente leal ao fenômeno físico naquela janela restrita.
3. **Normalização:** A curva final de **1008 pontos** é dividida pela **potência nominal do carregador** (ex: 7.2 kW). Este formato permite o uso fluido no atributo estático de `LoadShape` do simulador, que re-escala as curvas localmente através do parâmetro estático `kW`.

### 5.3 Sobreposição de Sessões e Análise de Picos (Simultaneidade)
Ao analisar as curvas geradas, observa-se que a maioria maciça dos perfis forma blocos contínuos limitados a `1.0` p.u. (per unit). No entanto, algumas curvas apresentam picos anômalos chegando a `2.0` ou mais. Isso reflete um fenômeno estocástico real da rede de distribuição:
1. **Infraestrutura do Dataset:** Conforme reportado por Sørensen et al. (2021), o identificador `User_ID` refere-se à conta do morador, e não estritamente a uma única tomada física. O complexo habitacional possui vagas **Privadas** e **Compartilhadas (Shared CPs)**.
2. **Física da Sobreposição:** Uma mesma família pode possuir dois VEs carregando simultaneamente, ou autenticar múltiplas recargas em tótens compartilhados. O algoritmo foi desenhado para **somar** as potências no mesmo recorte de tempo quando há sobreposição.
3. **Fator de Coincidência Realista:** Por conta da normalização ter sido ancorada na potência de *um* carregador, a presença de dois veículos sobrepostos cravará o pico matemático em `2.0`. Manter essa anomalia (ao invés de podá-la) é fundamental para simulações no OpenDSS, pois reflete o estresse máximo autêntico e a simultaneidade não-planejada que o transformador de distribuição sofreria no mundo real.

---

## 6. Arquivo de Saída
O orquestrador deságua toda a computação RAM num único repositório otimizado.
* **`ev_loadshapes_normalized.csv`**: Uma planilha onde cada linha representa o degrau temporal de 10 minutos e as colunas armazenam centenas de cenários no formato `[User_ID]_[Semana_Idx]_[Potencia]kW`.
