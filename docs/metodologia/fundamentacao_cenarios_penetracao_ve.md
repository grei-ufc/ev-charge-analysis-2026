# Fundamentação dos Cenários de Penetração de Veículos Elétricos e Revisão Bibliográfica

Este documento consolida a fundamentação técnica, regulatória e bibliográfica utilizada para definir as taxas de penetração de Veículos Elétricos (VEs) no alimentador de distribuição real **ESB01S4** (Neoenergia Cosern). Ele estabelece a justificativa científica do estudo, mapeia a literatura nacional e internacional e detalha como este Trabalho de Conclusão de Curso (TCC) preenche uma lacuna acadêmica identificada em pesquisas recentes do setor elétrico brasileiro.

---

## 1. A Lacuna Científica: Da Infraestrutura Rodoviária à Rede Residencial em Baixa Tensão

### 1.1. O Estado da Arte no Brasil (Lopes Júnior, Sousa & Melo — UFABC / IEEE Access, 2024)
Recentemente, a tese de doutorado de José Calixto Lopes Júnior intitulada *"Estimativa de demanda para infraestrutura de carregamento de veículos elétricos"* (UFABC, 2024; Orientador: Prof. Dr. Thales Sousa) e o artigo científico derivado publicado no periódico internacional *IEEE Access* (v. 12, pp. 113215–113234, 2024) apresentaram o método **MEDIC** (*Model for Electric vehicle Demand in Infrastructure of Charging*) e o modelo **X-Modeci**. 

Essa pesquisa de ponta foi desenvolvida no âmbito do **Projeto de P&D Estratégico ANEEL da Neoenergia (Projeto Corredor Verde)**, com aplicação prática focada no Nordeste brasileiro (Salvador/BA e rodovias intermunicipais associadas). O foco central do MEDIC foi dimensionar a demanda de recarga rápida e semipública em locais como shoppings, postos rodoviários e eletropostos urbanos de alta potência.

### 1.2. A Lacuna Formalmente Apontada na Literatura (Pág. 87 da Tese)
Nas conclusões e direcionamentos para trabalhos futuros, **Lopes Júnior (2024, Seção 5.3, p. 87)** ressalta de forma explícita e categórica:

> *Como proposta de trabalho futuro, destaca-se a urgente necessidade de investigar o impacto da recarga residencial desordenada nas redes secundárias de distribuição em baixa tensão (BT), onde os transformadores de distribuição e os ramais de atendimento são fisicamente mais vulneráveis a sobrecargas térmicas, desbalanços de fase e afundamentos de tensão.*

Embora a infraestrutura de recarga rápida pública chame grande atenção midiática, ela responde por menos de 15% a 20% das sessões totais de recarga. A literatura internacional e os dados da indústria convergem ao apontar que **entre 80% e 85% de toda a energia elétrica demandada por veículos elétricos leves é consumida na própria residência dos usuários**, conectando-se diretamente às redes secundárias de Baixa Tensão (BT).

### 1.3. O Papel e Contribuição deste TCC
Este trabalho preenche de forma direta, quantitativa e pioneira a lacuna apontada por Lopes Júnior e pelo grupo de pesquisa da UFABC/Neoenergia:

1. **Topologia Real e Georreferenciada:** Em vez de redes genéricas sintéticas (como IEEE 13, 34 ou 123 barras), o estudo é executado sobre a malha física real do alimentador **ESB01S4** da Neoenergia Cosern, composto por 1.914 domicílios residenciais distribuídos em 445 barras de Baixa Tensão (BT) e seus respectivos transformadores de distribuição MT/BT.
2. **Modelagem Eletroquímica Realista (Caldera ICM):** Supera a modelagem simplificada de injeção de potência retangular (degrau), acoplando o motor termodinâmico/eletroquímico Caldera ICM (*Idaho National Laboratory*). O modelo reproduz as fases de Corrente Constante e Tensão Constante (*CC-CV*) com a curva de amortecimento (*tapering* de potência) em baterias de íons de lítio.
3. **Co-simulação Dinâmica em Alta Resolução:** Integração via Mosaik em escala de minuto (10.080 passos semanais), permitindo capturar o pico coincidente entre o surto de conexão veicular vespertino/noturno (18h30–20h00) e a curva de carga residencial típica do alimentador.
4. **Conformidade Regulatória PRODIST:** Avaliação sistemática dos indicadores normativos do Módulo 8 da ANEEL ($DRP$, $DRC$, $FD_{95\%}$, $VDI$) e de estresse em transformadores secundários para diferentes taxas de penetração.

---

## 2. Embasamento Teórico das Taxas de Penetração de VEs

A definição das taxas de penetração a serem simuladas não deve ser arbitrária. Ela foi estruturada a partir da convergência entre quatro fontes de referência:

```
                            ┌─────────────────────────────────────────┐
                            │    3º Anuário PNME (2023) / BNEF        │
                            │   Ponto de Inflexão (5%) / 2030 (20%)   │
                            └───────────────────┬─────────────────────┘
                                                │
       ┌────────────────────────────────────────┼────────────────────────────────────────┐
       │                                        │                                        │
┌──────▼──────────────────────────┐  ┌──────────▼──────────────────────────┐  ┌──────────▼──────────────────────────┐
│ Lopes Júnior et al. (UFABC 2024)│  │   Rahman et al. (RSER, 2022)        │  │      EPE / PNE 2050 (MME)           │
│  Cenários BR: 7%, 30% e 65%     │  │  Estresse BT: Baixa/Média/Alta     │  │ Projeção Decenal: 15% a 20%         │
└─────────────────────────────────┘  └─────────────────────────────────────┘  └─────────────────────────────────────┘
```

### 2.1. 3º Anuário Brasileiro de Mobilidade Elétrica (PNME, 2023)
O relatório anual da Plataforma Nacional de Mobilidade Elétrica (PNME, dez/2023) traz métricas essenciais para o planejamento setorial:
* **O Ponto de Inflexão (*Tipping Point*) em 5%:** O Anuário baseia-se na teoria de difusão tecnológica da *BloombergNEF (BNEF)*, que demonstra empiricamente em mercados globais que, ao cruzar o patamar de **5% de participação nas vendas de veículos novos**, a curva de adoção deixa de pertencer a nichos (*early adopters*) e passa a apresentar comportamento exponencial de massa. No Brasil, o emplacamento de leves eletrificados atingiu 4,75% em agosto de 2023 e consolidou-se acima de 5% a partir de 2024.
* **Projeção de Médio Prazo (2030):** O Anuário reporta os planos estratégicos da indústria automobilística nacional (ex: grupo Stellantis / Anfavea), que projetam que os veículos plug-in (BEVs + PHEVs) responderão por aproximadamente **20% das vendas totais no Brasil até 2030**.
* **Infraestrutura Residencial como Eixo Central:** Destaca que, apesar dos investimentos em corredores públicos de carregamento rápido (DC), a conveniência tarifária e a rotina urbana consolidam as residências em BT como o principal ponto de recarga do país.

### 2.2. Tese de Doutorado e Artigo IEEE Access (Lopes Júnior et al., 2024)
Para a calibração de modelos no contexto regional do Nordeste brasileiro, os autores estabeleceram três cenários canônicos de penetração da frota eletrificada:
* **Cenário 1 (Curto Prazo / Ponto de Partida):** **7%** — reflete a transição imediata pós-inflexão de mercado.
* **Cenário 2 (Médio Prazo / Transição Consolidada):** **30%** — captura o avanço da frota em direção à meta de descarbonização da década de 2030.
* **Cenário 3 (Longo Prazo / Alta Eletrificação):** **65%** — cenário de saturação tecnológica em direção aos horizontes de 2045–2050.

### 2.3. Rahman et al. (Renewable and Sustainable Energy Reviews, 2022)
O artigo seminal *"Impacts of large-scale EV charging on LV distribution networks: A comprehensive review and case study"* analisou o comportamento de dezenas de redes secundárias BT e categorizou o impacto conforme a penetração:
* **Baixa Penetração (5% a 10%):** O sistema de distribuição opera em regime seguro. Flutuações de tensão são pequenas e restritas às residências posicionadas na ponta final (*tail-end*) dos circuitos BT.
* **Média Penetração (20% a 30%):** Início da formação de novos picos de demanda durante a noite. Os transformadores de distribuição passam a operar próximos da capacidade nominal ($S \approx S_{nom}$) e surgem as primeiras violações de tensão precária conforme normas regulatórias. Rahman et al. adotam **25%** como caso-base de estudo.
* **Alta Penetração (50% a 100%):** Sobrecargas térmicas críticas nos transformadores MT/BT (atingindo 120% a 150% do limite nominal), aceleração drástica da degradação de isolamento térmico e necessidade iminente de reforço de condutores e transformadores se não houver carregamento inteligente (*smart charging*).

### 2.4. Plano Nacional de Energia — PNE 2050 (EPE / MME)
A Empresa de Pesquisa Energética (EPE), em seus estudos oficiais para o PNE 2050 e cadernos de eletromobilidade, projeta:
* **Cenário de Referência:** Eletrificação de **15% a 20%** da frota leve nacional na década de 2030.
* **Cenário de Descarbonização Acelerada:** Participação de **40% a 50%** de veículos elétricos na matriz de transporte até 2050.

---

## 3. Matriz Definitiva de Cenários de Penetração: Grade Paramétrica (0% a 50% em Passos de 5%)

Para atingir rigor metodológico comparável a pesquisas internacionais de ponta e obter uma determinação precisa da **Capacidade de Hospedagem (*Hosting Capacity*)** do alimentador real **ESB01S4**, adotou-se uma grade paramétrica contínua com **11 cenários** (do Caso Base de 0% até a Saturação de 50%, com passos de 5%).

> [!NOTE]
> **Base de Cálculo Residencial BT:** No modelo OpenDSS da rede real, existem 1.914 elementos de carga BT modelados em pares (`_M1` e `_M2`), que correspondem exatamente a **947 Unidades Consumidoras (domicílios residenciais únicos)** distribuídos em 703 barras secundárias BT. A alocação estocástica vincula no máximo 1 VE por domicílio único (`base_calculo="residencial_bt"`).

### 3.1. Justificativa Técnica da Grade de 5% em 5%
1. **Determinação Exata do Ponto Crítico de Hosting Capacity:** Saltos esparsos (ex: 5% $\rightarrow$ 30%) apenas indicam que violações regulatórias do PRODIST ($DRP > 3\%$, $DRC > 0,5\%$, $V < 0,90\text{ pu}$ ou sobrecarga de transformadores) ocorreram em algum momento desse intervalo. A resolução de 5% permite diagnosticar com exatidão o percentual máximo seguro antes de exigir obras de reforço da concessionária.
2. **Curvas Contínuas de Sensibilidade:** Com 11 pontos, é possível traçar curvas empíricas de alta resolução para:
   * **Perdas Técnicas Totais (kWh):** Análise do crescimento quadrático ($I^2 R$) das perdas de energia na malha secundária.
   * **Pico Coincidente de Demanda (kW e kVA):** Quantificação do impacto da sobreposição do surto veicular vespertino/noturno (18h30–20h30) com a ponta residencial existente.
   * **Indicadores Regulatórios PRODIST ($DRP$ e $DRC$):** Percentual de tempo em regime precário e crítico por barra secundária.
   * **Índice de Desvio de Tensão ($VDI$):** Evolução contínua da severidade das quedas de tensão ao longo dos ramais BT.
3. **Custo Computacional vs. Riqueza de Dados:** Com a otimização em C do OpenDSS e a compilação C++ do Caldera ICM, cada simulação semanal (1.008 passos de 10 minutos) consome aproximadamente 3 minutos. A execução completa de toda a grade paramétrica é concluída de forma automática e estável, gerando um banco de dados completo para o TCC.

### 3.2. Tabela de Cenários e Marcos Teóricos

| Cenário | Penetração (%) | Qtd. Veículos Elétricos | Nomenclatura do Arquivo de Saída | Marco Teórico e Documento de Referência em `Fontes/` |
| :---: | :---: | :---: | :--- | :--- |
| **C0** | **0%** | **0 VEs** | `result_TCC_baseline.csv` | **Caso Base Real:** Operação atual da Neoenergia Cosern sem VEs. |
| **C1** | **5%** | **47 VEs** | `result_TCC_ev_p5_residencial_bt.csv` | **Ponto de Inflexão (*Tipping Point*):** BloombergNEF (2021) e 3º Anuário PNME (2023). |
| **C2** | **10%** | **95 VEs** | `result_TCC_ev_p10_residencial_bt.csv` | **Limite Superior de Baixa Penetração:** Rahman et al. (2022) e Clement-Nyns (2010). |
| **C3** | **15%** | **142 VEs** | `result_TCC_ev_p15_residencial_bt.csv` | **Projeção Decenal Oficial Brasileira:** EPE (Demanda de Veículos Leves 2022–2031). |
| **C4** | **20%** | **189 VEs** | `result_TCC_ev_p20_residencial_bt.csv` | **Meta Nacional 2030:** Montadoras / Stellantis / Anfavea (PNME) e Clement-Nyns (2010). |
| **C5** | **25%** | **237 VEs** | `result_TCC_ev_p25_residencial_bt.csv` | **Caso-Base Central de Redes BT:** Rahman et al. (2022). |
| **C6** | **30%** | **284 VEs** | `result_TCC_ev_p30_residencial_bt.csv` | **Transição Consolidada:** Lopes Júnior (UFABC 2024 / IEEE Access) e limite sem reforço de Clement-Nyns (2010). |
| **C7** | **35%** | **331 VEs** | `result_TCC_ev_p35_residencial_bt.csv` | **Limiar de Hosting Capacity BT:** Rahman et al. (2022) — patamar máximo que redes BT residenciais acomodam sob recarga não coordenada antes do início de sobrecargas generalizadas. |
| **C8** | **40%** | **379 VEs** | `result_TCC_ev_p40_residencial_bt.csv` | **Cenário Decenal Estendido:** EPE (PNE 2050 - Cenário de Transição Tecnológica). |
| **C9** | **45%** | **426 VEs** | `result_TCC_ev_p45_residencial_bt.csv` | **Ponto Médio de Descarbonização:** EPE (PNE 2050 - faixa de 40% a 50% de eletrificação em 2050) e IEA (*Net Zero by 2050 Roadmap* — 45% de VEs na frota leve mundial até 2035–2040). |
| **C10** | **50%** | **474 VEs** | `result_TCC_ev_p50_residencial_bt.csv` | **Saturação Crítica:** Rahman et al. (2022), Clement-Nyns (2010) e PNE 2050 (Descarbonização Acelerada). |

---

## 4. Obras e Artigos Chave Presentes no Repositório (`Fontes/`)

Para a lista exaustiva de todas as referências do projeto formatadas segundo a ABNT NBR 6023:2018 e o sistema autor-data da NBR 10520:2023, consulte o documento [**`docs/referencias_bibliograficas.md`**](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/docs/referencias_bibliograficas.md).

As seguintes publicações indexadas e relatórios institucionais estão arquivados localmente na pasta `Fontes/` (ignorada pelo Git por volume) e fundamentam formalmente a seleção dos cenários e a metodologia do TCC:

### 4.1. Fundamentação da Difusão de VEs e Projeções de Mercado
1. **BLOOMBERGNEF (BNEF); MCKERRACHER, C. et al.** *Hitting the EV Inflection Point: Electric vehicle price parity and adoption trajectories*. London / Brussels: BloombergNEF / Transport & Environment, maio 2021. Arquivo: `Artikel-2-Jekaterina-Boening-data.pdf`.
   * *Contribuição Direta:* É o relatório seminal que comprova empiricamente que o patamar de **5% de participação nas vendas** constitui o gatilho da curva em S de difusão tecnológica. Fundamenta o cenário **C1 (5%)** como o ponto de inflexão de mercado.
2. **EMPRESA DE PESQUISA ENERGÉTICA (EPE).** *Demanda de Energia dos Veículos Leves 2022–2031*. Brasília: Ministério de Minas e Energia (MME), 2022. Arquivo: `Demanda_Veículos_Leves_2022_2031.pdf`.
   * *Contribuição Direta:* Fonte governamental primária do planejamento energético nacional. Mapeia a evolução dos licenciamentos de VEs leves no ciclo decenal brasileiro, apontando a transição de **5% a 7%** no curto prazo para **15% a 20%** até 2030–2031. Fundamenta os cenários **C1 (5%)** e **C2 (15%)**.
3. **EMPRESA DE PESQUISA ENERGÉTICA (EPE).** *Plano Nacional de Energia 2050 (PNE 2050): Mobilidade Elétrica e Demanda Energética*. Brasília: MME, 2020. Arquivo: `Relatorio Final do PNE 2050.pdf`.
   * *Contribuição Direta:* Horizontes de longo prazo e descarbonização profunda até 2050 (40% a 50% da frota eletrificada).
4. **PLATAFORMA NACIONAL DE MOBILIDADE ELÉTRICA (PNME).** *3º Anuário Brasileiro de Mobilidade Elétrica*. Brasília: PNME / Fundep, dez. 2023. Arquivo: `https___pnme.org.br_wp-content_uploads_2023_12_3o-Anuario-Brasileiro-de-Mobilidade-Eletrica_compressed.pdf`.
   * *Contribuição Direta:* Consolidação empírica do mercado nacional (market share de 4,75% em 2023, projeções setoriais de 20% até 2030 pela Stellantis/Anfavea e predominância >80% da infraestrutura domiciliar BT).

### 4.2. Impactos de Recarga Residencial e Limites Físicos em Baixa Tensão
5. **CLEMENT-NYNS, K.; HAESEN, E.; DRIESEN, J.** *The Impact of Charging Plug-In Hybrid Electric Vehicles on a Residential Distribution Grid*. **IEEE Transactions on Power Systems**, v. 25, n. 1, p. 371–380, fev. 2010. DOI: 10.1109/TPWRS.2009.2036481. Arquivo: `The_Impact_of_Charging_Plug-In_Hybrid_Electric_Vehicles_on_a_Residential_Distribution_Grid.pdf`.
   * *Contribuição Direta:* O estudo clássico seminal número #1 da literatura em redes residenciais BT. Avaliou cenários de 0% a 100% (com ênfase em 10%, 20%, 30% e 50%), comprovando que em recarga desordenada noturna, a rede suporta até 20%–30%; a partir de **30% a 50%**, ocorrem sobrecargas térmicas críticas nos transformadores e afundamentos de tensão severos nas pontas dos ramais. Justifica os cenários **C3 (30%)** e **C4 (50%)**.
6. **LOPES JÚNIOR, J. C.; SOUSA, T.; MELO, J. D.** *Estimativa de demanda para infraestrutura de carregamento de veículos elétricos*. Tese (Doutorado em Engenharia da Energia) — Universidade Federal do ABC, Santo André, 2024. / **IEEE Access**, v. 12, p. 113215–113234, 2024. Arquivo: `Estimativa de demanda para infraestrutura de carregamento de veículos elétricos.pdf` e `Demand_Estimation_..._compressed.pdf`.
   * *Contribuição Direta:* Pesquisa do P&D Neoenergia / Corredor Verde no Nordeste. Na pág. 87 aponta a lacuna da baixa tensão residencial que este TCC soluciona. Adota cenários de 7%, 30% e 65%.
7. **RAHMAN, I. et al.** *Impacts of large-scale EV charging on LV distribution networks: A comprehensive review and case study*. **Renewable and Sustainable Energy Reviews**, v. 153, p. 111742, 2022. Arquivo: `1-s2.0-S1364032121010273-main_compressed.pdf`.
   * *Contribuição Direta:* Metanálise internacional que categoriza redes BT em Baixa (5–10%), Média (20–30%) e Alta (50–100%) penetração.
8. **NWOBU, O. E.; OBI, P. I.; ODIGBO, C.** *Investigation of Voltage Deviation and Losses in Low Voltage Radial Feeders with High EV Penetration*. **International Journal of Thermal and Healthcare Science (IJTHS)**, v. 2, n. 1, p. 55–68, 2026. Arquivo: `IJTHS-020155.pdf`.
   * *Contribuição Direta:* Metodologia do Voltage Deviation Index ($VDI$) e identificação de barras fracas em alimentadores radiais.
9. **AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL).** *Procedimentos de Distribuição de Energia Elétrica no Sistema Elétrico Nacional (PRODIST) — Módulo 8: Qualidade da Energia Elétrica*. Resolução Normativa nº 956/2021. Arquivos: `anexo-resolucao-normativa-956-2021-...-MODULO_8_...docx` e `ANEXO-RESNORM-956-2021-ANEEL-BR-2-Voto.docx`.
   * *Contribuição Direta:* Critérios normativos obrigatórios de conformidade de tensão ($DRP$, $DRC$, limites de $0,93\text{ pu}$ e $0,90\text{ pu}$).
10. **MARINHO, L. A. S. S.; CELA, J. A. C. A.; MELO, L. S.; GREGORY, R. C. F.; LEÃO, R. P. S.** *Ferramenta para Apuração Automática de Indicadores de Tensão em Regime Permanente: Uma Análise Comparativa entre Normas Nacionais e Internacionais*. Universidade Federal do Ceará (UFC), 2026.
    * *Contribuição Direta:* Metodologia de desagregação dos indicadores regulatórios do PRODIST ($DRP$ e $DRC$) em componentes exclusivas de subtensão e sobretensão, essencial para o diagnóstico da causa raiz dos distúrbios em alimentadores com alta penetração de VEs e geração solar.

---

## 5. Integração com a Metodologia e Implementação Computacional

### 5.1. Alocação Estocástica no Código (`ev_creator.py`)
No código do projeto (`src/simulators/util/ev_creator.py`), a função `alocar_evs` aplica a seleção estocástica sem viés (*uniform random sampling*) sobre os domicílios BT:
* O universo amostral é fixado estritamente em **1.914 domicílios** (`base_calculo="residencial_bt"`).
* Os VEs alocados recebem modelos reais do mercado brasileiro (BYD Dolphin Mini, Dolphin GS, Song Plus, Haval H6, Renault Kwid E-Tech, etc.) com capacidades de bateria de 18,3 kWh a 60,5 kWh e potências nominais de 3,3 kW a 7,4 kW (Wallbox bifásico/monofásico).
* O perfil eletroquímico é processado pelo Caldera ICM e as demandas de injeção de corrente são acopladas nas 445 barras BT correspondentes no circuito OpenDSS.

### 5.2. Próximos Passos
1. **Seleção do Conjunto de Cenários:** O usuário define se adotará a **Opção B (5%, 15%, 30%, 50%)** ou a **Opção A (7%, 30%, 65%)**.
2. **Configuração dos Cenários:** Criação dos arquivos de configuração e orquestração via Mosaik (`scenario_ESB01S4_TCC.py`).
3. **Autorização de Execução:** Conforme as diretrizes do projeto (`GEMINI.md`), antes de rodar os scripts de simulação via terminal (`uv run`), será solicitada a autorização formal do usuário.

