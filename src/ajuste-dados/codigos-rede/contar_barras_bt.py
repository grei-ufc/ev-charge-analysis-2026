import py_dss_interface
import os
import glob
import sys
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Permite passar o código como argumento no terminal (ex: python contar_barras_bt.py ADT)
    # ou pergunta interativamente caso não seja passado.
    if len(sys.argv) > 1:
        sub_code = sys.argv[1].upper()
    else:
        sub_code = input("Digite o código da Subestação (ex: ADT, AGF, ESB): ").strip().upper()
        
    from pathlib import Path
    base_dir = Path(__file__).resolve().parents[3]  # Raiz do projeto (ev-analysis-2026)
    
    # Busca na pasta dados-da-rede
    sub_dir_padrao = base_dir.parent / "dados-da-rede" / f"sub__{sub_code}"
    sub_dir_figuras = base_dir.parent / "dados-da-rede" / "figuras" / f"sub__{sub_code}"
    
    sub_dir = str(sub_dir_padrao if sub_dir_padrao.exists() else sub_dir_figuras)
    
    if not os.path.exists(sub_dir):
        print(f"Erro: Diretório da subestação não encontrado: {sub_dir}")
        return

    # Inicializando o py_dss_interface apenas uma vez
    dss = py_dss_interface.DSS()
    
    # Listar as pastas dos alimentadores
    alimentadores = [d for d in os.listdir(sub_dir) if os.path.isdir(os.path.join(sub_dir, d))]
    alimentadores.sort() # Ordenar para melhor visualização
    
    total_geral_barras = 0
    total_geral_bt = 0
    total_geral_cargas_bt = 0
    total_geral_cargas_mt = 0
    
    # Listas para guardar dados do gráfico
    nomes_alimentadores = []
    lista_barras_totais = []
    lista_barras_bt = []
    lista_cargas_bt = []
    lista_cargas_mt = []
    
    print(f"--- Iniciando Análise para {len(alimentadores)} Alimentadores da Subestação {sub_code} ---")
    
    for alimentador in alimentadores:
        alim_path = os.path.join(sub_dir, alimentador)
        
        # Encontrar o arquivo Master_*.dss dentro da pasta do alimentador
        dss_files = glob.glob(os.path.join(alim_path, "Master_*.dss"))
        if not dss_files:
            print(f"\n[{alimentador}] Arquivo Master_.dss não encontrado.")
            continue
            
        dss_file = dss_files[0]
        print(f"\n[{alimentador}] Analisando...")
        
        # Limpar a memória do OpenDSS antes de compilar uma nova rede
        dss.text("Clear")
        dss.text(f'Compile "{dss_file}"')
        dss.text('CalcVoltageBases')
        dss.text('Solve')
        
        # ==================================
        # 1. Contagem de Barras
        # ==================================
        bus_names = dss.circuit.buses_names
        todas_barras = len(bus_names) if bus_names else 0
        barras_bt_count = 0
        
        if bus_names:
            for bus_name in bus_names:
                dss.circuit.set_active_bus(bus_name)
                kv_base = dss.bus.kv_base
                if kv_base > 0 and kv_base <= 1.0:
                    barras_bt_count += 1
                    
        # ==================================
        # 2. Contagem de Cargas (BT e MT)
        # ==================================
        cargas_bt_count = 0
        cargas_mt_count = 0
        
        if dss.loads.count > 0:
            load_idx = dss.loads.first()
            while load_idx > 0:
                kv = dss.loads.kv
                if kv > 0 and kv <= 1.0:
                    cargas_bt_count += 1
                elif kv > 1.0:
                    cargas_mt_count += 1
                load_idx = dss.loads.next()
                
        print(f"[{alimentador}] Barras (Total/BT): {todas_barras}/{barras_bt_count} | Cargas (MT/BT): {cargas_mt_count}/{cargas_bt_count}")
        
        total_geral_barras += todas_barras
        total_geral_bt += barras_bt_count
        total_geral_cargas_bt += cargas_bt_count
        total_geral_cargas_mt += cargas_mt_count
        
        # Armazenando para o gráfico
        nomes_alimentadores.append(alimentador)
        lista_barras_totais.append(todas_barras)
        lista_barras_bt.append(barras_bt_count)
        lista_cargas_mt.append(cargas_mt_count)
        lista_cargas_bt.append(cargas_bt_count)
        
    print(f"\n--- Resultado Final da Subestação {sub_code} ---")
    print(f"Total Geral de Barras: {total_geral_barras} (BT: {total_geral_bt})")
    print(f"Total Geral de Cargas: {total_geral_cargas_bt + total_geral_cargas_mt} (MT: {total_geral_cargas_mt} | BT: {total_geral_cargas_bt})")

    # ==========================
    # Lógica de Plotagem (2 Subplots)
    # ==========================
    if nomes_alimentadores:
        x = np.arange(len(nomes_alimentadores))  # posições dos labels no eixo x
        width = 0.35  # largura de cada barra

        # Criando figura com 2 gráficos empilhados
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # --- Gráfico 1: Barras ---
        rects1_1 = ax1.bar(x - width/2, lista_barras_totais, width, label='Total de Barras', color='#1f77b4')
        rects1_2 = ax1.bar(x + width/2, lista_barras_bt, width, label='Barras BT (<= 1kV)', color='#ff7f0e')
        ax1.set_ylabel('Quantidade de Barras')
        ax1.set_title(f'Quantidade de BARRAS por Alimentador - Subestação {sub_code}')
        ax1.legend()
        ax1.bar_label(rects1_1, padding=3, rotation=90)
        ax1.bar_label(rects1_2, padding=3, rotation=90)
        ax1.margins(y=0.2)  # Adiciona 20% de espaço extra no topo para caber as labels verticais
        
        # --- Gráfico 2: Cargas ---
        rects2_1 = ax2.bar(x - width/2, lista_cargas_mt, width, label='Cargas MT (> 1kV)', color='#2ca02c')
        rects2_2 = ax2.bar(x + width/2, lista_cargas_bt, width, label='Cargas BT (<= 1kV)', color='#d62728')
        ax2.set_ylabel('Quantidade de Cargas')
        ax2.set_title(f'Quantidade de CARGAS por Alimentador - Subestação {sub_code}')
        ax2.legend()
        ax2.bar_label(rects2_1, padding=3, rotation=90)
        ax2.bar_label(rects2_2, padding=3, rotation=90)
        ax2.margins(y=0.2)  # Adiciona 20% de espaço extra no topo para caber as labels verticais

        # Ajustes do eixo X (aplica-se no gráfico de baixo por causa do sharex=True)
        ax2.set_xticks(x)
        ax2.set_xticklabels(nomes_alimentadores, rotation=45, ha='right')

        fig.tight_layout()
        
        # Salva a figura na mesma pasta do script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        grafico_path = os.path.join(script_dir, f'grafico_barras_cargas_{sub_code}.png')
        
        plt.savefig(grafico_path, dpi=300)
        print(f"\nGráfico salvo com sucesso em: {grafico_path}")

if __name__ == "__main__":
    main()
