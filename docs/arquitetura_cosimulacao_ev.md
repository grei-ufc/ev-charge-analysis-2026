# Documentação Técnica: Integração de VEs na Co-Simulação (Mosaik + OpenDSS)

Este documento descreve a engenharia de software e a topologia de controle desenvolvida para integrar as curvas de carregamento estocástico de Veículos Elétricos (VEs) no ambiente de co-simulação dinâmica Mosaik.

Diferente do fluxo tradicional onde o OpenDSS lê curvas estáticas internamente (`.dss`), a arquitetura implementada transfere o controle físico e temporal dos VEs para o orquestrador do Mosaik.

---

## 1. O Motor Ciberfísico: `ev_charger_simulator.py`
Para representar fielmente o comportamento elétrico de um carregador, foi criado um microserviço nativo do Mosaik (`src/simulators/ev/ev_charger_simulator.py`). Ele atua como uma camada tradutora entre os dados puros (0 a 1) e as grandezas elétricas reais (kW e kvar).

### 1.1 Parâmetros e Estados
* **Parâmetros Construtivos (Params):** Ao ser instanciado no cenário, o carregador recebe sua potência nominal (`charger_capacity_kw`, ex: 7.2 kW) e seu fator de potência (`power_factor`).
* **Sinal de Controle (Inputs):** A cada passo da simulação (ex: a cada 10 min), ele recebe o `normalized_power` vindo do simulador CSV.
* **Sinal Elétrico (Outputs):** Através do método `calculate_step()`, a potência real injetada/consumida é calculada.

### 1.2 Modelagem Matemática (Triângulo de Potências)
O carregador converte o fator de demanda em Potência Ativa ($P$) e Reativa ($Q$):
1. **Ativa:** $P = normalized\_power \times charger\_capacity\_kw$
2. **Reativa:** $Q = P \times \tan(\arccos(power\_factor))$

*Nota: Foi implementada uma trava de segurança trigonométrica limitando o fator de potência entre -1.0 e 1.0 para evitar falhas de tempo de execução.*

---

## 2. Abertura de Portas no Simulador OpenDSS (`element_specs.py`)

No ecossistema OpenDSS/Mosaik padrão, os elementos de carga (`Load`) são entidades "fechadas" que seguem o fluxo de carga estático nativo do motor do OpenDSS. Para permitir o controle externo sem alterar o código-fonte C++ do simulador elétrico, interviemos no *Wrapper* em Python.

### 2.1 A Função Escritora (`write_load`)
Foi desenvolvida uma função customizada injetada na camada de tradução do `element_specs.py` do OpenDSS:
```python
def write_load(sim, name: str, values: dict[str, Any]) -> None:
    if "P_kw" in values or "Q_kvar" in values:
        sim.dss_wrapper.set_power(name, p=values.get("P_kw"), q=values.get("Q_kvar"), element="Load")
```
Isso permite que qualquer sinal de $P$ ou $Q$ enviado pelo Mosaik atinja a API COM do OpenDSS e sobrescreva momentaneamente o estado daquela carga elétrica.

### 2.2 Exposição do Contrato (ModelSpec)
O elemento `Load` teve seu escopo alterado de um elemento puramente passivo (`reader`) para um elemento ativo bidirecional (`public=True`).
As portas `P_kw` e `Q_kvar` foram oficialmente adicionadas como **Inputs** no Mosaik, dizendo ao orquestrador que cabos virtuais agora podem ser conectados diretamente às cargas da rede de distribuição.

---

## 3. O Fluxo de Dados Completo (Data Pipeline)

A conexão do sistema durante uma simulação em tempo real (Runtime) flui da seguinte maneira:

1. **Simulador CSV:** Lê o arquivo `ev_loadshapes_normalized.csv` (onde valores normais chegam a 1.0, e sobreposições estocásticas atingem picos de 2.0 ou 3.0). Envia esse fator via rede local.
2. **Simulador de VE (`ev-charger` porta 5781):** Recebe o sinal. Se o carregador tiver 7.2 kW, e receber um sinal de 2.0 (overlap), ele calcula $P = 14.4$ kW. Envia os resultados via rede.
3. **Simulador OpenDSS (`opendss` porta 5771):** Recebe $P = 14.4$ kW e $Q = 0.0$ kvar em suas portas de input recém-criadas. Atualiza a Carga representante do carro na topologia, resolve a matriz de admitância (Fluxo de Carga) e expõe a queda de tensão resultante.
