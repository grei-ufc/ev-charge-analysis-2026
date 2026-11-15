# Documentação Técnica: Conversão Dinâmica de Geração Distribuída (PVSystem)

Este documento descreve detalhadamente a engenharia e o processamento de dados executados pelo script `src/ajuste-dados/codigos-rede/converter_gd_para_pvsystem.py`. O objetivo fundamental desse algoritmo é destruir a modelagem primitiva de Geração Distribuída (GD) adotada pela regulação padrão das concessionárias (BDGD) e substituí-la por um arranjo físico e dinâmico de **Sistemas Fotovoltaicos Reais (`PVSystem`)**, habilitando a rede para Co-simulações cibernéticas no ecossistema Mosaik.

---

## 1. O Problema da Modelagem BDGD (GD Estática)

Nas bases geográficas das distribuidoras brasileiras, a micro e minigeração distribuída é cadastrada majoritariamente utilizando o elemento `Generator` do OpenDSS acoplado a um `Loadshape` genérico. 
* **O Déficit Físico:** O `Generator` atua estritamente como uma "Carga Negativa". Ele injeta a potência da sua curva ignorando completamente os limites físicos de um inversor elétrico (eficiência em carga parcial, saturação de potência) e as leis da termodinâmica dos painéis.
* **O Bloqueio para a Co-Simulação:** O formato engessado não permite a injeção em tempo real de variações climáticas. Em uma rede inteligente, a passagem de uma nuvem deve reduzir a Irradiância instantaneamente, forçando quedas de tensão na rede. O `Generator` estático impede que o orquestrador (Mosaik) assuma o controle do clima.

A solução é a migração automatizada de todas as unidades geradoras da rede para o elemento **`PVSystem`**.

---

## 2. Arquitetura do Algoritmo de Conversão (`converter_gd_para_pvsystem.py`)

O código processa a conversão em quatro estágios altamente automatizados e alinhados à topologia criada pelo Pipeline de Cargas:

### A. Saneamento Cadastral BDGD, Varredura e Correção Topológica
O script localiza os arquivos de geração brutos gerados pelo `bdgd2opendss` (`GD_BT*.dss` e `GD_MT*.dss`, somando originalmente 303 geradores: 300 BT + 3 MT) e consulta diretamente as camadas `UGBT_tab` e `UGMT_tab` do Geodatabase oficial da ANEEL/Enel Ceará (`Enel_CE_39_2024-12-31_V11_20250822-1151.gdb`).
* **Filtro Cadastral `SIT_ATIV == 'AT'`:** O conversor `bdgd2opendss` não filtrava a coluna `SIT_ATIV` das tabelas de geração distribuída, convertendo unidades desativadas como geradores ativos. Como uma mesma barra (`PAC`) pode abrigar simultaneamente GDs ativas e desativadas, o script realiza o pareamento exato pelo código **`CEG_GD`** (`New "generator.<CEG_GD>"`), expurgando os **94 geradores BT com `SIT_ATIV == 'DS'`** ($903{,}04\text{ kW}$) — salvos para auditoria em `ESB01S4_gds_desativadas.dss` — e mantendo os **209 sistemas fotovoltaicos ativos** (**206 BT** = $1.835{,}90\text{ kW}$ + **3 MT** = $525{,}00\text{ kW}$, totalizando **$2.360{,}90\text{ kW}$**).
* **Extração via RegEx e Correção Topológica:** Para cada gerador ativo, são isolados `phases`, `bus1`, `kv`, `kw` e `conn`:
  * Unidades cadastradas na BDGD como trifásicas (`FAS_CON = 'ABC'` / `'ABCN'`) sobre ramais secundários fisicamente monofásicos (`BARRAS_MONOFASICAS_BT`: 23 registros na base bruta, dos quais 5 eram `DS` e **18 permanecem ativos**) são convertidas para `phases=1`, `conn=Wye` e `kV=0.22` ligadas à fase real + neutro (`.4`), eliminando nós flutuantes na matriz $Y_{\text{bus}}$.
  * Unidades polifásicas BT com `kV=0.22` são corrigidas para tensão de linha nominal `kV=0.38`, preservando `conn=Delta` nas unidades trifásicas.

### B. Engenharia Fotovoltaica e Parametrização (`PVGenerator`)
Para cada esqueleto elétrico capturado, o código instancializa a classe `PVGenerator`. É nesta fase que a física do inversor passa a existir matematicamente na simulação:
1. **$kVA$ e $P_{mpp}$:** A potência bruta outrora capturada ($kW$) é convertida nas variáveis físicas de Pico do Painel ($P_{mpp}$) e Potência Nominal do Inversor ($kVA$).
2. **Clipping (Ceifamento):** Ao configurar os painéis para injetar CC em um inversor CA, a simulação adquire a capacidade de calcular o *Clipping*. Se a irradiância superar o pico do inversor, a potência é automaticamente "ceifada", achatando o topo da curva (comportamento natural de usinas reais dimensionadas com Fator de Sobrecarga - *Oversizing*).
3. **Eficiência e Perdas:** Duas curvas não lineares são injetadas globalmente na rede (`XYCurve`): 
   * `EffCurve`: Curva de eficiência do inversor em relação ao carregamento (perdas elétricas).
   * `P-TCurve`: Curva de degradação da geração fotovoltaica conforme o aumento da Temperatura da placa solar (perdas termodinâmicas).

### C. Injeção de Telemetria Climática e Interpolação Hermitiana
Usinas fotovoltaicas reais não geram baseadas em um "fator multiplicador" bruto; elas respondem à **Irradiância Solar ($W/m^2$)** e à **Temperatura ($^\circ C$)**. 
* **Aquisição Estatística:** O algoritmo carrega um banco de dados real contendo a telemetria climática exata capturada de estações e usinas brasileiras (referência: base **BR-PVGen**). O script distribui de forma circular (módulo) dezenas de curvas climáticas validadas por entre os 209 geradores fotovoltaicos ativos da rede local, garantindo estocasticidade (nuvens e picos de sol passando em tempos diferentes por diferentes regiões geográficas do alimentador).
* **Blindagem e Sanitização Climática (Rejeição Dinâmica):** Bases de dados reais frequentemente sofrem com erros de *hardware*, como sensores reportando anomalias de $600^\circ C$ ou irradiâncias negativas. O código implementa uma barreira estrita baseada em padrões industriais (`mask()`). De acordo com as normas internacionais de homologação de módulos fotovoltaicos (como a **IEC 61215** e a **IEC 61730**) e os catálogos dos principais fabricantes, a faixa operacional de temperatura do painel é rigorosamente limitada entre **$-40^\circ C$ e $+85^\circ C$**. Valores de irradiância sofrem um limite protetor teto de **$1.5$ p.u**. (permitindo valores normais acima de 1.0 p.u. causados pelo fenômeno físico de Lente de Nuvem, mas barrando leituras impossíveis). Em vez de tentar consertar magicamente os dados defeituosos com interpolação (o que introduziria erros irreais na simulação), o sistema engatilha um "Pulo de Curva" (`ValueError`). O orquestrador descarta imediatamente a curva corrompida, exibe um *log* de aviso no terminal (`⚠️ [PULO DE CURVA]`) e busca automaticamente a próxima estação climática saudável do banco de dados, protegendo de forma integral as Matrizes Jacobianas da simulação.
* **Alinhamento da Malha Temporal (PCHIP):** O banco de telemetria climática original possui resolução de 15 minutos, enquanto o nosso modelo de Cargas e *Solver* operam na precisão cirúrgica de **10 minutos**. 
Para evitar dessincronismo no cálculo das Matrizes Jacobianas do OpenDSS, a telemetria climática sofre um agrupamento médio (`resample(new_rate).mean()`) seguido por uma **Interpolação PCHIP**. A adoção de *Piecewise Cubic Hermite Interpolating Polynomials* garante que os valos da irradiância assumam a mesma inclinação natural do sol ao longo dos 10 minutos intervalares sem criar picos negativos irrealistas ao anoitecer (*overshoots*). O recorte é feito perfeitamente para extrair 168 horas (1008 pontos), casando com a simulação.

### D. Sintetização do OpenDSS e Atualização do Orquestrador
Na última etapa, a inteligência extraída é devolvida ao HD através de matrizes massivas legíveis pelo OpenDSS:
1. **Modelagem Contínua e Otimização de I/O (Shapes Únicos):** Para garantir o máximo de eficiência de memória e evitar redundâncias, o algoritmo emprega um mecanismo de reuso. Em vez de gerar centenas de `LoadShape`s e `Tshape`s idênticos para cada gerador individual, o sistema consolida os dados e instancia apenas um único par de *shapes* por estação climática validada no *dataset*. Centenas de geradores fotovoltaicos diferentes reaproveitam (apontam para) essa mesma curva meteorológica na memória. Essa otimização derruba o tamanho e o tempo de compilação dos arquivos `.dss` e `.csv` finais em mais de 90%, otimizando redes de larga escala.
2. **Construção do PVSystem:** Cada inversor fotovoltaico ativo é instanciado na rede utilizando a sintaxe do OpenDSS, fazendo o redirecionamento centralizado dos *shapes*: 
   ```text
   New PVSystem.PV1 phases=3 conn=Delta Bus1=... kV=0.38 kVA=2.4 irrad=1.0 Pmpp=2.4
   ~ temperature=25 PF=1 EffCurve=MyEff P-TCurve=MyPvsT
   ~ Daily=shape_irrad_1 TDaily=shape_temp_1
   ~ Model=1 Vminpu=0.8 Vmaxpu=1.2
   ```
3. **Auto-Injeção no Orquestrador (`run`):** Para anular o risco de falha humana na compilação, o script possui uma rotina que acessa o arquivo mestre de execução (`run_ESB01S4.dss`), vasculha o seu conteúdo de forma programática e injeta perfeitamente a string `Redirect ESB01S4_pv.dss` e seus dependentes pouco antes da invocação do laço de tempo do OpenDSS (`Set ControlMode=Time`).

**Conclusão:** O produto deste script converte os geradores passivos e saneados da BDGD (`SIT_ATIV == 'AT'`) em **209 Inversores Fotovoltaicos ativos (`PVSystem`)** independentes (`206` BT + `3` MT, totalizando `2.360,90 kW`). Esses elementos reagem dinamicamente e com extrema precisão física a um microclima de irradiância calibrado perfeitamente a cada 10 minutos do fluxo de potência estocástico das cargas elétricas vizinhas.
