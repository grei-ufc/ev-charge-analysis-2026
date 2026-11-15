#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conversão de Geradores Distribuídos da BDGD em Elementos PVSystem no OpenDSS
=============================================================================

Converte os geradores de micro e minigeração distribuída fotovoltaica (GD-FV)
oriundos da Base de Dados Geográfica da Distribuidora (BDGD) em elementos dinâmicos
PVSystem no OpenDSS, compatibilizando níveis de tensão, conexões de enrolamento
e séries temporais de irradiância e temperatura com interpolação PCHIP.
"""

import os
import re
import sys
import pandas as pd
import pyogrio
from pathlib import Path
from math import ceil

# ==============================================================================
# CONFIGURAÇÕES DE DIRETÓRIOS E SIMULAÇÃO
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parents[3]
DADOS_REDE_DIR = BASE_DIR.parent / "dados" / "dados-da-rede"
GDB_PATH = DADOS_REDE_DIR / "Enel_CE_39_2024-12-31_V11_20250822-1151.gdb"
GDB_ZIP_PATH = DADOS_REDE_DIR / "Enel_CE_39_2024-12-31_V11_20250822-1151.gdb.zip"
METADATA_CSV = BASE_DIR / "data" / "datasets" / "geradores-fv" / "power_station_metadata.csv"
SOLAR_DIR = BASE_DIR / "data" / "datasets" / "geradores-fv" / "solar_station"

STEP = '10min'
DIAS = 7
T_SIMULATION_MIN = DIAS * 24 * 60
NPTS_ORIGIN = ceil(T_SIMULATION_MIN / 15)
START_DATE = "2024-09-09 00:00:00"

# Mapeamento de barras que fisicamente possuem apenas 1 fase + neutro na rede BT (evita nós flutuantes)
BARRAS_MONOFASICAS_BT = {
    "3866974338468827": "3866974338468827.3.4",
    "3858807938464405": "3858807938464405.1.4",
    "3857601938460002": "3857601938460002.1.4",
    "3858371138460380": "3858371138460380.1.4",
    "3857773338459146": "3857773338459146.1.4",
    "3856380038463820": "3856380038463820.1.4",
    "3866354038468928": "3866354038468928.1.4",
    "3859103838474718": "3859103838474718.1.4",
    "3872701038464502": "3872701038464502.1.4",
    "3857881438458524": "3857881438458524.1.4",
    "3858218938460615": "3858218938460615.1.4",
    "3857343438464427": "3857343438464427.1.4",
    "3858922838474457": "3858922838474457.3.4",
    "3873424138463998": "3873424138463998.1.4",
    "3862115538458927": "3862115538458927.1.4",
    "3876796438462655": "3876796438462655.3.4",
    "3873369138464025": "3873369138464025.1.4",
    "3873397138464000": "3873397138464000.1.4",
    "3859057838459073": "3859057838459073.1.4",
    "3857411438459173": "3857411438459173.1.4",
    "3872644238464508": "3872644238464508.1.4",
}

# ==============================================================================
# CONSULTA CADASTRAL (BDGD) E EXTRAÇÃO
# ==============================================================================
def _resolver_caminho_gdb() -> str:
    """Resolve o caminho do Geodatabase BDGD (diretório local ou fallback via /vsizip/)."""
    if GDB_PATH.exists():
        return str(GDB_PATH)
    if GDB_ZIP_PATH.exists():
        return f"/vsizip/{GDB_ZIP_PATH.as_posix()}/{GDB_PATH.name}"
    raise FileNotFoundError(
        f"Base BDGD não encontrada em {GDB_PATH} nem em {GDB_ZIP_PATH}."
    )


def carregar_situacao_gds_bdgd(alimentador: str) -> dict[str, dict]:
    """Consulta a situação de ativação (SIT_ATIV) das UGs em UGBT_tab e UGMT_tab."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", alimentador):
        raise ValueError(f"Identificador de alimentador inválido: {alimentador!r}")

    gdb_source = _resolver_caminho_gdb()
    situacao_por_ceg: dict[str, dict] = {}

    # CTMT precisa constar em columns para que o filtro where funcione no pyogrio/GDAL.
    for camada in ("UGBT_tab", "UGMT_tab"):
        df = pyogrio.read_dataframe(
            gdb_source,
            layer=camada,
            columns=["CEG_GD", "CTMT", "SIT_ATIV", "POT_INST"],
            where=f"CTMT = '{alimentador}'",
            read_geometry=False,
        )
        for row in df.itertuples(index=False):
            ceg = str(row.CEG_GD).strip().upper()
            sit_ativ = str(row.SIT_ATIV).strip().upper() if pd.notna(row.SIT_ATIV) else ""
            pot_inst = float(row.POT_INST) if pd.notna(row.POT_INST) else 0.0
            situacao_por_ceg[ceg] = {
                "ceg_gd": str(row.CEG_GD).strip(),
                "sit_ativ": sit_ativ,
                "pot_inst": pot_inst,
                "camada": camada,
            }

    return situacao_por_ceg


def extrair_geradores(dss_file: Path, sit_ativ_map: dict[str, dict] | None = None):
    """Extrai parâmetros elétricos dos geradores definidos no arquivo DSS da BDGD.

    Filtra unidades desativadas (SIT_ATIV != 'AT') quando ``sit_ativ_map`` é
    fornecido e corrige fases, tensão nominal e tipo de ligação dos elementos ativos.
    """
    geradores = []
    desativados = []
    nao_encontrados = []
    if not dss_file.exists():
        return geradores, desativados, nao_encontrados

    with open(dss_file, 'r', encoding='utf-8', errors='ignore') as f:
        for linha in f:
            if not linha.strip().lower().startswith('new "generator.'):
                continue

            m_nome = re.search(r'new\s+"generator\.([^"]+)"', linha, re.IGNORECASE)
            m_phases = re.search(r'phases=(\d+)', linha, re.IGNORECASE)
            m_bus = re.search(r'bus1=([^\s]+)', linha, re.IGNORECASE)
            m_kv = re.search(r'kv=([\d\.]+)', linha, re.IGNORECASE)
            m_kw = re.search(r'kw=([\d\.]+)', linha, re.IGNORECASE)
            m_conn = re.search(r'conn=([^\s]+)', linha, re.IGNORECASE)

            if m_phases and m_bus and m_kv and m_kw:
                nome_gd = m_nome.group(1).strip() if m_nome else ""
                phases = int(m_phases.group(1))
                bus = m_bus.group(1)
                kv = float(m_kv.group(1))
                kw = float(m_kw.group(1))
                conn = m_conn.group(1).capitalize() if m_conn else ("Delta" if phases >= 3 else "Wye")

                # Saneamento cadastral: descarta GDs desativadas (SIT_ATIV != 'AT') pareando por CEG_GD
                if sit_ativ_map is not None:
                    info_bdgd = sit_ativ_map.get(nome_gd.upper())
                    if info_bdgd is None:
                        nao_encontrados.append(nome_gd)
                    elif info_bdgd["sit_ativ"] != "AT":
                        desativados.append({
                            "nome": nome_gd,
                            "sit_ativ": info_bdgd["sit_ativ"],
                            "bus": bus,
                            "phases": phases,
                            "kw": kw,
                            "linha_dss": linha.strip(),
                        })
                        continue

                # Checagem de nós flutuantes em barras monofásicas BT
                bus_base = bus.split('.')[0]
                if bus_base in BARRAS_MONOFASICAS_BT:
                    phases = 1
                    bus = BARRAS_MONOFASICAS_BT[bus_base]
                    kv = 0.22
                    conn = "Wye"
                else:
                    # Correção de Topologia: Geradores trifásicos em rede 380/220V com kv=0.22 devem ser kv=0.38
                    if phases >= 2 and abs(kv - 0.22) < 0.05:
                        kv = 0.38

                geradores.append({
                    'PV_nome_gd': nome_gd,
                    'PV_phases': phases,
                    'PV_bus': bus,
                    'PV_conn': conn,
                    'PV_kv': kv,
                    'PV_kva': kw
                })
    return geradores, desativados, nao_encontrados

# ==============================================================================
# CLASSE DE GERAÇÃO
# ==============================================================================
class PVGenerator:
    """Modela e processa parâmetros elétricos e séries temporais climáticas para elementos PVSystem."""
    _solar_cache = {}

    def __init__(self, PV_id, PV_phases, PV_bus, PV_kv, PV_kva, PV_curve_id, PV_list, PV_conn="Delta", start=96):
        self.curve_id = PV_curve_id
        self.curve = PV_list.iloc[self.curve_id - 1]['id']
        self.FILE_CSV = self.curve + '.csv'
        self.SOLAR_STATION_FILE = SOLAR_DIR / self.FILE_CSV

        if self.FILE_CSV not in PVGenerator._solar_cache:
            PVGenerator._solar_cache[self.FILE_CSV] = pd.read_csv(self.SOLAR_STATION_FILE)
        
        self.solar_station_curves = PVGenerator._solar_cache[self.FILE_CSV].copy()
        
        self.name = f'PV{PV_id}'
        self.phases = PV_phases
        self.bus = PV_bus
        self.conn = PV_conn
        self.kv = PV_kv
        self.kva = PV_kva
        
        self.irrad = 1000
        self.pmpp = self.kva
        self.temperature = 25
        self.pf = 1
        self.vminpu = 0.80
        self.vmaxpu = 1.20
        self.model = 1

        self.effcurve = 'New XYCurve.MyEff npts=4 xarray=[0.1, 0.2, 0.4, 1.0] yarray=[0.86, 0.90, 0.93, 0.97]'
        self.ptcurve = 'New XYCurve.MyPvsT npts=4 xarray=[0, 25, 75, 100] yarray=[1.2, 1.0, 0.8, 0.6]'

        self.npts = NPTS_ORIGIN
        data_slice = slice(start, self.npts + start + 1)
        
        self.irrad_curve = (self.solar_station_curves['poa_irradiance_wm2'].iloc[data_slice] / self.irrad).reset_index(drop=True)
        
        # 1. Validação física da irradiância solar no plano do arranjo (POA):
        # Elimina valores negativos decorrentes de desvio térmico noturno dos sensores (piranômetros).
        self.irrad_curve = self.irrad_curve.clip(lower=0)
        
        # Verifica consistência física de pico (teto de 1,5 pu considerando amplificação por borda de nuvem).
        if (self.irrad_curve > 1.5).any():
            max_val = self.irrad_curve.max()
            raise ValueError(f"Irradiância inconsistente (Pico: {max_val:.2f} p.u.) na série {self.FILE_CSV}.")
        
        # Interpolação linear de leituras faltantes (NaN)
        self.irrad_curve = self.irrad_curve.interpolate(method='linear').fillna(0)
        self.irrad_curve.name = f'my_shape{PV_id}_irrad'

        self.temperature_curve = self.solar_station_curves['panel_temperature_celsius'].iloc[data_slice].reset_index(drop=True)
        
        # 2. Validação da temperatura operacional do módulo (IEC 61215: -40°C a +85°C)
        if (self.temperature_curve < -40).any() or (self.temperature_curve > 85).any():
            min_val = self.temperature_curve.min()
            max_val = self.temperature_curve.max()
            raise ValueError(f"Temperatura fora dos limites de operação ({min_val:.1f}°C a {max_val:.1f}°C) na série {self.FILE_CSV}.")
        
        # Interpolação linear de leituras faltantes em temperatura
        self.temperature_curve = self.temperature_curve.interpolate(method='linear').fillna(25)
        self.temperature_curve.name = f'my_shape{PV_id}_temperature'

        self.datetime = pd.to_datetime(self.solar_station_curves['datetime'].iloc[data_slice]).reset_index(drop=True)

        self.irrad_curve = pd.concat([self.datetime, self.irrad_curve], axis=1).set_index('datetime')
        self.temperature_curve = pd.concat([self.datetime, self.temperature_curve], axis=1).set_index('datetime')

    def CurvePCHIPInterpolation(self, new_rate=STEP, start_date=START_DATE):
        base_delta = pd.Timedelta('15min')
        new_delta = pd.Timedelta(new_rate)
        expected_points = ceil(self.npts * (base_delta / new_delta))

        irrad_res = self.irrad_curve.resample(new_rate).mean()
        temp_res = self.temperature_curve.resample(new_rate).mean()
        
        # PCHIP
        self.irrad_curve = irrad_res.reset_index(drop=True).interpolate(method='pchip').round(6)
        self.temperature_curve = temp_res.reset_index(drop=True).interpolate(method='pchip').round(6)
        
        self.irrad_curve = self.irrad_curve.iloc[:expected_points]
        self.temperature_curve = self.temperature_curve.iloc[:expected_points]

        new_timeline = pd.date_range(start=start_date, periods=expected_points, freq=new_rate)
        
        self.irrad_curve.index = new_timeline
        self.temperature_curve.index = new_timeline

        self.irrad_curve = self.irrad_curve.reset_index().rename(columns={'index': 'Date'})
        self.temperature_curve = self.temperature_curve.reset_index().rename(columns={'index': 'Date'})

    @staticmethod
    def GenerateCSV(PVGen, out_irrad, out_temp):
        if not PVGen: return
        
        # Filtra para armazenar e exportar apenas as curvas únicas (otimização de tamanho)
        unique_pvs = {}
        for pv in PVGen:
            if pv.curve_id not in unique_pvs:
                unique_pvs[pv.curve_id] = pv
                
        unique_pv_list = list(unique_pvs.values())
        
        # Monta a lista de irradiância (Primeira coluna = Data)
        irrad_list = [unique_pv_list[0].irrad_curve.iloc[:, 0]]
        for pv in unique_pv_list:
            col = pv.irrad_curve.iloc[:, 1].copy()
            col.name = f"shape_irrad_{pv.curve_id}"
            irrad_list.append(col)
            
        # Monta a lista de temperatura
        temp_list = [unique_pv_list[0].temperature_curve.iloc[:, 0]]
        for pv in unique_pv_list:
            col = pv.temperature_curve.iloc[:, 1].copy()
            col.name = f"shape_temp_{pv.curve_id}"
            temp_list.append(col)

        pd.concat(irrad_list, axis=1).to_csv(out_irrad, index=False)
        pd.concat(temp_list, axis=1).to_csv(out_temp, index=False)
        print(f"Arquivos CSV de irradiância e temperatura gerados: {out_irrad.name} e {out_temp.name}")

    @staticmethod
    def GenerateDSS(PVGen, out_dss):
        if not PVGen: return
        dss_lines = []
        irrad_shape_lines = []
        temp_shape_lines = []

        npts = len(PVGen[0].irrad_curve)
        try:
            delta = PVGen[0].irrad_curve['Date'].iloc[1] - PVGen[0].irrad_curve['Date'].iloc[0]
            minterval = delta.total_seconds() / 60.0
        except Exception:
            minterval = 10
            
        irrad_shape_file_name = out_dss.with_name(out_dss.stem + "_irrad_shapes.dss")
        temp_shape_file_name = out_dss.with_name(out_dss.stem + "_temp_shapes.dss")

        processed_curves = set()

        for pv in PVGen:
            pv_id = pv.name.replace('PV', '')
            c_id = pv.curve_id
            
            # Registra curvas de carga apenas uma vez no arquivo DSS
            if c_id not in processed_curves:
                irrad_mults = pv.irrad_curve.iloc[:, 1].tolist()
                temp_mults = pv.temperature_curve.iloc[:, 1].tolist()
                
                irrad_str = " ".join([f"{x:.4f}" for x in irrad_mults])
                temp_str = " ".join([f"{x:.4f}" for x in temp_mults])
                
                irrad_shape_lines.append(f"New LoadShape.shape_irrad_{c_id} npts={npts} minterval={minterval} mult=[{irrad_str}]")
                temp_shape_lines.append(f"New Tshape.shape_temp_{c_id} npts={npts} minterval={minterval} temp=[{temp_str}]")
                
                processed_curves.add(c_id)
            
            pv_command = (
                f"New PVSystem.{pv.name} phases={pv.phases} conn={pv.conn} Bus1={pv.bus} "
                f"kV={pv.kv} kVA={pv.kva} irrad={pv.irrad/1000} Pmpp={pv.pmpp}\n"
                f"~ temperature={pv.temperature} PF={pv.pf} EffCurve=MyEff P-TCurve=MyPvsT\n"
                f"~ Daily=shape_irrad_{c_id} TDaily=shape_temp_{c_id}\n"
                f"~ Model={pv.model} Vminpu={pv.vminpu} Vmaxpu={pv.vmaxpu}\n"
            )
            dss_lines.append(pv_command)

        dss_lines.insert(0, f"Redirect {irrad_shape_file_name.name}\n")
        dss_lines.insert(1, f"Redirect {temp_shape_file_name.name}\n")
        dss_lines.insert(2, f"{PVGen[0].ptcurve}")
        dss_lines.insert(3, f"{PVGen[0].effcurve}\n")

        with open(irrad_shape_file_name, "w") as f:
            f.write("\n".join(irrad_shape_lines))
        with open(temp_shape_file_name, "w") as f:
            f.write("\n".join(temp_shape_lines))
        with open(out_dss, "w") as f:
            f.write("\n".join(dss_lines))
            
        print(f"Arquivo DSS gerado com comandos PVSystem e curvas: {out_dss.name}")

# ==============================================================================
# PROCESSAMENTO DE GERADORES DISTRIBUÍDOS
# ==============================================================================
def processar_gds(alimentador: str):
    """Lê os arquivos DSS de GD, filtra SIT_ATIV == 'AT' e gera os PVSystems correspondentes."""
    pasta_ajustada = BASE_DIR / "data" / "rede" / f"{alimentador}"

    # 1. Consulta situação cadastral oficial (SIT_ATIV) em UGBT_tab e UGMT_tab da BDGD
    print(f"Consultando situação cadastral (SIT_ATIV) na BDGD para o alimentador {alimentador}...")
    sit_ativ_map = carregar_situacao_gds_bdgd(alimentador)
    total_bdgd = len(sit_ativ_map)
    total_bdgd_at = sum(1 for info in sit_ativ_map.values() if info["sit_ativ"] == "AT")
    total_bdgd_ds = total_bdgd - total_bdgd_at
    print(
        f"BDGD {alimentador}: {total_bdgd} UGs cadastradas "
        f"({total_bdgd_at} ativas ['AT'], {total_bdgd_ds} desativadas ['DS'])."
    )

    # 2. Busca os arquivos de GD base (BT antes de MT, ordem determinística)
    arquivos_gd = sorted(pasta_ajustada.glob("GD_BT*.dss")) + sorted(pasta_ajustada.glob("GD_MT*.dss"))

    todos_geradores = []
    todos_desativados = []
    for arq in arquivos_gd:
        geradores, desativados, nao_encontrados = extrair_geradores(arq, sit_ativ_map=sit_ativ_map)
        todos_geradores.extend(geradores)
        todos_desativados.extend(desativados)
        kw_ativos = sum(g['PV_kva'] for g in geradores)
        kw_desativados = sum(d['kw'] for d in desativados)
        print(
            f"{arq.name}: {len(geradores)} ativos mantidos ({kw_ativos:.2f} kW) | "
            f"{len(desativados)} desativados expurgados ({kw_desativados:.2f} kW)"
        )
        if nao_encontrados:
            print(
                f"[Aviso] {len(nao_encontrados)} geradores em {arq.name} sem correspondência na BDGD: "
                f"{nao_encontrados[:5]}"
            )

    if not todos_geradores:
        print(f"Nenhum gerador GD ativo encontrado na pasta: {pasta_ajustada}")
        return

    # Registra arquivo de auditoria das GDs removidas (não incluído no run_ESB01S4.dss)
    if todos_desativados:
        out_desativados = pasta_ajustada / f"{alimentador}_gds_desativadas.dss"
        kw_total_ds = sum(d['kw'] for d in todos_desativados)
        linhas_auditoria = [
            f"! Geradores Distribuídos expurgados por SIT_ATIV != 'AT' na BDGD ({alimentador})",
            f"! Total removido: {len(todos_desativados)} geradores ({kw_total_ds:.2f} kW nominais)",
            "",
        ]
        linhas_auditoria.extend(
            f"! SIT_ATIV={d['sit_ativ']} kw={d['kw']}\n{d['linha_dss']}"
            for d in todos_desativados
        )
        with open(out_desativados, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas_auditoria) + "\n")
        print(f"Auditoria de GDs desativadas salva em: {out_desativados.name}")

    # 3. Carrega metadados das usinas solares fotovoltaicas
    PV_list = pd.read_csv(METADATA_CSV)
    total_curvas = len(PV_list)
    
    print("Processando e interpolando curvas climáticas via PCHIP...")
    PVGen = []
    
    available_curves = list(range(1, total_curvas + 1))
    current_idx = 0
    
    for i, gen_data in enumerate(todos_geradores):
        while True:
            if not available_curves:
                raise RuntimeError("Todas as curvas solares disponíveis foram rejeitadas na validação física.")
                
            curve_id = available_curves[current_idx % len(available_curves)]
            
            try:
                new_pv = PVGenerator(
                    PV_id=i+1,
                    PV_phases=gen_data['PV_phases'],
                    PV_bus=gen_data['PV_bus'],
                    PV_conn=gen_data['PV_conn'],
                    PV_kv=gen_data['PV_kv'],
                    PV_kva=gen_data['PV_kva'],
                    PV_curve_id=curve_id,
                    PV_list=PV_list
                )
                new_pv.CurvePCHIPInterpolation(STEP)
                PVGen.append(new_pv)
                current_idx += 1
                break
            
            except ValueError as e:
                print(f"[Aviso] Curva {curve_id} rejeitada: {e}")
                available_curves.remove(curve_id)
        
    # 4. Gera arquivos de saída
    out_irrad = pasta_ajustada / f"{alimentador}_shape_pv_{STEP}.csv"
    out_temp = pasta_ajustada / f"{alimentador}_temperature_{STEP}.csv"
    out_dss = pasta_ajustada / f"{alimentador}_pv.dss"
    
    PVGenerator.GenerateCSV(PVGen, out_irrad, out_temp)
    PVGenerator.GenerateDSS(PVGen, out_dss)
    
    # 5. Atualiza o script run_{alimentador}.dss incluindo o Redirect para o novo arquivo DSS
    run_file = pasta_ajustada / f"run_{alimentador}.dss"
    if run_file.exists():
        with open(run_file, 'r', encoding='utf-8') as f:
            conteudo_run = f.read()
            
        if f"Redirect {out_dss.name}" not in conteudo_run:
            conteudo_run = conteudo_run.replace(
                "Set ControlMode=Time", 
                f"! Adiciona os PVSystems substituindo as GDs estáticas\nRedirect {out_dss.name}\n\nSet ControlMode=Time"
            )
            with open(run_file, 'w', encoding='utf-8') as f:
                f.write(conteudo_run)
            print(f"Arquivo {run_file.name} atualizado com Redirect para {out_dss.name}")

if __name__ == "__main__":
    alim = sys.argv[1] if len(sys.argv) > 1 else "ESB01S4"
    processar_gds(alim)

