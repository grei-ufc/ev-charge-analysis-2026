#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para converter geradores GD (provenientes da BDGD) em objetos PVSystem do OpenDSS,
gerando também as curvas CSV de irradiância e temperatura correspondentes,
reaproveitando a lógica do pv_creator.py.
"""

import os
import re
import sys
import pandas as pd
from pathlib import Path
from math import ceil

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parents[3]
METADATA_CSV = BASE_DIR / "data" / "datasets" / "geradores-fv" / "power_station_metadata.csv"
SOLAR_DIR = BASE_DIR / "data" / "datasets" / "geradores-fv" / "solar_station"

STEP = '10min'
DIAS = 7
T_SIMULATION_MIN = DIAS * 24 * 60
NPTS_ORIGIN = ceil(T_SIMULATION_MIN / 15)
START_DATE = "2026-01-01 00:00:00"

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO
# ==============================================================================
def extrair_geradores(dss_file: Path):
    """Lê um arquivo .dss de GD (BDGD) e extrai fases, barra, tensão e potência."""
    geradores = []
    if not dss_file.exists():
        return geradores
    
    with open(dss_file, 'r', encoding='utf-8', errors='ignore') as f:
        for linha in f:
            if not linha.strip().lower().startswith('new "generator.'):
                continue
            
            m_phases = re.search(r'phases=(\d+)', linha, re.IGNORECASE)
            m_bus = re.search(r'bus1=([^\s]+)', linha, re.IGNORECASE)
            m_kv = re.search(r'kv=([\d\.]+)', linha, re.IGNORECASE)
            m_kw = re.search(r'kw=([\d\.]+)', linha, re.IGNORECASE)
            
            if m_phases and m_bus and m_kv and m_kw:
                geradores.append({
                    'PV_phases': int(m_phases.group(1)),
                    'PV_bus': m_bus.group(1),
                    'PV_kv': float(m_kv.group(1)),
                    'PV_kva': float(m_kw.group(1))
                })
    return geradores

# ==============================================================================
# CLASSE DE GERAÇÃO (Adaptada do pv_creator.py)
# ==============================================================================
class PVGenerator:
    _solar_cache = {}

    def __init__(self, PV_id, PV_phases, PV_bus, PV_kv, PV_kva, PV_curve_id, PV_list, start=96):
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
        self.kv = PV_kv
        self.kva = PV_kva
        
        self.irrad = 1000
        self.pmpp = self.kva
        self.temperature = 25
        self.pf = 1
        self.vminpu = 0.001
        self.model = 1

        self.effcurve = 'New XYCurve.MyEff npts=4 xarray=[0.1, 0.2, 0.4, 1.0] yarray=[0.86, 0.90, 0.93, 0.97]'
        self.ptcurve = 'New XYCurve.MyPvsT npts=4 xarray=[0, 25, 75, 100] yarray=[1.2, 1.0, 0.8, 0.6]'

        self.npts = NPTS_ORIGIN
        data_slice = slice(start, self.npts + start + 1)
        
        self.irrad_curve = (self.solar_station_curves['poa_irradiance_wm2'].iloc[data_slice] / self.irrad).reset_index(drop=True)
        
        # --- BLINDAGEM DE DADOS CLIMÁTICOS (Validação Rigorosa) ---
        # Rejeitamos a curva corrompida apenas se os valores forem fisicamente absurdos.
        # Pequenas quedas de sensor (NaN) serão tratadas com interpolação.
        
        # 1. Validação e Correção de Irradiância
        # Sensores reais (piranômetros) frequentemente registram ruído térmico negativo à noite (ex: -0.5 W/m²).
        # Primeiro, ceifamos qualquer valor negativo para zero.
        self.irrad_curve = self.irrad_curve.clip(lower=0)
        
        # O P.U. em dias claros pode passar de 1.0 devido ao efeito Lente de Nuvem (Cloud-Edge Effect).
        # Rejeitamos apenas se passar de um teto absurdamente alto (ex: 1.5 p.u.).
        if (self.irrad_curve > 1.5).any():
            max_val = self.irrad_curve.max()
            raise ValueError(f"Irradiância extrema (Pico: {max_val:.2f} p.u.) detectada na curva {self.FILE_CSV}.")
        
        # Valores > 1.0 p.u. são mantidos intocados para simular a física real.
        # Suavizamos apenas buracos de falhas curtas de sensor (NaN).
        self.irrad_curve = self.irrad_curve.interpolate(method='linear').fillna(0)
        self.irrad_curve.name = f'my_shape{PV_id}_irrad'

        self.temperature_curve = self.solar_station_curves['panel_temperature_celsius'].iloc[data_slice].reset_index(drop=True)
        
        # 2. Validação de Temperatura (IEC 61215: -40°C a +85°C)
        if (self.temperature_curve < -40).any() or (self.temperature_curve > 85).any():
            min_val = self.temperature_curve.min()
            max_val = self.temperature_curve.max()
            raise ValueError(f"Temperatura inválida (Min: {min_val:.1f}°C, Max: {max_val:.1f}°C) detectada na curva {self.FILE_CSV}.")
        
        # Suaviza buracos (NaN) de falhas curtas
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
        print(f"✅ CSVs otimizados (curvas únicas) gerados: {out_irrad.name} e {out_temp.name}")

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
        except:
            minterval = 5
            
        irrad_shape_file_name = out_dss.with_name(out_dss.stem + "_irrad_shapes.dss")
        temp_shape_file_name = out_dss.with_name(out_dss.stem + "_temp_shapes.dss")

        processed_curves = set()

        for pv in PVGen:
            pv_id = pv.name.replace('PV', '')
            c_id = pv.curve_id
            
            # Só criamos os shapes no DSS se aquela curva ainda não foi registrada
            if c_id not in processed_curves:
                irrad_mults = pv.irrad_curve.iloc[:, 1].tolist()
                temp_mults = pv.temperature_curve.iloc[:, 1].tolist()
                
                irrad_str = " ".join([f"{x:.4f}" for x in irrad_mults])
                temp_str = " ".join([f"{x:.4f}" for x in temp_mults])
                
                irrad_shape_lines.append(f"New LoadShape.shape_irrad_{c_id} npts={npts} minterval={minterval} mult=[{irrad_str}]")
                temp_shape_lines.append(f"New Tshape.shape_temp_{c_id} npts={npts} minterval={minterval} temp=[{temp_str}]")
                
                processed_curves.add(c_id)
            
            pv_command = (
                f"New PVSystem.{pv.name} phases={pv.phases} Bus1={pv.bus} "
                f"kV={pv.kv} kVA={pv.kva} irrad={pv.irrad/1000} Pmpp={pv.pmpp}\n"
                f"~ temperature={pv.temperature} PF={pv.pf} EffCurve=MyEff P-TCurve=MyPvsT\n"
                f"~ Daily=shape_irrad_{c_id} TDaily=shape_temp_{c_id}\n"
                f"~ Vminpu={pv.vminpu} Model={pv.model}\n"
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
            
        print(f"✅ DSS gerado com shapes otimizados: {out_dss.name}")

# ==============================================================================
# ORQUESTRADOR
# ==============================================================================
def processar_gds(alimentador):
    pasta_ajustada = BASE_DIR / "data" / "rede" / f"{alimentador}"
    
    # 1. Buscar os arquivos de GD base
    arquivos_gd = list(pasta_ajustada.glob("GD_BT*.dss")) + list(pasta_ajustada.glob("GD_MT*.dss"))
    
    todos_geradores = []
    for arq in arquivos_gd:
        geradores = extrair_geradores(arq)
        todos_geradores.extend(geradores)
        print(f"Extraídos {len(geradores)} geradores do arquivo {arq.name}")

    if not todos_geradores:
        print("⚠️ Nenhum gerador GD (BDGD) encontrado na pasta!")
        return

    # 2. Carregar metadados das usinas fotovoltaicas
    PV_list = pd.read_csv(METADATA_CSV)
    total_curvas = len(PV_list)
    
    print("Processando e interpolando curvas...")
    PVGen = []
    
    # Pool de curvas disponíveis. Se uma curva for considerada corrompida, ela será removida deste pool.
    available_curves = list(range(1, total_curvas + 1))
    current_idx = 0
    
    for i, gen_data in enumerate(todos_geradores):
        while True:
            if not available_curves:
                raise RuntimeError("Erro Fatal: Todas as curvas solares disponíveis foram classificadas como corrompidas e rejeitadas.")
                
            # Distribui circularmente apenas as curvas válidas restantes
            curve_id = available_curves[current_idx % len(available_curves)]
            
            try:
                new_pv = PVGenerator(
                    PV_id=i+1,
                    PV_phases=gen_data['PV_phases'],
                    PV_bus=gen_data['PV_bus'],
                    PV_kv=gen_data['PV_kv'],
                    PV_kva=gen_data['PV_kva'],
                    PV_curve_id=curve_id,
                    PV_list=PV_list
                )
                new_pv.CurvePCHIPInterpolation(STEP)
                PVGen.append(new_pv)
                
                # Sucesso: avança o índice para a próxima iteração
                current_idx += 1
                break
            
            except ValueError as e:
                # Falhou na validação: Logamos o motivo exato
                print(f"⚠️ [PULO DE CURVA] {e}")
                # Removemos a curva corrompida permanentemente do pool para não testá-la novamente
                available_curves.remove(curve_id)
                # O current_idx não é incrementado, então na próxima rodada do `while`,
                # o `available_curves[current_idx]` automaticamente apontará para a "nova" curva que caiu nesta posição.
        
    # 3. Gerar os outputs
    out_irrad = pasta_ajustada / f"{alimentador}_shape_pv_{STEP}.csv"
    out_temp = pasta_ajustada / f"{alimentador}_temperature_{STEP}.csv"
    out_dss = pasta_ajustada / f"{alimentador}_pv.dss"
    
    PVGenerator.GenerateCSV(PVGen, out_irrad, out_temp)
    PVGenerator.GenerateDSS(PVGen, out_dss)
    
    # 4. Inserir Redirect no run_{alimentador}.dss, se existir
    run_file = pasta_ajustada / f"run_{alimentador}.dss"
    if run_file.exists():
        with open(run_file, 'r', encoding='utf-8') as f:
            conteudo_run = f.read()
            
        # Se não houver redirect, adiciona logo após a compilação do master
        if f"Redirect {out_dss.name}" not in conteudo_run:
            conteudo_run = conteudo_run.replace(
                "Set ControlMode=Time", 
                f"! Adiciona os PVSystems substituindo as GDs antigas\nRedirect {out_dss.name}\n\nSet ControlMode=Time"
            )
            with open(run_file, 'w', encoding='utf-8') as f:
                f.write(conteudo_run)
            print(f"✅ Arquivo {run_file.name} atualizado com Redirect para {out_dss.name}")

if __name__ == "__main__":
    alim = sys.argv[1] if len(sys.argv) > 1 else "ESB01S4"
    processar_gds(alim)

