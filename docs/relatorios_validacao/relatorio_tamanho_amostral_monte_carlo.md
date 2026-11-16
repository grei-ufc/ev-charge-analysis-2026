# Relatório de Dimensionamento Amostral de Monte Carlo (Law, 2015 / Chow & Robbins, 1965)

- **Cenário Avaliado:** 50.0% de Penetração de VEs (Cenário de Estresse Máximo)
- **Número Total de Sementes Executadas ($n$):** 10 replicações independentes
- **Sementes Executadas:** `[8, 25, 2026, 42, 100, 777, 1234, 5555, 9999, 12345]`
- **Nível de Confiança Adotado:** 95% ($\alpha = 0,05$, quantil bilateral final $t_{0,025; 9} = 2.262$)
- **Erro Relativo Máximo Admissível Adotado:** $\epsilon = 1,0\%$ ($0,01$) — critério primário de precisão estocástica
- **Critério de Decisão:** **Abordagem A (Variável Governante: Tensão Mínima Global $V_{\min}$)** — respaldada pelo PRODIST Módulo 8 (ANEEL, 2021) e literatura clássica (LAW, 2015; CHOW & ROBBINS, 1965)

## 1. Evolução Passo a Passo do Procedimento Sequencial de Parada (Law, 2015 / Chow & Robbins, 1965)

Avaliando a **Tensão Mínima Global ($V_{\min}$)** como Variável Governante (Abordagem A) sob tolerância $\epsilon = 1,0\%$ e 95% de confiança:

| Passo ($k$) | Semente | $V_{\min}$ Indiv. | $\bar{V}_{\min}$ Acum. | Desvio ($s$) | $\widehat{CV}$ (%) | $t_{0,025; k-1}$ | Erro Obs. (%) | $M^*(k)$ Req. | Condição de Parada ($k \ge M^*$)? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2 | `25` | 0.7608 pu | 0.7625 pu | 0.00238 | 0.31% | 12.706 | ±2.81% | **16** | ❌ Prosseguir |
| 3 | `2026` | 0.7721 pu | 0.7657 pu | 0.00579 | 0.76% | 4.303 | ±1.88% | **11** | ❌ Prosseguir |
| 4 | `42` | 0.7371 pu | 0.7585 pu | 0.01503 | 1.98% | 3.182 | ±3.15% | **40** | ❌ Prosseguir |
| 5 | `100` | 0.7526 pu | 0.7574 pu | 0.01328 | 1.75% | 2.776 | ±2.18% | **24** | ❌ Prosseguir |
| 6 | `777` | 0.7799 pu | 0.7611 pu | 0.01502 | 1.97% | 2.571 | ±2.07% | **26** | ❌ Prosseguir |
| 7 | `1234` | 0.7297 pu | 0.7566 pu | 0.01813 | 2.40% | 2.447 | ±2.22% | **35** | ❌ Prosseguir |
| 8 | `5555` | 0.7564 pu | 0.7566 pu | 0.01678 | 2.22% | 2.365 | ±1.85% | **28** | ❌ Prosseguir |
| 9 | `9999` | 0.7915 pu | 0.7605 pu | 0.01955 | 2.57% | 2.306 | ±1.98% | **36** | ❌ Prosseguir |
| 10 | `12345` | 0.7731 pu | 0.7617 pu | 0.01885 | 2.47% | 2.262 | ±1.77% | **32** | ❌ Prosseguir |

> **Observação Metodológica sobre a Dinâmica Sequencial:**
> Conforme demonstrado por Chow e Robbins (1965) e Law (2015), o aumento do número de replicações $k$ expande os graus de liberdade $\nu = k - 1$, reduzindo o quantil $t$ de Student de forma acentuada. Entretanto, com $\widehat{CV} = 2,47\%$ nas 10 sementes executadas, o erro relativo observado ($\pm 1,77\%$) permaneceu acima da tolerância primária de $\epsilon = 1,0\%$ (que requer $M^* = 32$).

---

## 2. Tabela Síntese das Métricas Eletrotécnicas Avaliadas no Conjunto Final

| Métrica Eletrotécnica | Média ($\bar{X}$) | Desvio ($s$) | Coef. Variação ($\widehat{CV}$) | Erro Obs. (95% IC) | $M^*$ ($\epsilon = 1.0%$) | $M^*$ ($\epsilon = 2.0%$) | $M^*$ ($\epsilon = 5.0%$) | Suficiente? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **v_min_global** | 0.7617 pu | 0.01885 | 2.475% | ±1.771% | **32** | **8** | **2** | ⚠️ Requer complemento |
| **v_med_global** | 1.0050 pu | 0.00024 | 0.024% | ±0.017% | **1** | **1** | **1** | ✅ Suficiente |
| **v_afetada_min** | 0.7711 pu | 0.01796 | 2.329% | ±1.666% | **28** | **7** | **2** | ⚠️ Requer complemento |
| **v_afetada_med** | 0.9389 pu | 0.00544 | 0.579% | ±0.414% | **2** | **1** | **1** | ✅ Suficiente |
| **energia_ves_kwh** | 15757.2 | 592.38 | 3.759% | ±2.689% | **73** | **19** | **3** | ⚠️ Requer complemento |
| **p_max_kw** | 1823.5 | 21.45 | 1.176% | ±0.842% | **8** | **2** | **1** | ✅ Suficiente |
| **vdi_sub_acum** | 3336.6 | 152.56 | 4.572% | ±3.271% | **107** | **27** | **5** | ⚠️ Requer complemento |
| **n_barras_violam_drc_sub** | 375.9 | 76.57 | 20.370% | ±14.572% | **2124** | **531** | **85** | ⚠️ Requer complemento |
| **CRITÉRIO GOVERNANTE (Abordagem A: $V_{\min}$)** | — | — | — | — | **32** | **8** | **2** | ⚠️ Requer complemento |

---

## 3. Minuta Textual para Inserção no Capítulo de Metodologia e Resultados do TCC

> **Validação Estatística e Procedimento Sequencial de Amostragem (Law, 2015; Chow & Robbins, 1965)**
>
> Para assegurar a validade estatística das conclusões e comprovar a suficiência do número de replicações estocásticas sem incorrer em esforço computacional redundante, adotou-se o **Procedimento Sequencial de Parada** com erro relativo especificado, formalizado por Chow e Robbins (1965) e consagrado por Law (2007, 2015) para simulações estocásticas de Monte Carlo.
>
> Em sistemas de distribuição de energia elétrica com múltiplas saídas, adota-se a **Abordagem A (Variável Governante)** recomendada por Law (2015) e Banks et al. (2010), elegendo a **Tensão Mínima Global ($V_{\min}$)** como grandeza primária de projeto. Do ponto de vista físico e regulatório (PRODIST Módulo 8 / ANEEL, 2021), a conformidade do alimentador, as violações críticas e a determinação da Capacidade de Hospedagem (*Hosting Capacity*) são estritamente governadas pelo ponto de maior afundamento de tensão do circuito. Como qualquer barra $i$ opera com tensão superior ou igual ao mínimo global ($V_i(t) \ge V_{\min}(t)$ para todo $i$ e $t$), controlar o erro amostral sobre a variável governante garante a blindagem estatística de toda a rede.
>
> No procedimento sequencial, simulações quase-estáticas (QSTS em passos de 10 minutos ao longo de 168 horas) foram executadas iterativamente para uma sequência de sementes pseudoaleatórias independentes (`[8, 25, 2026, 42, 100, 777, 1234, 5555, 9999, 12345]`). A cada passo $k$ ($k \ge 2$), recalcularam-se a média $\bar{V}_{\min}(k)$, o desvio padrão $s_k$, o coeficiente de variação $\widehat{CV}_k$ e os graus de liberdade $\nu_k = k - 1$, atualizando o quantil $t_{\alpha/2, \nu_k}$ e avaliando a condição analítica de parada:
>
> $$k \ge M^*(k) = \left\lceil \left( \frac{t_{\alpha/2, k-1} \cdot \widehat{CV}_{V_{\min}}}{\epsilon} \right)^2 \right\rceil \quad \iff \quad \frac{t_{\alpha/2, k-1} \cdot s_k}{\bar{V}_{\min}(k) \sqrt{k}} \le \epsilon$$
>
> Para 95% de confiança estatística ($\alpha = 0,05$) e tolerância primária de $\epsilon = 1,0\%$ ($0,01$), o lote de **$M = 10$ replicações** obteve $\bar{V}_{\min} = 0,7617\text{ pu}$, $s = 0,01885\text{ pu}$, $\widehat{CV} = 2,475\%$, $t_{0,025; 9} = 2,262$ e erro relativo observado de $\pm 1,77\%$, não atingindo o alvo primário de 1,0% (que requereria $M^* = 32$ replicações). Por outro lado, para $\epsilon = 2,0%$ ($M^* = 8 \le 10$) e $\epsilon = 5,0%$ ($M^* = 2 \le 10$), a suficiência amostral foi plenamente atingida dentro do lote executado. Para o mesmo alvo $\epsilon = 1,0\%$, as grandezas agregadas apresentaram tamanhos requeridos de $M^* = 1$ para tensão média nodal, $M^* = 8$ para demanda de pico no tronco e $M^* = 73$ para energia total de recarga dos VEs.
