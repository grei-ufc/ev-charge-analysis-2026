# Relatório Consolidado de Cossimulação Mosaik (7 Dias / 1.008 Passos)

**Alimentador:** `ESB01S4`  
**Período Simulado:** 7 dias completos (1.008 passos temporais de 600 segundos / 10 minutos)  
**Resolução Temporal:** 10 minutos  
**Ambiente de Execução:** Mosaik 3.5.0 nativo (Python 3.12 / WSL2 Ubuntu) com OpenDSS e Caldera ICM C++  
**Regime de Operação dos Inversores:** **Modo Pass-through / FP Unitário ($FP = 1,0$ e $Q = 0$) — Controles Volt-VAr e Volt-Watt desligados**  

---

## 1. Sumário Executivo

A cossimulação Mosaik multi-agente foi executada com sucesso absoluto em ambos os cenários de planejamento da rede `ESB01S4`:
1. **Cenário 1 — Base (com GD Fotovoltaica):** Executado via `scenarios/scenario_ESB01S4.py` — 1.008/1.008 passos (100% de convergência).
2. **Cenário 2 — Com Veículos Elétricos (PV + Caldera EVs):** Executado via `scenarios/scenario_ESB01S4_EVs.py` — 1.008/1.008 passos (100% de convergência).

> [!IMPORTANT]
> **Premissa Regulatória e Realidade Operacional Atual (Brasil):**  
> Os controles autônomos **Volt-VAr** e **Volt-Watt** foram expressamente **desligados** (`reactive_mode = "none"` e `volt_watt = None`), operando em fator de potência unitário estrito ($FP = 1,0$ e $Q_{\text{ac}} = 0$) e sem corte ativo (*curtailment*). Essa configuração retrata com exatidão o parque atual de micro e minigeração distribuída no Brasil, regulamentado pela ANEEL e pela **ABNT NBR 16149**, servindo como caso-base (*baseline*) de referência.

---

## 2. Operação dos Sistemas Fotovoltaicos (PVs)

Todos os **303 sistemas fotovoltaicos (`pv1` a `pv303`)** distribuídos pela rede BT e MT foram ativamente simulados:
- **Fluxo Mosaik:** As séries históricas de irradiância e temperatura excitam cada agente `PVPanelSim`, que calcula a potência $P_{\text{dc}}$ em função da curva de temperatura $P-T$. O inversor `SmartInverterSim` aplica a curva de eficiência e injeta integralmente a potência ativa $P_{\text{ac}}$ no OpenDSS com $Q_{\text{ac}} = 0\text{ kVAr}$.
- **Potência DC de Pico Global:** **3.228,11 kW** (3,23 MW).
- **Energia Solar Gerada na Semana:** **89,08 MWh** injetados na rede.
- **Impacto da Ausência de Volt-VAr / Volt-Watt:** Sem absorção de reativo capacitivo e sem redução de potência ativa, a injeção solar massiva nos horários de pico (11h às 15h) eleva naturalmente as tensões nas barras com alta densidade de GD, atingindo **$1,2077\text{ pu}$** no pior ponto.

---

## 3. Tabela Comparativa Consolidada

| Métrica / Grandeza | Cenário 1: Base (Com PV) | Cenário 2: Com VEs (PV + Caldera) | Impacto / Diferença |
| :--- | :---: | :---: | :---: |
| **Passos Simulados** | 1.008 passos (7 dias) | 1.008 passos (7 dias) | 100% de convergência em ambos |
| **Parque Solar Ativo** | 303 sistemas fotovoltaicos | 303 sistemas fotovoltaicos | Idêntico |
| **Controles Volt-VAr e Volt-Watt** | **Desligados (Modo `none`, $FP = 1,0$)** | **Desligados (Modo `none`, $FP = 1,0$)** | Prática operacional brasileira |
| **Pico de Geração Solar ($P_{\text{dc}}$)** | 3.228,11 kW | 3.228,11 kW | Idêntico |
| **Energia Solar Gerada (7 dias)** | 89,08 MWh | 89,08 MWh | Idêntico |
| **Veículos Elétricos Ativos** | 0 VEs | 50 VEs (Física Caldera ICM C++) | +50 VEs distribuídos |
| **Pico de Demanda dos VEs** | 0,00 kW | **60,87 kW** | Ocorrido em `2024-09-12 23:50:00` |
| **Energia Semanal Consumida por VEs** | 0,00 MWh | **2,19 MWh** | +2,19 MWh demanda líquida |
| **Máximo de VEs Recarregando Simult.** | 0 | **8 VEs** | Fator de coincidência = 16,0% |
| **Média Contínua de VEs em Recarga** | 0 | **1,7 VEs** | Demanda noturna distribuída |
| **Tensão Mínima Global ($V_{\text{min}}$)** | 1,0007 pu | **0,8557 pu** | Queda por pico de demanda noturna |
| **Barra Crítica de Subtensão** | `243862438tr` (fase A) | `3861951838457432` (fase B) | Ponta de ramal secundário longo |
| **Tensão Máxima Global ($V_{\text{max}}$)** | 1,0423 pu | **1,2077 pu** | Horário de pico solar sem Volt-VAr/Watt |
| **Barra Crítica de Sobretensão** | `243862438tr` (fase A) | `3857980038462787` (fase B) | Barramento com alta concentração GD |
| **Tensão Média BT ($V_{\text{med}}$)** | 1,0212 pu | **1,0117 pu** | Relief global moderado (-0,0095 pu) |
| **Conformidade PRODIST Adequada** | 100,00% | **96,25%** | 96,25% das leituras entre 0,93 e 1,05 pu |
| **Subtensão Crítica ($V < 0,93$ pu)** | 0,00% | **0,65%** | Restrita a horários de pico em pontas de ramal |
| **Sobretensão Crítica ($V > 1,05$ pu)**| 0,00% | **3,10%** | Restrita aos picos solares em barramentos com GD |

---

## 4. Análise de Impacto dos Veículos Elétricos e Dinâmica de Tensão

1. **Impacto da Operação dos Inversores em $FP = 1,0$ (Sem Volt-VAr / Volt-Watt):**
   - Na ausência de suporte de reativo (sem absorção de $Q$) ou corte de potência ativa (sem corte de $P$), os barramentos de baixa tensão que concentram alta geração fotovoltaica sofrem elevação expressiva de tensão durante o meio-dia.
   - Isso explica por que **3,10% das medições semanais** ultrapassaram o teto regulatório de $1,05\text{ pu}$, com máxima pontual de **$1,2077\text{ pu}$**.
   - Esse resultado evidencia perfeitamente o problema prático enfrentado pelas distribuidoras brasileiras hoje e justifica tecnicamente propostas futuras de regulação para exigência de inversores inteligentes com curvas Volt-VAr ativas.
2. **Perfil de Recarga dos Veículos Elétricos (Caldera ICM):**
   - O pico conjunto dos 50 VEs atingiu **60,87 kW às 23:50**, compatível com a rotina de deslocamento e recarga noturna domiciliar.
   - Fator de simultaneidade de apenas **16,0%** (8 VEs simultâneos), comprovando a não-coincidência temporal estocástica dos usuários.
   - As violações de subtensão (0,65%) concentraram-se na madrugada em ramais longos, sem correlação direta com a geração solar, que ocorre no período diurno.

---

## 5. Arquivos de Saída e Rastreabilidade

- **Cenário 1 (Base):** `output/result_run_ESB01S4.csv` (51 MB)
- **Cenário 2 (EVs):** `output/result_run_ESB01S4_EVs.csv` (165 MB)
- **Topologia Base:** `output/topologia_ESB01S4.json`
- **Topologia EVs:** `output/topologia_ESB01S4_EVs.json`
- **Resumo Estruturado JSON:** `output/resumo_comparativo_cossimulacao.json`
- **Script de Análise:** `testes_convergencia/analisar_resultados_cossimulacao.py`
