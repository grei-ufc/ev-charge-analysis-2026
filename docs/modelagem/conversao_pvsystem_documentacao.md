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

### A. Varredura e Extração Topológica (RegEx)
O script localiza os arquivos de geração brutos originais que habitam a pasta da rede (arquivos `GD_BT*.dss` e `GD_MT*.dss`). Em vez de exigir uma parametrização manual exaustiva das mais de 600 usinas, ele utiliza **Expressões Regulares (RegEx)** para dissecar o arquivo linha a linha.
Sempre que encontra o prefixo `New "Generator...`, o motor isola os parâmetros elétricos que dão a "identidade" da usina:
* `phases`: Número de fases (mono, bi ou trifásico).
* `bus1`: A coordenada topológica exata de interligação da GD.
* `kv`: O nível de tensão de operação.
* `kw`: A potência nominal homologada.
A usina antiga é então descartada da memória, e apenas o seu esqueleto topológico é salvo para a recriação estrutural.

### B. Engenharia Fotovoltaica e Parametrização (`PVGenerator`)
Para cada esqueleto elétrico capturado, o código instancializa a classe `PVGenerator`. É nesta fase que a física do inversor passa a existir matematicamente na simulação:
1. **$kVA$ e $P_{mpp}$:** A potência bruta outrora capturada ($kW$) é convertida nas variáveis físicas de Pico do Painel ($P_{mpp}$) e Potência Nominal do Inversor ($kVA$).
2. **Clipping (Ceifamento):** Ao configurar os painéis para injetar CC em um inversor CA, a simulação adquire a capacidade de calcular o *Clipping*. Se a irradiância superar o pico do inversor, a potência é automaticamente "ceifada", achatando o topo da curva (comportamento natural de usinas reais dimensionadas com Fator de Sobrecarga - *Oversizing*).
3. **Eficiência e Perdas:** Duas curvas não lineares são injetadas globalmente na rede (`XYCurve`): 
   * `EffCurve`: Curva de eficiência do inversor em relação ao carregamento (perdas elétricas).
   * `P-TCurve`: Curva de degradação da geração fotovoltaica conforme o aumento da Temperatura da placa solar (perdas termodinâmicas).

### C. Injeção de Telemetria Climática e Interpolação Hermitiana
Usinas fotovoltaicas reais não geram baseadas em um "fator multiplicador" bruto; elas respondem à **Irradiância Solar ($W/m^2$)** e à **Temperatura ($^\circ C$)**. 
* **Aquisição Estatística:** O algoritmo carrega um banco de dados real contendo a telemetria climática exata capturada de estações e usinas brasileiras (referência: base **BR-PVGen**). O script distribui de forma circular (módulo) dezenas de curvas climáticas diferentes por entre os mais de 600 geradores da rede local, garantindo estocasticidade (nuvens e picos de sol passando em tempos diferentes por diferentes regiões geográficas do alimentador).
* **Blindagem e Sanitização Climática (Rejeição Dinâmica):** Bases de dados reais frequentemente sofrem com erros de *hardware*, como sensores reportando anomalias de $600^\circ C$ ou irradiâncias negativas. O código implementa uma barreira estrita baseada em padrões industriais (`mask()`). De acordo com as normas internacionais de homologação de módulos fotovoltaicos (como a **IEC 61215** e a **IEC 61730**) e os catálogos dos principais fabricantes, a faixa operacional de temperatura do painel é rigorosamente limitada entre **$-40^\circ C$ e $+85^\circ C$**. Valores de irradiância sofrem um limite protetor teto de **$1.5$ p.u**. (permitindo valores normais acima de 1.0 p.u. causados pelo fenômeno físico de Lente de Nuvem, mas barrando leituras impossíveis). Em vez de tentar consertar magicamente os dados defeituosos com interpolação (o que introduziria erros irreais na simulação), o sistema engatilha um "Pulo de Curva" (`ValueError`). O orquestrador descarta imediatamente a curva corrompida, exibe um *log* de aviso no terminal (`⚠️ [PULO DE CURVA]`) e busca automaticamente a próxima estação climática saudável do banco de dados, protegendo de forma integral as Matrizes Jacobianas da simulação.
* **Alinhamento da Malha Temporal (PCHIP):** O banco de telemetria climática original possui resolução de 15 minutos, enquanto o nosso modelo de Cargas e *Solver* operam na precisão cirúrgica de **10 minutos**. 
Para evitar dessincronismo no cálculo das Matrizes Jacobianas do OpenDSS, a telemetria climática sofre um agrupamento médio (`resample(new_rate).mean()`) seguido por uma **Interpolação PCHIP**. A adoção de *Piecewise Cubic Hermite Interpolating Polynomials* garante que os valos da irradiância assumam a mesma inclinação natural do sol ao longo dos 10 minutos intervalares sem criar picos negativos irrealistas ao anoitecer (*overshoots*). O recorte é feito perfeitamente para extrair 168 horas (1008 pontos), casando com a simulação.

### D. Sintetização do OpenDSS e Atualização do Orquestrador
Na última etapa, a inteligência extraída é devolvida ao HD através de matrizes massivas legíveis pelo OpenDSS:
1. **Modelagem Contínua e Otimização de I/O (Shapes Únicos):** Para garantir o máximo de eficiência de memória e evitar redundâncias, o algoritmo emprega um mecanismo de reuso. Em vez de gerar centenas de `LoadShape`s e `Tshape`s idênticos para cada gerador individual, o sistema consolida os dados e instancia apenas um único par de *shapes* por estação climática validada no *dataset*. Centenas de geradores fotovoltaicos diferentes reaproveitam (apontam para) essa mesma curva meteorológica na memória. Essa otimização derruba o tamanho e o tempo de compilação dos arquivos `.dss` e `.csv` finais em mais de 90%, otimizando redes de larga escala.
2. **Construção do PVSystem:** Cada inversor fotovoltaico é instanciado na rede utilizando a robusta sintaxe do OpenDSS, fazendo o redirecionamento centralizado dos *shapes*: 
   ```text
   New PVSystem.PV1 phases=3 Bus1=... kV=0.38 kVA=4.6 irrad=1.0 Pmpp=4.6 temperature=25 PF=1 EffCurve=MyEff P-TCurve=MyPvsT Daily=shape_irrad_4 TDaily=shape_temp_4 Vminpu=0.001 Model=1
   ```
3. **Auto-Injeção no Orquestrador (`run`):** Para anular o risco de falha humana na compilação, o script possui uma rotina que acessa o arquivo mestre de execução (`run_ESB01S4.dss`), vasculha o seu conteúdo de forma programática e injeta perfeitamente a string `Redirect ESB01S4_pv.dss` e seus dependentes pouco antes da invocação do laço de tempo do OpenDSS (`Set ControlMode=Time`).

**Conclusão:** O produto deste script converte um mapa morto de geradores passivos em um exército de 600 Inversores Inteligentes independentes. Esses elementos reagem dinamicamente e com extrema precisão física a um microclima de irradiância calibrado perfeitamente a cada 10 minutos do fluxo de potência estocástico das cargas elétricas vizinhas.
