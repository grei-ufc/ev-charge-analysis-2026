import mosaik_api_v3
import math

# ==============================================================================
# 1. MOTOR FÍSICO DO CARREGADOR (EV Charger Physical Model)
# ==============================================================================
# Esta classe é pura matemática de Engenharia Elétrica. Ela não sabe que o Mosaik
# existe. O papel dela é pegar uma curva de dados p.u. (0 a 1) e converter em
# Potência Ativa (kW) e Reativa (kvar) para injeção no simulador elétrico.
# ==============================================================================
class EVChargerModel:
    """
    Emula o comportamento elétrico de um posto de carregamento de Veículo Elétrico.
    """

    def __init__(self, charger_capacity_kw: float, power_factor: float) -> None:
        # --- PARÂMETROS CONSTRUTIVOS (Fixos de Fábrica) ---
        # charger_capacity_kw: Potência ativa nominal máxima do carregador (ex: 3.6 ou 7.2 kW)
        self.charger_capacity_kw = charger_capacity_kw
        
        # power_factor: Fator de potência (normalmente entre 0.98 e 1.0 para VEs)
        self.power_factor = power_factor

        # --- VARIÁVEIS DE ESTADO (Variam a cada passo de tempo) ---
        # normalized_power (INPUT): Valor lido do CSV (0.0 = ocioso, 1.0 = carregando, 2.0 = sobreposição)
        self.normalized_power = 0.0
        
        # P_kw e Q_kvar (OUTPUTS): Potências reais injetadas/consumidas da rede
        self.P_kw = 0.0
        self.Q_kvar = 0.0

    def calculate_step(self) -> None:
        """
        Executado a cada passo de tempo para atualizar os valores de P e Q daquele instante.
        """
        # 1. Cálculo da Potência Ativa (P)
        # Transforma a curva estocástica do CSV em potência real (kW)
        self.P_kw = self.normalized_power * self.charger_capacity_kw

        # 2. Cálculo da Potência Reativa (Q) via Triângulo de Potências
        # Garante que só calcula reativo se o carro estiver puxando energia
        if self.power_factor > 0 and self.P_kw > 0:
            # Trava o Fator de Potência matematicamente entre -1.0 e 1.0 para evitar crash de software
            pf = min(1.0, max(-1.0, self.power_factor))
            
            # Descobre o ângulo (Teta) da corrente fazendo o arco-cosseno do fator de potência
            angle_rad = math.acos(pf)
            
            # Equação da potência reativa: Q = P * tangente(Teta)
            self.Q_kvar = self.P_kw * math.tan(angle_rad)
        else:
            self.Q_kvar = 0.0


# ==============================================================================
# 2. CONTRATO DE COMUNICAÇÃO COM O MOSAIK (META)
# ==============================================================================
# Este dicionário é o "cartão de visitas" do simulador. Ele ensina o orquestrador
# do Mosaik sobre como interagir com este microserviço.
# ==============================================================================
META = {
    "api_version": "3.0",          # Versão da API do Mosaik
    "type": "time-based",          # Indica que caminha em sincronia com o relógio central
    "models": {
        "EVCharger": {
            "public": True,
            # params: Informações estáticas exigidas na hora de "instalar" o carregador
            "params": ["charger_capacity_kw", "power_factor", "bus_name"],
            
            # attrs: Variáveis vivas. Podem receber sinais (inputs) e enviar cálculos (outputs)
            "attrs": ["normalized_power", "P_kw", "Q_kvar"],
        },
    },
}


# ==============================================================================
# 3. INTERFACE DE CO-SIMULAÇÃO (Mosaik Wrapper)
# ==============================================================================
# Esta classe herda do Mosaik e serve como "tradutora". Ela lê comandos da rede
# de co-simulação, alimenta o Motor Físico (EVChargerModel) e devolve os cálculos.
# ==============================================================================
class EVChargerSim(mosaik_api_v3.Simulator):

    def __init__(self) -> None:
        super().__init__(META)
        # Dicionário para armazenar todas as instâncias de carregadores criadas na simulação
        self.entities = {}  
        self.step_size = 1

    def init(self, sid, time_resolution=1.0, step_size=1.0):
        # Chamado uma vez no início para ajustar o tamanho do passo temporal
        self.step_size = int(step_size)
        return self.meta

    def create(self, num, model, **model_params):
        """
        Gera os objetos físicos. Se o cenário pedir 50 carregadores, roda 50 vezes.
        """
        entities = []
        for i in range(num):
            # Formatação do nome (ID) do equipamento na simulação
            bus_name = model_params.get("bus_name", "")
            bus_suffix = f"_bus{bus_name}" if bus_name else ""
            eid = f"{model}_{len(self.entities) + i}{bus_suffix}"
            
            # Instancia o Motor Físico do carregador puxando os parâmetros fornecidos pelo cenário
            charger_model = EVChargerModel(
                charger_capacity_kw=model_params.get("charger_capacity_kw", 7.2),
                power_factor=model_params.get("power_factor", 1.0)
            )

            # Salva o motor físico no dicionário e retorna o ID criado para o orquestrador
            self.entities[eid] = charger_model
            entities.append({"eid": eid, "type": model})

        return entities

    def step(self, time, inputs, max_advance):
        """
        Loop dinâmico chamado a cada passo de tempo (ex: a cada 10 minutos simulados).
        """
        # PASSO 1: Atualizar Entradas (Inputs)
        # O Mosaik traz os valores do Simulador CSV. Extraímos e injetamos na variável normalized_power.
        for eid, attrs in inputs.items():
            charger = self.entities[eid]
            
            if "normalized_power" in attrs:
                # O Mosaik envia os dados num dicionário aninhado, a função 'next(iter(...))' puxa o valor puro
                charger.normalized_power = float(next(iter(attrs["normalized_power"].values())))

        # PASSO 2: Rodar a Matemática
        # Manda cada um dos carregadores calcular P_kw e Q_kvar com base no input que acabou de receber
        for _eid, charger in self.entities.items():
            charger.calculate_step()

        # Avança o relógio interno do simulador
        return time + self.step_size

    def get_data(self, outputs):
        """
        Função de requisição de dados. Imediatamente após o "step", o Mosaik liga
        pedindo os resultados (P_kw, Q_kvar) para enviar para a rede elétrica (OpenDSS).
        """
        data = {}
        for eid, attrs in outputs.items():
            charger = self.entities[eid]
            data[eid] = {}
            for attr in attrs:
                if hasattr(charger, attr):
                    # Empacota os valores calculados (P, Q) num dicionário estruturado
                    data[eid][attr] = getattr(charger, attr)
        return data


# ==============================================================================
# INICIALIZAÇÃO DO MICROSERVIÇO (DOCKER)
# ==============================================================================
if __name__ == "__main__":
    # Mantém o simulador ativo na porta TCP, escutando comandos do Orquestrador Mosaik
    mosaik_api_v3.start_simulation(EVChargerSim())
