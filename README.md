# TCC: Análise dos Impactos do Aumento da Penetração de Carregadores de Veículos Elétricos na Rede de Distribuição de Baixa Tensão Brasileira via Co-simulação

**👨‍💻 Autor:** Paulo Victor Pereira Lima  
*Estudante de Engenharia Elétrica na Universidade Federal do Ceará (UFC) e pesquisador do **GREI** (Grupo de Redes Elétricas Inteligentes).*  
**Orientação:** Departamento de Engenharia Elétrica – Centro de Tecnologia (CT/UFC).

---

## 📌 Visão Geral do Projeto

Plataforma avançada de co-simulação para avaliação de impacto técnico e regulatório da integração em larga escala de **Veículos Elétricos (VEs)** e **Geração Distribuída Fotovoltaica (GD-FV)** em redes reais de distribuição de energia elétrica de Baixa Tensão (BT).

A infraestrutura orquestra o framework de co-simulação assíncrona **[Mosaik (API v3)](https://mosaik.offis.de/)**, o motor de cálculo de fluxo de potência quase-estático (*Quasi-Static Time Series* - QSTS) **[OpenDSS](https://www.epri.com/pages/sa/opendss)** e a modelagem eletroquímica de alta fidelidade de baterias e recarga **Caldera ICM**, expandindo e especializando a arquitetura modular do projeto **tsre-der-opentes** (GREI-UFC, 2024).

---

## 🎯 Objetivo e Escopo da Pesquisa

O Trabalho de Conclusão de Curso investiga os limites físicos e normativos de operação da rede frente à difusão de VEs residenciais (recarga não coordenada em 220 V), avaliando uma **grade paramétrica contínua de 0% a 50% de penetração** (em passos discretos de 5%) sobre os **947 domicílios de baixa tensão** do alimentador.

### Dimensões de Análise e Métricas Eletrotécnicas:
1. **Conformidade Regulatória ANEEL (PRODIST Módulo 8):** Apuração dos indicadores semanais de Duração Relativa da Transgressão de Tensão Precária ($\text{DRP} \le 3{,}0\%$) e Crítica ($\text{DRC} \le 0{,}5\%$) em janelas de 168 horas (1.008 passos de 10 min).
2. **Desagregação Vetorial de Tensão (MARINHO et al., 2026):** Separação algébrica entre transgressões por sobretensão solar diurna ($\text{DRP}_{\text{sob}}$, $\text{DRC}_{\text{sob}}$) e afundamentos por subtensão veicular noturna ($\text{DRP}_{\text{sub}}$, $\text{DRC}_{\text{sub}}$).
3. **Índice de Desvio de Tensão (NWOBU; OBI; ODIGBO, 2026):** Severidade física contínua nodal e agregada via $\text{VDI}_{\text{RMS}}$ e identificação das barras mais frágeis da rede pela **Regra do VDI Máximo (*Maximum-VDI Rule*)**.
4. **Análise Comparativa Diferencial e Relativa ao Caso Base:** Isolamento absoluto da causalidade veicular ($\Delta P_{\max}$, $\% \Delta P_{\max}$, $\% \Delta E$, $\Delta V_{\min}$, $\% \Delta \text{VDI}_{\text{sub}}$ e novas barras transgressoras $\Delta N_{\text{barras}}$).
5. **Capacidade de Hospedagem (*Hosting Capacity*):** Determinação matemática do limiar de saturação do alimentador para recarga desordenada de veículos elétricos.
6. **Desbalanceamento de Tensão e Fator de Potência:** Monitoramento do indicador estatístico $FD_{95\%} \le 2{,}0\%$ e faixas operacionais de $\text{FP}$ na linha tronco segundo a Resolução Normativa ANEEL nº 1.000/2021.

---

## 🌐 O Circuito Real em Estudo: Alimentador ESB01S4

Diferente de abordagens tradicionais baseadas em redes sintéticas ou sistemas-teste simplificados do IEEE, este estudo utiliza um circuito de distribuição real brasileiro:

* **Subestação de Origem:** SE Eusébio (ESB), operada pela concessionária local na Região Metropolitana de Fortaleza (Ceará).
* **Alimentador:** **ESB01S4** em Média Tensão (13,8 kV) e redes secundárias de Baixa Tensão (380/220 V).
* **Origem dos Dados:** Extraído da Base de Dados Geográfica da Distribuidora (BDGD) da ANEEL e convertido para formato nativo do OpenDSS através do conversor de código aberto [`bdgd2opendss`](https://github.com/PauloRadatz/bdgd2opendss) (RADATZ, 2023).
* **Escala do Circuito:**
  * **2.210 barras de Baixa Tensão** monitoradas por fase;
  * **1.914 cargas secundárias** agregadas em **947 Unidades Consumidoras (domicílios)** residenciais;
  * **303 sistemas de microgeração fotovoltaica (PVs)** ativos, totalizando mais de **3,16 MWp** de geração distribuída integrada;
  * **Linha Tronco Principal (`smt_1071706`):** Maior fluxo de entrada do alimentador, com demanda máxima de **$1.393,5\text{ kW}$** e **$130.345,8\text{ kWh}$** semanais.

---

## 🔬 Metodologia: Lógica de Adoção Incremental Aninhada (*Nested Adoption*)

Para assegurar consistência física e eliminar artefatos estatísticos de reamostragem entre os cenários, a alocação dos VEs foi modelada segundo a **Teoria da Difusão de Inovações de Rogers (2003)** e o **Modelo de Crescimento de Bass (1969)**:

* **Fila Universal de Adoção Determinística ($\mathcal{F}_{\text{adoção}}$):** Os 947 domicílios foram ordenados canonicamente e receberam previamente, de forma definitiva, sua fase de conexão monofásica (220 V) e seu perfil de recarga Caldera ICM ($3,6\text{ kW}$ ou $7,2\text{ kW}$).
* **Relação de Contenção Estrita:**
  $$\mathcal{V}(5\%) \subset \mathcal{V}(10\%) \subset \mathcal{V}(15\%) \subset \dots \subset \mathcal{V}(50\%)$$
  Cada cenário superior mantém **100% dos veículos e conexões dos cenários anteriores**, apenas acrescentando novos consumidores na rede.
* **Garantia Eletrotécnica:** Assegura monotonicidade estrita nas curvas de demanda acumulada ($\sum E_{\text{VE}}$) e afundamento nodal de tensão ($V_{\min}$), eliminando anomalias causadas por troca aleatória de vizinhança.

> 📄 **Documento Completo da Metodologia:** [`docs/metodologia_alocacao_incremental_aninhada.md`](docs/metodologia_alocacao_incremental_aninhada.md)

---

## 📊 Síntese dos Resultados e Limiares de Hosting Capacity

Simulação semanal (1.008 passos de 10 min) executada sobre toda a grade paramétrica:

| Cenário | Qtd VEs | Tensão Mínima $V_{\min}$ | Classificação PRODIST | Novas Barras $\Delta N_{\text{DRC\_sub}}$ | Distúrbio $\% \Delta \text{VDI}_{\text{sub}}$ | Energia VEs |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Caso Base** | 0 | **0,9721 pu** | **Adequada** | 0 | 0,0% | 0 kWh |
| **5% VEs** | 47 | **0,9059 pu** | Precária | 0 | $+645,9\%$ | 2.455 kWh |
| **10% VEs** | 95 | **0,8758 pu** | Precária (limiar) | 0 | $+1.548,4\%$ | 4.594 kWh |
| **15% VEs** | 142 | **0,8655 pu** | **Crítica** ($<0,87$) | 0 | $+2.260,3\%$ | 6.482 kWh |
| **20% VEs** | 189 | **0,8646 pu** | Crítica | 0 | $+3.055,9\%$ | 8.863 kWh |
| **25% VEs** | 237 | **0,8311 pu** | Crítica | 0 | $+4.293,6\%$ | 10.821 kWh |
| **30% VEs** | 284 | **0,8332 pu** | **Crítica Regulada** | **+22 barras** | $+6.134,8\%$ | 12.741 kWh |
| **35% VEs** | 331 | **0,8042 pu** | Crítica Severa | **+95 barras** | $+8.356,3\%$ | 15.279 kWh |
| **40% VEs** | 379 | **0,8013 pu** | Crítica Severa | **+125 barras** | $+9.268,4\%$ | 17.395 kWh |
| **45% VEs** | 426 | **0,7963 pu** | Crítica Severa | **+164 barras** | $+11.014,1\%$ | 19.233 kWh |
| **50% VEs** | 474 | **0,7857 pu** | **Pior Caso (-18,6%)** | **+215 barras** | **$+13.758,7\%$** | 21.410 kWh |

### Principais Conclusões Eletrotécnicas:
1. **O Efeito Preenchimento de Vale (*Valley Filling*):** O pico máximo do alimentador na subestação ($1.393,5\text{ kW}$) ocorre durante o horário comercial diurno (14h–16h). Como a recarga residencial ocorre predominantemente entre 19h e 03h (no vale noturno da curva de carga), a demanda agregada dos VEs preenche o vale sem criar um novo pico diurno superior na linha tronco.
2. **Gargalo Exclusivo na Baixa Tensão:** Enquanto a subestação e a linha tronco operam com folga térmica, **os ramais secundários de BT colapsam**: a tensão despenca para $0,785\text{ pu}$ e mais de 215 barras entram em violação crítica permanente de DRC no cenário de 50%.
3. **Limiar de Hosting Capacity:** Fica delimitado entre **15%** (rompimento do patamar absoluto de $0,87\text{ pu}$) e **30%** (rompimento do tempo limite regulatório de 0,5% do PRODIST Módulo 8).

---

## 📁 Estrutura de Diretórios do Repositório

```text
ev-analysis-2026/
├── pyproject.toml             # Gerenciamento de dependências via uv
├── REFERENCIAS.md             # Catálogo mestre de referências bibliográficas (ABNT NBR 6023/10520)
├── scenarios/                 # Scripts executáveis de simulação
│   ├── executar_grade_cenarios.py # Orquestrador em lote da grade (5% a 50%)
│   ├── scenario_ESB01S4_TCC.py    # Cenário principal integrado no Mosaik
│   ├── scenario_ESB01S4.py        # Cenário base (0 VEs)
│   └── scenario_ESB01S4_EVs.py    # Cenário com VEs isolado
├── src/                       # Códigos-fonte e módulos de apoio
│   ├── simulators/util/
│   │   ├── ev_creator.py          # Gerador da alocação incremental aninhada (Rogers/Bass)
│   │   ├── analisador_grade_tcc.py# Analisador diferencial relativo e gráficos 300 DPI
│   │   └── topologia.py           # Extrator de grafos da rede do OpenDSS
│   └── ajuste-dados/          # Tratamento de datasets solares e perfis Caldera
├── data/rede/ESB01S4/         # Modelos OpenDSS nativos do alimentador real
│   ├── run_ESB01S4.dss        # Master script do circuito
│   └── ESB01S4_evs.dss        # Arquivo compilado dos VEs alocados
├── notebooks/                 # Ambiente analítico Jupyter
│   └── analise_tcc_principal.ipynb # Notebook executivo com Módulo 9.1 integrado
├── output/                    # Resultados gerados
│   ├── figuras_comparativas/  # Figuras acadêmicas em 300 DPI (Figuras 1 a 4)
│   ├── tabela_comparativa_relativa_tcc.csv # Tabela resumo CSV
│   └── tabela_comparativa_relativa_tcc.json# Tabela resumo JSON estruturada
└── docs/                      # Documentação técnica e metodológica
    ├── metodologia_alocacao_incremental_aninhada.md
    ├── metodologia_analise_comparativa_relativa.md
    ├── fundamentacao_cenarios_penetracao_ve.md
    └── modelagem_veiculos_eletricos.md
```

---

## 🚀 Como Executar o Projeto

O projeto utiliza o gerenciador de pacotes ultrarrápido **[`uv`](https://docs.astral.sh/uv/)** para garantir reprodutibilidade estrita do ambiente virtual Python.

### 1. Clonagem e Instalação de Dependências

```bash
# Clone o repositório
git clone https://github.com/pvictorl/ev-analysis-2026.git
cd ev-analysis-2026

# Sincronize o ambiente virtual e instale todas as dependências
uv sync
```

### 2. Execução da Grade Paramétrica de Simulações (0% a 50%)

Para executar sequencialmente todos os cenários da pesquisa (com a nova lógica aninhada e substituição automática):

```bash
# Executa todos os 10 cenários (5% a 50%) garantindo alocação aninhada:
uv run python scenarios/executar_grade_cenarios.py --forcar

# Para executar apenas cenários específicos (ex: 5%, 15%, 30% e 50%):
uv run python scenarios/executar_grade_cenarios.py --cenarios 5 15 30 50 --forcar
```

### 3. Pós-Processamento, Figuras Acadêmicas e Tabelas Relativas

Após a conclusão das simulações, processe os resultados com o analisador diferencial:

```bash
uv run python src/simulators/util/analisador_grade_tcc.py
```

* **Figuras Geradas:** Salvas automaticamente em `output/figuras_comparativas/` a 300 DPI:
  * `fig1_impacto_relativo_pico_energia.png` (Sensibilidade da Demanda e Energia);
  * `fig2_hosting_capacity_novas_barras_prodist.png` (Limiar de *Hosting Capacity* e transgressões ANEEL);
  * `fig3_vdi_subtensao_relativo.png` (Agravamento do VDI de Subtensão - Nwobu et al., 2026);
  * `fig4_tensao_minima_global_prodist.png` (Afundamento da Tensão Mínima Global $V_{\min}$).
* **Tabelas Consolidadas:** Salvas em `output/tabela_comparativa_relativa_tcc.csv` e `.json`.

### 4. Visualização Interativa no Jupyter Notebook

Abra o notebook principal para inspeção visual interativa e replicação de gráficos:

```bash
uv run jupyter lab notebooks/analise_tcc_principal.ipynb
```

---

## 📚 Documentação Técnica e Referências Normativas

* **Metodologia de Alocação Incremental Aninhada:** [`docs/metodologia_alocacao_incremental_aninhada.md`](docs/metodologia_alocacao_incremental_aninhada.md)
* **Metodologia de Análise Comparativa Diferencial:** [`docs/metodologia_analise_comparativa_relativa.md`](docs/metodologia_analise_comparativa_relativa.md)
* **Catálogo Geral de Referências Bibliográficas (ABNT NBR 6023/10520):** [`REFERENCIAS.md`](REFERENCIAS.md)

---

## ⚖️ Licença

Este repositório é parte de um Trabalho de Conclusão de Curso desenvolvido na Universidade Federal do Ceará (UFC). O código é distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais informações.

## ⚖️ Licença

Este repositório é parte de um Trabalho de Conclusão de Curso desenvolvido na Universidade Federal do Ceará (UFC). O código é distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais informações.

