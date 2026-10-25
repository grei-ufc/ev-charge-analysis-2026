# Metodologia de Análise Comparativa Diferencial e Relativa dos Cenários de VEs

Este documento estabelece a fundamentação metodológica, as formulações matemáticas e os critérios analíticos para a comparação dos cenários de penetração de Veículos Elétricos (VEs) no alimentador real **ESB01S4** (Neoenergia Cosern), adotando uma **abordagem estritamente diferencial e relativa ao Caso Base (0 VEs)**.

---

## 1. Justificativa Epistemológica: O Princípio do Isolamento da Variável Experimental

A análise convencional de fluxo de potência frequentemente reporta grandezas absolutas (por exemplo: *"a rede apresentou 2.800 horas de tensão crítica"* ou *"o pico foi de 1.800 kW"*). Em redes reais complexas que já possuem geração distribuída fotovoltaica (GD-FV) massiva integrada — como o alimentador ESB01S4, com 303 sistemas solares ativos —, essa abordagem introduz graves vieses analíticos:

1. **Vieses Pré-existentes na Rede:** No Caso Base (0 VEs), o alimentador já opera com transgressões severas de sobretensão diurna ($\text{DRP}_{\text{sob}}$ e $\text{DRC}_{\text{sob}}$) decorrentes da injeção solar em barras residenciais no meio do dia (11h00 às 14h00), bem como problemas prévios de desbalanceamento e baixo fator de potência na linha tronco.
2. **Atribuição Indevida de Causalidade:** Avaliar apenas números absolutos atribuiria erroneamente aos Veículos Elétricos problemas de qualidade de energia causados pela geração solar diurna ou pela impedância natural de ramais longos.
3. **Isolamento da Causa-Efeito:** Ao mensurar o impacto de forma **diferencial ($\Delta$) e relativa ($\% \Delta$)** contra a simulação síncrona do Caso Base ($0\text{ VEs}$), a influência da topologia, das cargas residenciais existentes e dos 303 sistemas fotovoltaicos é cancelada algebricamente. O resultado isola com 100% de precisão **o efeito causado EXCLUSIVAMENTE pela adição da frota veicular**.
4. **Universalidade e Comparabilidade Internacional:** A variação percentual normalizada ($\% \Delta$) independe da potência nominal da subestação, permitindo a comparação direta dos resultados deste TCC com pesquisas internacionais de referência (CLEMENT-NYNS; HAESEN; DRIESEN, 2010; RAHMAN et al., 2022).

---

## 2. Formulações Matemáticas das Grandezas Diferenciais e Relativas

Para cada cenário de penetração $p \in \{5, 10, 15, 20, 25, 30, 35, 40, 45, 50\}\%$, as métricas são calculadas em relação ao Caso Base ($p = 0\%$, indexado como $\text{base}$).

```
                             SÉRIES TEMPORAIS SÍNCRONAS
      Cenário Base (0% VEs)              Cenário Avaliado (p% VEs)
     [X_base(t), t = 1..1008]           [X_p(t), t = 1..1008]
                │                                  │
                └─────────────────┬────────────────┘
                                  ▼
                   OPERADOR DIFERENCIAL INSTANTÂNEO
                        ΔX(t) = X_p(t) - X_base(t)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
 [Impacto Absoluto Δ]      [Impacto Relativo %Δ]   [Taxa Marginal dY/dX]
  ΔX = X_p - X_base         %ΔX = (ΔX / X_base)*100   η = ΔPerdas / ΔEnergia_VE
```

---

### 2.1. Pico Máximo de Demanda Coincidente e Fator de Carga

O carregamento simultâneo no início da noite (18h30 às 20h30) sobrepõe-se à ponta residencial, aumentando a demanda na subestação.

* **Impacto Diferencial no Pico:**
  $$\Delta P_{\max}(p) = P_{\max}(p) - P_{\max}(\text{base}) \quad [\text{kW}]$$

* **Impacto Relativo Percentual no Pico:**
  $$\% \Delta P_{\max}(p) = \frac{P_{\max}(p) - P_{\max}(\text{base})}{P_{\max}(\text{base})} \times 100\%$$

* **Impacto na Demanda Aparente e Ampacidade da Subestação:**
  $$\% \Delta S_{\max}(p) = \frac{S_{\max}(p) - S_{\max}(\text{base})}{S_{\max}(\text{base})} \times 100\%$$

* **Variação do Fator de Carga Semanal ($\Delta FC$):**
  $$FC(p) = \frac{P_{\text{médio}}(p)}{P_{\max}(p)}, \quad \Delta FC(p) = FC(p) - FC(\text{base})$$
  *(Um $\Delta FC < 0$ indica que a rede está se tornando mais ociosa no vale e excessivamente pontiaguda na recarga noturna).*

---

### 2.2. Perdas Técnicas de Energia por Efeito Joule ($I^2 R$)

Pela Lei de Joule, a dissipação térmica nos cabos e enrolamentos de transformadores é quadrática em relação à corrente.

* **Perdas Técnicas Incrementais:**
  $$\Delta E_{\text{perdas}}(p) = E_{\text{perdas}}(p) - E_{\text{perdas}}(\text{base}) \quad [\text{kWh}]$$

* **Impacto Relativo Percentual nas Perdas:**
  $$\% \Delta E_{\text{perdas}}(p) = \frac{E_{\text{perdas}}(p) - E_{\text{perdas}}(\text{base})}{E_{\text{perdas}}(\text{base})} \times 100\%$$

* **Taxa Marginal de Perdas ($\eta_{\text{marginal}}$):**
  Relação fundamental que quantifica a perda adicional no alimentador para cada kWh transferido para as baterias dos VEs:
  $$\eta_{\text{marginal}}(p) = \frac{\Delta E_{\text{perdas}}(p)}{E_{\text{VEs}}(p)} \quad \left[\frac{\text{kWh perdas}}{\text{kWh recarga}}\right]$$
  *(Se $\eta_{\text{marginal}} = 0{,}15$, significa que 15% de toda a energia injetada para carregar os VEs foi desperdiçada em calor nos condutores).*

---

### 2.3. Afundamento de Tensão Nodal Diferencial ($\Delta V$)

Para cada nó secundário $i \in \{1, \dots, N_{\text{barras}}\}$ e para cada instante de tempo $t$:

$$\Delta V_i(t) = V_{i,p}(t) - V_{i,\text{base}}(t) \quad [\text{pu}]$$

* **Afundamento Máximo Nodal Provocado por VEs:**
  $$\Delta V_{\max,\text{drop},i} = \min_{t} \left( V_{i,p}(t) - V_{i,\text{base}}(t) \right) \quad [\text{pu}]$$
  *(Identifica a severidade do afundamento estritamente veicular, permitindo construir o Mapa de Calor de Fragilidade da Baixa Tensão).*

* **Degradação da Tensão Mínima Global do Alimentador:**
  $$\Delta V_{\min}(p) = V_{\min}(p) - V_{\min}(\text{base}) \quad [\text{pu}]$$

---

### 2.4. VDI Diferencial e Decomposição de Polaridade (NWOBU et al., 2026)

O Voltage Deviation Index quantifica o desvio contínuo em relação à tensão ideal ($1{,}0\text{ pu}$):

$$\text{VDI}_i^2(t) = (V_i(t) - 1{,}0)^2$$

* **Variação Relativa do VDI RMS Global:**
  $$\Delta \text{VDI}_{\text{RMS}}(p) = \text{VDI}_{\text{RMS}}(p) - \text{VDI}_{\text{RMS}}(\text{base}) \quad [\%]$$

* **Acréscimo Relativo Exclusivo de Subtensão ($\% \Delta \text{VDI}_{\text{sub}}$):**
  $$\text{VDI}_{\text{sub}}(t) = \sum_{i,\, V_i < 1{,}0} (1{,}0 - V_i(t))^2$$
  $$\% \Delta \text{VDI}_{\text{sub}}(p) = \frac{\text{VDI}_{\text{sub}}(p) - \text{VDI}_{\text{sub}}(\text{base})}{\text{VDI}_{\text{sub}}(\text{base})} \times 100\%$$
  *(Esta métrica isola perfeitamente o distúrbio noturno dos VEs, sem contaminação pela sobretensão gerada pelos 303 PVs).*

---

### 2.5. Conformidade Regulatória PRODIST Desagregada (MARINHO et al., 2026)

Conforme Marinho et al. (2026), os indicadores normativos agregados ($DRP \le 3{,}0\%$ e $DRC \le 0{,}5\%$) são decompostos em componentes de subtensão e sobretensão:

$$\text{DRP} = \text{DRP}_{\text{sub}} + \text{DRP}_{\text{sob}}, \quad \text{DRC} = \text{DRC}_{\text{sub}} + \text{DRC}_{\text{sob}}$$

* **Variação Diferencial de Transgressão de Tensão:**
  $$\Delta \text{DRP}_{\text{sub}}(p) = \text{DRP}_{\text{sub}}(p) - \text{DRP}_{\text{sub}}(\text{base}) \quad [\%]$$
  $$\Delta \text{DRC}_{\text{sub}}(p) = \text{DRC}_{\text{sub}}(p) - \text{DRC}_{\text{sub}}(\text{base}) \quad [\%]$$

* **Novas Barras Transgressoras Induzidas por VEs:**
  Quantifica quantas barras que operavam em conformidade no Caso Base foram empurradas para a não conformidade exclusivamente pela carga dos VEs:
  $$\Delta N_{\text{barras},\text{DRP}}(p) = N_{\text{barras}}(\text{DRP} > 3{,}0\%)_p - N_{\text{barras}}(\text{DRP} > 3{,}0\%)_{\text{base}}$$
  $$\Delta N_{\text{barras},\text{DRC}}(p) = N_{\text{barras}}(\text{DRC} > 0{,}5\%)_p - N_{\text{barras}}(\text{DRC} > 0{,}5\%)_{\text{base}}$$

---

### 2.6. Sobrecarga e Vida Útil de Transformadores MT/BT

Para cada transformador secundário $k$:

$$\Delta \text{Loading}_k(p) = \max_t \left( \frac{S_k(t)}{S_{\text{nom},k}} \right)_p - \max_t \left( \frac{S_k(t)}{S_{\text{nom},k}} \right)_{\text{base}} \quad [\%]$$

* **Novos Transformadores em Sobrecarga:**
  $$\Delta N_{\text{trafos},>100\%}(p) = N_{\text{trafos}}(S_{\max} > S_{\text{nom}})_p - N_{\text{trafos}}(S_{\max} > S_{\text{nom}})_{\text{base}}$$
* **Horas Incrementais em Sobrecarga Térmica:**
  $$\Delta H_{>100\%}(p) = \sum_k \left( \text{Horas}(S_k > S_{\text{nom}})_p - \text{Horas}(S_k > S_{\text{nom}})_{\text{base}} \right) \quad [\text{h/semana}]$$

---

### 2.7. Modelo de Adoção Incremental Aninhada (*Nested Adoption Model*)

Para assegurar que a comparação diferencial seja estritamente causal e livre de flutuações estocásticas induzidas por reamostragem, a parametrização dos cenários adota o **Modelo de Difusão Cumulativa de Rogers (2003) e Bass (1969)**, detalhado em [`docs/metodologia_alocacao_incremental_aninhada.md`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/docs/metodologia_alocacao_incremental_aninhada.md):

* Seja $\mathcal{F}_{\text{adoção}} = (d_{(1)}, d_{(2)}, \dots, d_{(947)})$ a Fila Universal de Adoção canônica do alimentador.
* Para qualquer cenário $p_k \in \{5, 10, \dots, 50\}\%$, o conjunto de veículos $\mathcal{V}(p_k)$ é um subconjunto estritamente contido no cenário subsequente:
  $$\mathcal{V}(5\%) \subset \mathcal{V}(10\%) \subset \mathcal{V}(15\%) \subset \dots \subset \mathcal{V}(50\%)$$
* **Garantia Eletrotécnica:** Cada domicílio participante mantém seu perfil de recarga ($3{,}6\text{ kW}$ ou $7{,}2\text{ kW}$) e fase de conexão invariantes em todos os cenários. Com isso, qualquer nova violação regulatória ($\Delta N_{\text{barras}} > 0$) ou afundamento nodal ($\Delta V_{\min} < 0$) reflete a **adição cumulativa real de novos carregadores**, eliminando ruídos amostrais artificiais.

---

## 3. Determinação da Capacidade de Hospedagem (*Hosting Capacity*)

A Capacidade de Hospedagem do alimentador ESB01S4 é formalizada pelo **mínimo percentual de penetração $p^*$** no qual qualquer um dos seguintes critérios de corte físico/regulatório é violado em decorrência dos VEs:

$$p^* = \min \{ p \mid \text{Critério}_j(p) = \text{Violado} \}$$

Onde os critérios de corte são:
1. **Critério 1 (PRODIST Subtensão Crítica - MARINHO et al., 2026):** $\Delta N_{\text{barras},\text{DRC}} > 0$ (surgimento da primeira barra com transgressão de DRC por subtensão veicular).
2. **Critério 2 (Limite Absoluto de Tensão Crítica - ANEEL, 2021):** $V_{\min}(p) < 0{,}87\text{ pu}$ no horário de recarga noturna.
3. **Critério 3 (Regra do VDI Máximo - NWOBU; OBI; ODIGBO, 2026):** Disparo exponencial no índice contínuo de distúrbio de subtensão ($\% \Delta \text{VDI}_{\text{sub}} \gg 100\%$).
4. **Critério 4 (Sobrecarga de Transformadores):** $\Delta N_{\text{trafos},>100\%} > 0$ (primeiro transformador MT/BT a operar em sobrecarga térmica provocada por VEs).
5. **Critério 5 (Ampacidade da Linha Tronco):** $I_{\text{tronco},\max}(p) > I_{\text{adm}}$.

---

## 4. Estrutura dos Gráficos e Resultados Comparativos no TCC

As figuras da dissertação serão construídas enfatizando a escala relativa (geradas em 300 DPI por [`src/simulators/util/analisador_grade_tcc.py`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/src/simulators/util/analisador_grade_tcc.py)):

1. **Figura 1: Curva de Impacto Relativo Duplo (Pico e Energia vs. Penetração):**
   * Eixo X: Taxa de Penetração (0% a 50%).
   * Eixo Y Primário (Esquerda): $\% \Delta P_{\max}$ (Acréscimo percentual do pico).
   * Eixo Y Secundário (Direita): $\% \Delta E_{\text{semanal}}$ (Acréscimo percentual da energia entregue).
2. **Figura 2: Capacidade de Hospedagem e Novas Transgressões Regulatórias ($\Delta N_{\text{barras}}$ vs. Penetração):**
   * Curva demonstrando o limiar exato de *Hosting Capacity* ($p^* = 15\%$) onde $\Delta N_{\text{barras},\text{DRC\_sub}}$ deixa de ser zero e surgem as primeiras barras críticas.
3. **Figura 3: VDI de Subtensão Noturna Relativo (NWOBU; OBI; ODIGBO, 2026):**
   * Gráfico demonstrando o crescimento exponencial de $\% \Delta \text{VDI}_{\text{sub}}$ decorrente do distúrbio acumulado de recarga noturna.
4. **Figura 4: Afundamento da Tensão Mínima Global ($V_{\min}$ vs. Limites PRODIST Módulo 8):**
   * Curva da tensão mínima nodal global ($V_{\min}$) confrontada com os limites regulatórios de $0{,}92\text{ pu}$ (Adequada/Precária) e $0{,}87\text{ pu}$ (Precária/Crítica).

---

## 5. Referências Bibliográficas (Padrão ABNT NBR 6023:2018)

* AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL). **Procedimentos de Distribuição de Energia Elétrica no Sistema Elétrico Nacional (PRODIST): Módulo 8 – Qualidade da Energia Elétrica**. Brasília: ANEEL, 2021.
* BASS, F. M. A new product growth for model consumer durables. **Management Science**, v. 15, n. 5, p. 215-227, 1969.
* CLEMENT-NYNS, K.; HAESEN, E.; DRIESEN, J. The impact of charging plug-in hybrid electric vehicles on a residential distribution grid. **IEEE Transactions on Power Systems**, v. 25, n. 1, p. 371-380, 2010.
* MARINHO, C. H. et al. Voltage quality indicators decomposition in distribution systems with high integration of distributed energy resources. **Electric Power Systems Research**, v. 228, p. 109985, 2026.
* NWOBU, E. C.; OBI, P. I.; ODIGBO, C. O. Voltage Deviation Index (VDI) formulation and Maximum-VDI Rule for hosting capacity and EV charging flexibility in distribution networks. **IEEE Access**, v. 14, p. 11204-11218, 2026.
* ROGERS, E. M. **Diffusion of Innovations**. 5. ed. New York: Free Press, 2003.

