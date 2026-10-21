# Relatório de Diagnóstico e Convergência — Alimentador `ESB01S4` (OpenDSS / BDGD)

**Data:** 19/10/2026  
**Ferramenta de Análise:** `py-dss-interface` (OpenDSS Engine)  
**Diretório do Alimentador:** `data/rede/ESB01S4/`  
**Arquivo Principal de Simulação:** `data/rede/ESB01S4/run_ESB01S4.dss`

---

## 1. Resumo Executivo

O alimentador `ESB01S4`, modelado no OpenDSS a partir da Base de Dados Geográfica da Distribuidora (BDGD) e acrescido de perfis sintéticos de cargas, sistemas fotovoltaicos (`PVSystem`) e veículos elétricos (EVs), apresentava **falha de convergência** (atingindo o limite de 150 iterações em todos os passos) e **tensões nodais irreais** (chegando a mais de $16\text{ p.u.}$ em algumas barras e colapsando para $0,32\text{ p.u.}$ em outras).

Seguindo a estratégia de simplificação progressiva da topologia (isolando a Média Tensão da Baixa Tensão e testando cada grupo de elementos separadamente via `py-dss-interface`), comprovou-se que:

1. **A rede de Média Tensão (MT) é 100% saudável e estável:** Removendo a rede de Baixa Tensão (BT), o alimentador converge em **100% dos passos (`144/144`)** com média de apenas **2,0 iterações por passo**, tensões entre $0,985\text{ p.u.}$ e $1,045\text{ p.u.}$ e potências coerentes na subestação.
2. **Todos os problemas de convergência residem na Baixa Tensão (BT)** e decorrem de **três causas principais**:
   - **Causa A:** **23 sistemas `PVSystem` trifásicos** conectados a barramentos BT que possuem **apenas 1 fase + neutro** (`.1.4` ou `.3.4`), criando nós eletricamente flutuantes com sobretensões de $6,0\text{ p.u.}$ a $16,3\text{ p.u.}$
   - **Causa B:** Omissão de `conn=Delta` na conversão de `GD_BT` para `PVSystem` (`converter_gd_para_pvsystem.py`), fazendo com que o OpenDSS adote `conn=wye` aterrado diretamente na referência `.0`, em conflito com o neutro `.4` dos transformadores BT (aterrado por reator de $15\,\Omega$), gerando severo deslocamento de neutro (até $155\text{ V}$).
   - **Causa C:** Sobrecarga extrema no transformador BT `TRF_TOK5079A` (`2296520tr`, **150 kVA** alimentando **533,26 kW** de cargas em 207 barras), cuja queda de tensão atinge exatamente o limiar `vminpu=0.5` das cargas `model=3`, provocando oscilação numérica entre iterações.

---

## 2. Comparativo dos Cenários Simulados

Os testes abaixo foram executados em modo **Snapshot** e em modo **Daily** (1 dia completo = 144 passos de 10 minutos, `maxiterations=150`, `maxcontroliter=100`):

| Cenário | Elementos Incluídos | Passos Convergidos (Daily) | Média de Iterações | Máx. Iterações | Faixa de Tensão de Fase ($V_{\text{pu}}$) | Diagnóstico |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Apenas Rede MT** | `SegmentosMT`, `ChavesMT`, `ReguladorMT`, `CargasMT_Sintetico`, `GD_MT` | **144 / 144 (100%)** | **2,0** | 2 | $0,985 \text{ – } 1,045$ | Operação perfeita ($P_{\text{sub}} \in [646; 2289]\text{ kW}$, perdas de $9,4\text{ a }48,0\text{ kW}$). |
| **2. Rede MT + BT (Sem Cargas/PV/EV)** | `Master` completo (apenas linhas e transformadores em vazio) | **1 / 1 (Snapshot)** | **2,0** | 2 | $1,008 \text{ – } 1,037$ | Topologia física de linhas e transformadores sem defeitos em vazio. |
| **3. Rede MT + BT Completa (Original)** | `run_ESB01S4.dss` original (`Master` + `Cargas` + `PV` + `EV`) | **0 / 144 (0%)** | **150,0** | 150 | $0,000 \text{ – } 16,320$ | Divergência total por nós flutuantes nos PVs, deslocamento de neutro e colapso em `TRF_TOK5079A`. |
| **4. Rede MT + BT (Apenas PVs corrigidos)** | Completo, corrigindo os 23 PVs monofásicos e `conn=Delta` nos PVs 3F | **58 / 144 (40,3%)** | **92,1** | 150 | $0,468 \text{ – } 1,055$ | Converge na madrugada/manhã, mas diverge nos horários de carga alta devido ao `vminpu=0.5` no circuito do `TRF_TOK5079A`. |
| **5. Rede MT + BT (PVs corrigidos + `vminpu=0.80` nas Cargas BT)** | Completo + correção dos PVs + `vminpu=0.80` nas cargas BT | **144 / 144 (100%)** | **5,6** | 9 | $0,590 \text{ – } 1,055$ | **Convergência de 100% em todos os passos**, sem oscilações numéricas. |

---

## 3. Detalhamento das Causas Raiz na Baixa Tensão

### 3.1. Causa A: 23 `PVSystem` Trifásicos Conectados em Barras BT Monofásicas (Nós Flutuantes)

No arquivo `data/rede/ESB01S4/ESB01S4_pv.dss` (originado de `GD_BT_20250139_ESB01S4_------1-----.dss`), **23 sistemas fotovoltaicos** foram declarados como trifásicos (`phases=3`, `kV=0.38`, `Bus1=<barra>.1.2.3` ou `.1.2.3.4`). Entretanto, ao inspecionar os segmentos e ramais BT (`SegmentosBT` e `RamaisBT`) que chegam a essas barras, verifica-se que **essas barras possuem apenas 1 fase e neutro** (`{1, 4}` ou `{3, 4}`).

Como consequência:
- Dois dos três terminais de fase de cada um desses 23 inversores (`.2` e `.3`, ou `.1` e `.2`) ficam **eletricamente isolados (flutuantes)** na matriz de admitância nodal $Y_{\text{bus}}$.
- Aliado ao parâmetro `Vminpu=0.001` nos objetos `PVSystem`, o OpenDSS tenta injetar potência ativa nesses nós sem admitância de saída, elevando a tensão nodal para valores entre **6,0 p.u. e 16,3 p.u.** e destruindo a convergência.

#### Tabela Completa dos 23 Sistemas PV com Incompatibilidade de Fases

| Nome do PV | Barra Declarada (`Bus1`) | Fases no PV | `kV` no PV | Potência (`kVA` / `Pmpp`) | Nós Realmente Existentes na Rede BT | Correção Necessária |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `pv20` | `3866974338468827.1.2.3` | 3 | 0,38 | 8,40 | `{3, 4}` | `phases=1 Bus1=3866974338468827.3.4 kV=0.22 conn=wye` |
| `pv34` | `3858807938464405.1.2.3` | 3 | 0,38 | 5,40 | `{1, 4}` | `phases=1 Bus1=3858807938464405.1.4 kV=0.22 conn=wye` |
| `pv37` | `3857601938460002.1.2.3` | 3 | 0,38 | 7,20 | `{1, 4}` | `phases=1 Bus1=3857601938460002.1.4 kV=0.22 conn=wye` |
| `pv41` | `3858371138460380.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3858371138460380.1.4 kV=0.22 conn=wye` |
| `pv52` | `3857773338459146.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3857773338459146.1.4 kV=0.22 conn=wye` |
| `pv74` | `3856380038463820.1.2.3` | 3 | 0,38 | 5,40 | `{1, 4}` | `phases=1 Bus1=3856380038463820.1.4 kV=0.22 conn=wye` |
| `pv76` | `3866354038468928.1.2.3` | 3 | 0,38 | 8,00 | `{1, 4}` | `phases=1 Bus1=3866354038468928.1.4 kV=0.22 conn=wye` |
| `pv141` | `3859103838474718.1.2.3` | 3 | 0,38 | 15,00 | `{1, 4}` | `phases=1 Bus1=3859103838474718.1.4 kV=0.22 conn=wye` |
| `pv151` | `3872701038464502.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3872701038464502.1.4 kV=0.22 conn=wye` |
| `pv154` | `3857881438458524.1.2.3.4` | 3 | 0,38 | 15,00 | `{1, 4}` | `phases=1 Bus1=3857881438458524.1.4 kV=0.22 conn=wye` |
| `pv158` | `3858218938460615.1.2.3` | 3 | 0,38 | 16,00 | `{1, 4}` | `phases=1 Bus1=3858218938460615.1.4 kV=0.22 conn=wye` |
| `pv159` | `3857343438464427.1.2.3` | 3 | 0,38 | 7,10 | `{1, 4}` | `phases=1 Bus1=3857343438464427.1.4 kV=0.22 conn=wye` |
| `pv160` | `3857601938460002.1.2.3.4` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3857601938460002.1.4 kV=0.22 conn=wye` |
| `pv162` | `3858922838474457.1.2.3` | 3 | 0,38 | 20,00 | `{3, 4}` | `phases=1 Bus1=3858922838474457.3.4 kV=0.22 conn=wye` |
| `pv171` | `3857343438464427.1.2.3` | 3 | 0,38 | 7,00 | `{1, 4}` | `phases=1 Bus1=3857343438464427.1.4 kV=0.22 conn=wye` |
| `pv184` | `3873424138463998.1.2.3` | 3 | 0,38 | 5,00 | `{1, 4}` | `phases=1 Bus1=3873424138463998.1.4 kV=0.22 conn=wye` |
| `pv185` | `3862115538458927.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3862115538458927.1.4 kV=0.22 conn=wye` |
| `pv204` | `3876796438462655.1.2.3` | 3 | 0,38 | 10,00 | `{3, 4}` | `phases=1 Bus1=3876796438462655.3.4 kV=0.22 conn=wye` |
| `pv227` | `3873369138464025.1.2.3` | 3 | 0,38 | 3,00 | `{1, 4}` | `phases=1 Bus1=3873369138464025.1.4 kV=0.22 conn=wye` |
| `pv239` | `3873397138464000.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3873397138464000.1.4 kV=0.22 conn=wye` |
| `pv273` | `3859057838459073.1.2.3` | 3 | 0,38 | 8,05 | `{1, 4}` | `phases=1 Bus1=3859057838459073.1.4 kV=0.22 conn=wye` |
| `pv279` | `3857411438459173.1.2.3` | 3 | 0,38 | 8,00 | `{1, 4}` | `phases=1 Bus1=3857411438459173.1.4 kV=0.22 conn=wye` |
| `pv290` | `3872644238464508.1.2.3` | 3 | 0,38 | 6,00 | `{1, 4}` | `phases=1 Bus1=3872644238464508.1.4 kV=0.22 conn=wye` |

> **Nota:** Todas as cargas de Baixa Tensão (`CargasBT_Sintetico_20250139_ESB01S4.dss`) também foram verificadas quanto à consistência topológica de fases e **nenhuma carga apresentou nó inexistente** (`0` erros em 5.654 elementos de carga). O problema de nós flutuantes é exclusivo dos 23 sistemas `PVSystem` listados acima.

---

### 3.2. Causa B: Omissão de `conn=Delta` nos `PVSystem` Trifásicos (Deslocamento de Neutro `.0` vs `.4`)

No arquivo original da BDGD (`GD_BT_20250139_ESB01S4_------1-----.dss`), os 300 geradores BT estão definidos como:
- **297 geradores trifásicos:** `phases=3 kv=0.38 conn=Delta`
- **3 geradores monofásicos (`pv85`, `pv147`, `pv155`):** `phases=1 kv=0.22 conn=Wye bus1=<barra>.1.4`

Porém, o script `src/ajuste-dados/codigos-rede/converter_gd_para_pvsystem.py` (linhas 43–60) extrai apenas `phases`, `bus1`, `kv` e `kw`, **descartando o atributo `conn`**.

Quando `conn` é omitido em um `PVSystem` no OpenDSS:
1. O OpenDSS adota por padrão **`conn=wye`**.
2. Como o terminal está declarado como `Bus1=<barra>.1.2.3` (sem o quarto nó `.4`), o OpenDSS aterra o ponto neutro da estrela do inversor diretamente na **referência ideal da terra (`.0`)**.
3. Entretanto, na modelagem da BDGD (`TransformadorMTMTMTBT_20250139_ESB01S4_------1-----.dss`), o neutro do secundário de todos os transformadores MT/BT está conectado ao **condutor `.4`**, o qual é aterrado através de um reator/resistor de aterramento de **$15\,\Omega$** (`New Reactor.TRF_... bus1=<barra>tr.4 bus2=<barra>tr.0 R=15 X=0`).
4. Isso cria um caminho espúrio de sequência zero através da terra (`.0`) entre os inversores e o resistor de $15\,\Omega$ do transformador. No ramo do transformador `TRF_TEK0222A` (barra `310537494tr`), por exemplo, a tensão do condutor neutro `.4` desloca-se para **$155,1\text{ V}$ ($0,707\text{ p.u.}$)**, empurrando as tensões fase-terra das fases 1 e 2 para **$1,526\text{ p.u.}$ ($334,8\text{ V}$)** e afundando a fase 3 para **$0,324\text{ p.u.}$ ($71,2\text{ V}$)**, impedindo a convergência.

**Comprovação experimental (Cenário `Master + PV` em Snapshot):**
- Com `conn=wye` (default atual): **Não converge** (`Converged = 0`, `150` iterações).
- Definindo `conn=delta` nos PVs trifásicos (ou conectando ao neutro `.4` com `vminpu=0.8`) e corrigindo os 23 PVs monofásicos: **Converge em 8 iterações** (`Converged = 1`, $V_{\text{pu}} \in [1,008; 1,076]$).

---

### 3.3. Causa C: Sobrecarga Severa no Transformador `TRF_TOK5079A` (`2296520tr`) e Oscilação em `vminpu=0.5`

Mesmo simulando a rede **sem nenhum sistema PV ou EV** (`Master` + `CargasBT_Sintetico` ou `CargasBT` original da BDGD), o fluxo de potência falha em convergir nos horários de maior demanda.

Ao mapear todas as sub-redes secundárias (BT) por transformador MT/BT, identificou-se uma anomalia severa no transformador **`TRF_TOK5079A`** (barra secundária `2296520tr`):

#### Resumo das Principais Sub-redes BT por Transformador

| Transformador | Barra BT | Potência Nominal (`kVA`) | Nº de Barras BT | Carga BT Instalada (`kW`) | GD BT Instalada (`kVA`) | Relação Carga / Trafo |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`TRF_TOK5079A`** | `2296520tr` | **150,0** | **207** | **533,26 kW** | 183,10 kVA | **355,5%** (Sobrecarga extrema) |
| `TRF_29L2218A` | `147874444tr` | 75,0 | 322 | 92,90 kW | 66,00 kVA | 123,9% |
| `TRF_TOP7583A` | `4629197tr` | 112,5 | 207 | 90,90 kW | 236,10 kVA | 80,8% |
| `TRF_TKS0917A` | `203121545tr` | 150,0 | 45 | 84,90 kW | 331,00 kVA | 56,6% |
| `TRF_TKS0918A` | `203121547tr` | 225,0 | 104 | 72,30 kW | 236,00 kVA | 32,1% |
| `TRF_29L1163A` | `147874442tr` | 75,0 | 73 | 65,70 kW | 136,50 kVA | 87,6% |
| `TRF_29L1610A` | `2296525tr` | 150,0 | 116 | 63,10 kW | 175,30 kVA | 42,1% |

#### Perfil de Queda de Tensão no Tronco BT do `TRF_TOK5079A`
O transformador `TRF_TOK5079A` (150 kVA) alimenta 350 elementos de carga (175 consumidores) através de um tronco BT de ~270 metros com cabo `Linecode=113458533_4` ($R_1 = 0,732\,\Omega/\text{km}$, $I_{\text{norm}} = 195\text{ A}$):
1. Barra MT `3870454638466202` (primário do trafo): $V = [1,029;\; 1,031;\; 1,030]\text{ p.u.}$
2. Barra BT `2296520tr` (saída secundária do trafo): $V = [0,899;\; 0,919;\; 0,911]\text{ p.u.}$ (~10% de queda apenas na impedância interna do transformador devido à sobrecarga).
3. Barra BT `3870827138466016` (+48 m): $V = [0,788;\; 0,823;\; 0,814]\text{ p.u.}$
4. Barra BT `3871303338466059` (+131 m): $V = [0,658;\; 0,706;\; 0,690]\text{ p.u.}$
5. Barra BT `3872145438465583` (+240 m): $V = [0,551;\; 0,598;\; 0,575]\text{ p.u.}$
6. Barras finais `3872640938465802` / `3872188838466090` (+296 m): **$V \approx 0,50\text{ p.u.}$ ($85\text{ V a }117\text{ V}$)**.

#### Por que ocorre a não-convergência em $0,50\text{ p.u.}$?
Todas as cargas BT estão divididas em duas parcelas (`_M1` com `model=2` Z constante e `_M2` com `model=3` P constante / Q variável) e configuradas com **`vminpu=0.5`**.
- Quando a tensão nas barras finais do `TRF_TOK5079A` atinge $0,50\text{ p.u.}$, as cargas `model=3` ficam exatamente sobre o ponto de transição entre potência constante e impedância constante.
- A cada iteração de ponto fixo do OpenDSS, a tensão nessas barras salta entre **$85\text{ V}$ ($0,39\text{ p.u.}$) e $117\text{ V}$ ($0,53\text{ p.u.}$)** ($\Delta V \approx 42\text{ V}$ por iteração), nunca estabilizando dentro da tolerância de $0,0001\text{ p.u.}$
- **Solução comprovada:** Ao alterar `vminpu` das cargas BT de `0.5` para **`0.80`** (ou `0.75`–`0.85`, faixa recomendada no OpenDSS para evitar colapso numérico em redes BT sobrecarregadas), a transição para impedância constante ocorre de forma suave e **100% dos 144 passos diários convergem em média com 5,6 iterações**.

---

## 4. Outros Detalhes de Modelagem Identificados

### 4.1. Ordem dos Comandos em `run_ESB01S4.dss`
Em `data/rede/ESB01S4/run_ESB01S4.dss` (linhas 25–34):
```dss
Set mode=Daily
Set stepsize=10m
Set number=1008

Set Voltagebases=[13.8 0.38 0.22]
CalcVoltageBases
```
O comando `CalcVoltageBases` realiza uma solução em vazio para determinar as bases de tensão de cada barra e deve ser executado **antes** de configurar `Set mode=Daily` e `Set number=1008`.

### 4.2. Omissão de Impedância de Sequência Zero (`r0`, `x0`) em `CodCondutor`
No arquivo `data/rede/ESB01S4/CodCondutor_20250139_ESB01S4_------1-----.dss`, os objetos `Linecode` definem apenas `r1` e `x1`:
```dss
New "Linecode.113458533_4" nphases=4 r1=0.732 x1=0.322 normamps=195.000 units=km
```
Como `r0` e `x0` não são informados, o OpenDSS mantém seus valores default internos (`r0=0.1784`, `x0=0.4047`). Para condutores BT mais finos (onde `r1` chega a `5.24 ohm/km`), isso faz com que $R_0 \ll R_1$, gerando resistências mútuas negativas na matriz de fase ($R_m = (R_0 - R_1)/3 < 0$). Caso não haja dados de sequência zero na BDGD, recomenda-se definir explicitamente $R_0 \approx 3 R_1$ e $X_0 \approx 3 X_1$ (ou manter a redução de Kron consistente).

### 4.3. Sorteio Duplicado de Curvas `_M1` e `_M2` em `passo4_montar_semanas.py`
No script `src/ajuste-dados/codigos-cargas/passo4_montar_semanas.py` (linhas 223–250), cada linha do arquivo `CargasBT` é tratada como uma carga independente. Como cada unidade consumidora da BDGD possui duas entradas (`_M1` e `_M2`), o script sorteia duas curvas `LoadShape` diferentes (`LS_<id>_M1` e `LS_<id>_M2`) para o mesmo consumidor, em vez de compartilhar a mesma curva estocástica entre as duas metades do modelo ZIP.

### 4.4. Execução Automatizada via `py-dss-interface` no Windows
Quando o OpenDSS atinge limites de iteração ou avisos de controle no Windows, a DLL nativa pode abrir janelas modais invisíveis que travam a execução em background. Nos scripts Python que utilizam `py-dss-interface`, recomenda-se sempre incluir logo após instanciar `DSS()`:
```python
dss = py_dss_interface.DSS()
dss.dssinterface.allow_forms = 0
```

---

## 5. Resumo das Recomendações e Correções

1. **Corrigir `src/ajuste-dados/codigos-rede/converter_gd_para_pvsystem.py` e regenerar `ESB01S4_pv.dss`:**
   - Ler e preservar a propriedade `conn` (`Delta` ou `Wye`) do arquivo `GD_BT`.
   - Verificar os nós existentes na barra BT antes de declarar o `PVSystem`: para os 23 casos em barras monofásicas, converter para `phases=1`, `kV=0.22`, `conn=wye` e `Bus1=<barra>.<fase>.4`.
   - Ajustar `vminpu=0.80` e `vmaxpu=1.20` (em vez de `Vminpu=0.001`).
2. **Ajustar `vminpu` nas Cargas BT (`CargasBT_Sintetico_20250139_ESB01S4.dss`):**
   - Alterar `vminpu=0.5` para `vminpu=0.80` (e opcionalmente avaliar se a carga ou a potência nominal de `TRF_TOK5079A` na BDGD possui erro de cadastro).
3. **Reordenar `data/rede/ESB01S4/run_ESB01S4.dss`:**
   - Posicionar `Set Voltagebases=[13.8 0.38 0.22]` e `CalcVoltageBases` antes de `Set mode=Daily`.

