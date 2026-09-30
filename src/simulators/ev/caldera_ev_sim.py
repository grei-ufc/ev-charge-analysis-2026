import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import mosaik_api_v3

# Garante a importação do CalderaWrapper local
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from caldera_wrapper import CalderaWrapper

PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
DEFAULT_SESSIONS_CSV = (
    PROJECT_ROOT / "data" / "datasets" / "veiculos-eletricos" / "ev_sessions_caldera.csv"
)

META = {
    "type": "time-based",
    "models": {
        "CalderaEV": {
            "public": True,
            "params": [
                "profile_name",  # Ex: User_12_semana_1_7p2kW
                "csv_path",      # Opcional: Caminho para ev_sessions_caldera.csv
            ],
            "attrs": [
                "P_kw",          # Potência Ativa demandada da rede AC (kW)
                "Q_kvar",        # Potência Reativa (kVAr)
                "is_charging",   # Status booleano indicando recarga ativa
            ],
        },
    },
}


class CalderaEVModel:
    """
    Representação física de uma entidade de Veículo Elétrico na co-simulação.
    Armazena a série temporal pré-calculada de recarga (10.080 minutos) com base
    nas físicas de bateria, inversores e tapering do Caldera ICM (C++).
    """

    def __init__(self, eid: str, profile_name: str, power_series: np.ndarray):
        self.eid = eid
        self.profile_name = profile_name
        self.power_series = power_series  # Array de 10080 minutos
        self.total_minutes = len(power_series)

        # Estados dinâmicos expostos ao Mosaik
        self.P_kw = 0.0
        self.Q_kvar = 0.0
        self.is_charging = False

    def update_step(self, current_minute: int):
        # Trata repetições cíclicas de semana se a simulação passar de 7 dias
        idx = current_minute % self.total_minutes
        self.P_kw = float(self.power_series[idx])
        self.Q_kvar = 0.0  # FP unitário padrão nas Wallboxes residenciais AC
        self.is_charging = self.P_kw > 0.05


class CalderaEVSim(mosaik_api_v3.Simulator):
    """
    Simulador Mosaik para Veículos Elétricos com motor físico Caldera ICM.
    """

    def __init__(self):
        super().__init__(META)
        self.sid = None
        self.step_size = None
        self.entities: Dict[str, CalderaEVModel] = {}
        self.wrapper: CalderaWrapper = None
        self.events_df: pd.DataFrame = None

    def init(self, sid, time_resolution=1.0, step_size=600, inputs_dir=None, **kwargs):
        self.sid = sid
        self.step_size = step_size

        # Inicializa o motor físico do C++
        self.wrapper = CalderaWrapper(inputs_dir=inputs_dir)
        return self.meta

    def create(self, num, model, **model_params):
        if model != "CalderaEV":
            raise ValueError(f"Modelo desconhecido: {model}. Esperado: 'CalderaEV'")

        # Carrega o CSV de sessões físicas na primeira chamada
        if self.events_df is None:
            csv_path = model_params.get("csv_path", DEFAULT_SESSIONS_CSV)
            if not Path(csv_path).exists():
                raise FileNotFoundError(f"Arquivo de sessões não encontrado em: {csv_path}")
            self.events_df = pd.read_csv(csv_path)

        entities_info = []

        for i in range(num):
            eid = f"{model}_{len(self.entities) + i}"
            profile_name = model_params.get("profile_name")

            if not profile_name:
                raise ValueError(f"Parâmetro obrigatório 'profile_name' ausente para {eid}")

            # Filtra todas as sessões de recarga desta curva/usuário
            df_perfil = self.events_df[self.events_df["Profile_Name"] == profile_name]

            # Vetor de 7 dias * 24 horas * 60 minutos = 10.080 minutos
            power_series = np.zeros(10080, dtype=np.float64)

            # Para cada sessão do perfil, calcula a física exata do Caldera
            for _, sessao in df_perfil.iterrows():
                start_min = int(sessao["Start_Min"])
                end_min = int(sessao["End_Min"])
                soc_in = float(sessao["Initial_SoC"])
                soc_out = float(sessao["Target_SoC"])
                modelo_veiculo = str(sessao.get("Modelo_Veiculo", "BYD DOLPHIN MINI GS5EV"))

                # Consulta a física do C++ com tapering CC/CV e eficiência de inversor
                curva_p = self.wrapper.get_charge_profile(
                    vehicle_model=modelo_veiculo,
                    initial_soc=soc_in,
                    target_soc=soc_out,
                )

                duracao_fisica = len(curva_p)
                duracao_sessao = max(1, end_min - start_min)

                # Preenche a série temporal
                # Se o carro completou a recarga antes de desempilhar (t_idle > 0), a potência vai a zero
                for m_rel in range(duracao_sessao):
                    min_abs = start_min + m_rel
                    if min_abs < 10080:
                        if m_rel < duracao_fisica:
                            power_series[min_abs] = curva_p[m_rel]
                        else:
                            power_series[min_abs] = 0.0  # Concluído e ocioso na tomada

            # Instancia o modelo da entidade
            ev_model = CalderaEVModel(eid, profile_name, power_series)
            self.entities[eid] = ev_model
            entities_info.append({"eid": eid, "type": model})

        return entities_info

    def step(self, time, inputs, max_advance):
        # time é dado em segundos pelo Mosaik
        current_minute = int(time // 60)

        for _eid, ev_model in self.entities.items():
            ev_model.update_step(current_minute)

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            ev_model = self.entities[eid]
            data[eid] = {}
            for attr in attrs:
                if hasattr(ev_model, attr):
                    data[eid][attr] = getattr(ev_model, attr)
        return data


def main():
    return mosaik_api_v3.start_simulation(CalderaEVSim())


if __name__ == "__main__":
    main()

