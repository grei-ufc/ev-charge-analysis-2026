# Metodologia de Alocação Incremental Aninhada de Veículos Elétricos (*Nested Adoption Model*)

Este documento detalha a formulação matemática, o algoritmo computacional e a fundamentação teórica da **Lógica de Alocação Incremental Aninhada (*Nested / Cumulative Adoption Model*)**, implementada no módulo [`src/simulators/util/ev_creator.py`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/src/simulators/util/ev_creator.py) para a parametrização dos cenários de penetração de Veículos Elétricos (VEs) no alimentador real **ESB01S4** (Neoenergia Cosern).

---

## 1. Fundamentação Teórica: Difusão Cumulativa de Inovações Tecnológicas

Em estudos de planejamento de sistemas de distribuição de energia elétrica com penetração progressiva de Recursos Energéticos Distribuídos (REDs), a alocação de novas cargas veiculares deve representar com fidedignidade o processo socioeconômico de eletrificação da frota particular.

Segundo a **Teoria da Difusão de Inovações de Rogers (2003)** e os modelos analíticos de crescimento de mercado de **Bass (1969)**, a adoção de bens tecnológicos de consumo durável é um processo **estritamente cumulativo e irreversível** em horizontes de planejamento:
* O consumidor pioneiro (*innovator / early adopter*) que adquire um veículo elétrico em um determinado estágio de mercado ($5\%$ de penetração) **permanece com seu veículo nas etapas subsequentes** ($10\%, 15\%, \dots, 50\%$).
* O aumento da penetração reflete o ingresso contínuo de novos adotantes (*early majority* e *late majority*) na rede, sem que os adotantes prévios sejam realocados geograficamente ou troquem aleatoriamente de fase elétrica de conexão.

```
       PROGRESSÃO CRONOLÓGICA DA ADOÇÃO ANINHADA (ROGERS, 2003)
==========================================================================
Cenário 05% (47 VEs):  [ VE_1, VE_2, ..., VE_47 ]
Cenário 10% (95 VEs):  [ VE_1, VE_2, ..., VE_47 ] + [ VE_48, ..., VE_95 ]
Cenário 15% (142 VEs): [ VE_1, VE_2, ..., VE_95 ] + [ VE_96, ..., VE_142 ]
...
Cenário 50% (474 VEs): [ VE_1, ..., VE_426 ]      + [ VE_427, ..., VE_474 ]
==========================================================================
         RELAÇÃO DE CONTENÇÃO ESTREITA: V(p_1) ⊂ V(p_2) ⊂ ... ⊂ V(p_k)
```

---

## 2. Limitações Críticas da Amostragem Independente de Monte Carlo

Em versões preliminares de simulação, cada taxa de penetração $p \in \{5, 10, \dots, 50\}\%$ sorteava de forma independente um subconjunto de tamanho $k$ a partir dos $N_{\text{total}} = 947$ domicílios através da função nativa `random.sample(lista, k)`. 

Essa abordagem, embora comum em ensaios puramente estatísticos descorrelacionados, introduziu anomalias nas análises eletrotécnicas:

1. **Variabilidade Espacial Descorrelacionada:** Em virtude da implementação interna de *Fisher-Yates* do Python, o conjunto de 379 domicílios sorteados para $40\%$ não era um subconjunto contido nos 426 domicílios de $45\%$.
2. **Efeito Falso de Recuperação da Tensão Nodal ($V_{\min}$):** No cenário de 40%, o sorteio aleatório alocou múltiplos VEs de $7{,}2\text{ kW}$ em uma mesma fase na ponta de um ramal secundário longo (concentração local / *clustering*), provocando um afundamento extremo de $0{,}722\text{ pu}$. Já em 45%, a nova amostra dispersou os veículos de forma mais balanceada, elevando a tensão mínima pontual para $0{,}817\text{ pu}$.
3. **Viés no Diagnóstico do Sistema:** Esse comportamento criava a ilusão incorreta de que a rede "melhorava" com mais carros elétricos, quando na verdade tratava-se de um ruído introduzido pela troca aleatória de domicílios amostrados.

---

## 3. Formulação Matemática do Modelo Incremental Aninhado

Para eliminar completamente esse ruído e assegurar que as degradações observadas na rede decorram **exclusivamente do acréscimo de carga**, formaliza-se a seguinte estrutura:

### 3.1. Ordenação Canônica e Permutação Fixa
Seja $\mathcal{D} = \{d_1, d_2, \dots, d_{N_{\text{total}}}\}$ o conjunto de $N_{\text{total}} = 947$ unidades consumidoras residenciais de Baixa Tensão (BT) do alimentador ESB01S4. 
Ordena-se $\mathcal{D}$ canonicamente por identificador e barra para neutralizar variações entre sistemas operacionais:

$$\mathcal{D}_{\text{ordenado}} = \text{sort}(\mathcal{D})$$

Aplica-se uma permutação estocástica $\pi$ gerada por uma semente pseudoaleatória fixa e documentada ($\text{seed} = 42$):

$$\mathcal{F}_{\text{adoção}} = \pi(\mathcal{D}_{\text{ordenado}}) = \left( d_{(1)}, d_{(2)}, \dots, d_{(N_{\text{total}})} \right)$$

Onde $\mathcal{F}_{\text{adoção}}$ representa a **Fila Universal de Adoção** do circuito.

---

### 3.2. Pré-atribuição Canônica de Parâmetros Eletrotécnicos
Para cada domicílio $j$ posicionado no índice $i$ da fila $\mathcal{F}_{\text{adoção}}$, são sorteados previamente e de forma definitiva:

1. **Curva Estocástica de Recarga ($C_i$):** Sorteada a partir dos perfis de condução realísticos do *Caldera Storage & Battery Simulator* (com baterias Li-ion, potências nominais de $3{,}6\text{ kW}$ ou $7{,}2\text{ kW}$ e perfis temporais de chegada residencial):
   $$C_i \in \mathcal{P}_{\text{Caldera}}, \quad P_{\text{nom},i} \in \{3{,}6\text{ kW}, 7{,}2\text{ kW}\}$$

2. **Fase Elétrica de Conexão ($\phi_i$):** Conexão monofásica fase-neutro ($220\text{ V}$) sorteada entre as fases disponíveis no ramal do domicílio:
   $$\phi_i \in \text{Fases}(d_{(i)}) \subseteq \{1, 2, 3\}$$

---

### 3.3. Fatiamento Cumulativo dos Cenários
Para qualquer taxa de penetração percentual $p_k \in [0\%, 50\%]$, a quantidade de VEs alocados é:

$$N_k = \text{round}\left( N_{\text{total}} \times \frac{p_k}{100} \right)$$

O conjunto de veículos elétricos ativos no cenário $p_k$, denotado por $\mathcal{V}(p_k)$, é dado pelo fatiamento estrito da fila:

$$\mathcal{V}(p_k) = \{ (d_{(i)}, C_i, \phi_i) \mid 1 \le i \le N_k \}$$

Desta formulação decorre o **Princípio da Contenção Estrita**:

$$\forall \, p_a < p_b \implies \mathcal{V}(p_a) \subset \mathcal{V}(p_b)$$

$$\mathcal{V}(p_b) = \mathcal{V}(p_a) \cup \Delta \mathcal{V}(p_a \to p_b)$$

Onde $\Delta \mathcal{V}(p_a \to p_b) = \{ (d_{(i)}, C_i, \phi_i) \mid N_a < i \le N_b \}$ são rigorosamente os novos consumidores que adquiriram VEs no incremento de penetração.

---

## 4. Tabela de Quantitativos da Grade Padrão do TCC

A tabela abaixo sumariza o dimensionamento rigoroso dos 10 cenários de co-simulação para os $947$ domicílios residenciais BT:

| Cenário ($p_k$) | Quantidade Acumulada ($N_k$) | Acréscimo Incremental ($\Delta N_k$) | Fração da Fila ($\mathcal{F}_{\text{adoção}}$) | Status de Adoção |
| :---: | :---: | :---: | :---: | :--- |
| **Caso Base (0%)** | **0 VEs** | - | - | Referência Limpa (0 VEs) |
| **5% VEs** | **47 VEs** | $+47$ | Índices $1 \dots 47$ | Adotantes Iniciais |
| **10% VEs** | **95 VEs** | $+48$ | Índices $1 \dots 95$ | Adotantes Iniciais |
| **15% VEs** | **142 VEs** | $+47$ | Índices $1 \dots 142$ | *Hosting Capacity* Limiar |
| **20% VEs** | **189 VEs** | $+47$ | Índices $1 \dots 189$ | Maioria Inicial |
| **25% VEs** | **237 VEs** | $+48$ | Índices $1 \dots 237$ | Maioria Inicial |
| **30% VEs** | **284 VEs** | $+47$ | Índices $1 \dots 284$ | Maioria Inicial |
| **35% VEs** | **331 VEs** | $+47$ | Índices $1 \dots 331$ | Expansão Rápida |
| **40% VEs** | **379 VEs** | $+48$ | Índices $1 \dots 379$ | Maioria Tardia |
| **45% VEs** | **426 VEs** | $+47$ | Índices $1 \dots 426$ | Maioria Tardia |
| **50% VEs** | **474 VEs** | $+48$ | Índices $1 \dots 474$ | Meio do Alimentador |

---

## 5. Algoritmo Computacional Implementado

O algoritmo a seguir sintetiza a lógica programada no script [`src/simulators/util/ev_creator.py`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/src/simulators/util/ev_creator.py):

```python
def alocar_evs_incremental_aninhado(penetracao_pct, seed=42):
    # 1. Mapeamento e ordenação canônica
    consumidores = mapear_topologia_bt(CIRCUITO_DSS)
    lista_consumidores = sorted(
        list(consumidores.values()),
        key=lambda c: (str(c.get('bus', '')), str(c.get('name', '')))
    )
    
    # 2. Embaralhamento único e determinístico
    rng = random.Random(seed)
    rng.shuffle(lista_consumidores)
    
    # 3. Pré-geração da Fila de Adoção Canônica
    fila_adocao = []
    for idx, local in enumerate(lista_consumidores, start=1):
        curva = rng.choice(curvas_disponiveis)
        fase = rng.choice(local['phases'])
        fila_adocao.append({"idx": idx, "local": local, "curva": curva, "fase": fase})
        
    # 4. Fatiamento estrito cumulativo (Nested Slicing)
    qtd_evs = round(len(lista_consumidores) * (penetracao_pct / 100.0))
    veiculos_cenario = fila_adocao[:qtd_evs]
    
    # 5. Escrita das diretrizes no arquivo OpenDSS (ESB01S4_evs.dss)
    gravar_arquivo_opendss(veiculos_cenario)
```

---

## 6. Vantagens Eletrotécnicas e Metodológicas no TCC

A adoção do Modelo Incremental Aninhado traz vantagens determinantes para a solidez científica da pesquisa:

1. **Monotonicidade Física Estrita da Demanda:** A energia consumida pelos VEs ($\sum E_{\text{VE}}$) e a demanda acumulada tornam-se estritamente crescentes ($E_{k+1} > E_k$).
2. **Eliminação de Falsas Recuperações de Tensão:** O perfil de tensão em qualquer barra da rede $V_i(t, p_{k+1})$ será sempre menor ou igual a $V_i(t, p_k)$, garantindo que o indicador de tensão mínima global $V_{\min}$ decresça monotonicamente com a penetração.
3. **Consistência dos Indicadores PRODIST Módulo 8 (MARINHO et al., 2026):**
   Uma barra que entra em violação de $\text{DRP} > 3\%$ ou $\text{DRC}_{\text{sub}} > 0{,}5\%$ em determinado patamar de penetração **permanece em violação em todos os cenários superiores**, permitindo traçar curvas de acumulação acumulada de barras não conformes ($\Delta N_{\text{barras}}$) matematicamente consistentes.
4. **Isolamento Perfeito da Relação Causa-Efeito:** Permite atribuir com 100% de rigor que qualquer novo transformador em sobrecarga ou nova barra em subtensão decorre exclusivamente da adição do novo bloco de VEs ($\Delta N$).

---

## 7. Referências Normativas e Bibliográficas (Padrão ABNT NBR 6023:2018)

* AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL). **Procedimentos de Distribuição de Energia Elétrica no Sistema Elétrico Nacional (PRODIST): Módulo 8 – Qualidade da Energia Elétrica**. Brasília: ANEEL, 2021.
* BASS, F. M. A new product growth for model consumer durables. **Management Science**, v. 15, n. 5, p. 215-227, 1969.
* CLEMENT-NYNS, K.; HAESEN, E.; DRIESEN, J. The impact of charging plug-in hybrid electric vehicles on a residential distribution grid. **IEEE Transactions on Power Systems**, v. 25, n. 1, p. 371-380, 2010.
* MARINHO, C. H. et al. Voltage quality indicators decomposition in distribution systems with high integration of distributed energy resources. **Electric Power Systems Research**, v. 228, p. 109985, 2026.
* NWOBU, E. C.; OBI, P. I.; ODIGBO, C. O. Voltage Deviation Index (VDI) formulation and Maximum-VDI Rule for hosting capacity and EV charging flexibility in distribution networks. **IEEE Access**, v. 14, p. 11204-11218, 2026.
* ROGERS, E. M. **Diffusion of Innovations**. 5. ed. New York: Free Press, 2003.

