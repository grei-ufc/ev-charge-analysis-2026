import pandas as pd
import matplotlib.pyplot as plt
import random
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parents[3]
    arquivo_csv = base_dir / "data" / "datasets" / "curvas-de-carga" / "Curvas_Semanas_Sinteticas.csv"
    
    if not arquivo_csv.exists():
        print(f"Arquivo não encontrado: {arquivo_csv}")
        return
        
    print(f"Carregando {arquivo_csv.name}...")
    df = pd.read_csv(arquivo_csv, index_col='index')
    
    # Escolhe uma curva aleatória para inspecionar
    coluna_teste = random.choice(df.columns)
    print(f"Plotando curva sintética: {coluna_teste}")
    
    y = df[coluna_teste].values
    x = range(len(y))
    
    # Prepara a Figura com 1 gráfico grande em cima e 3 de zoom embaixo
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.5, 1])
    
    # -------------------------------------------------------------
    # Gráfico 1: Visão Geral (Semana Inteira)
    # -------------------------------------------------------------
    ax_geral = fig.add_subplot(gs[0, :])
    ax_geral.plot(x, y, color='royalblue', linewidth=1.5)
    ax_geral.set_title(f"Visão Geral da Semana - {coluna_teste}", fontsize=14, fontweight='bold')
    ax_geral.set_ylabel("Potência (P.U.)")
    ax_geral.grid(True, linestyle='--', alpha=0.5)
    
    # Marca as 6 emendas de meia-noite com linhas verticais vermelhas
    for dia in range(1, 7):
        ax_geral.axvline(dia * 144, color='crimson', linestyle='--', alpha=0.8, 
                         label="Meia-noite" if dia == 1 else "")
                         
    ax_geral.legend()
    
    # Eixo X configurado para os dias da semana
    ax_geral.set_xticks([0, 144, 288, 432, 576, 720, 864])
    ax_geral.set_xticklabels(['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'])
    ax_geral.set_xlim(0, 1008)
    
    # -------------------------------------------------------------
    # Função Auxiliar para os Zooms
    # -------------------------------------------------------------
    def plot_zoom_emenda(ax, dia, titulo):
        meia_noite = dia * 144
        # Janela de visualização: 18 pontos para cada lado (3 horas antes e 3 depois)
        janela_zoom = 18 
        
        inicio = meia_noite - janela_zoom
        fim = meia_noite + janela_zoom
        
        # Plota os pontos reais para vermos como o PCHIP se comportou
        ax.plot(x[inicio:fim], y[inicio:fim], marker='o', markersize=5, color='darkorange', linewidth=2)
        
        # Marca exato o ponto da transição
        ax.axvline(meia_noite, color='crimson', linestyle='--', linewidth=2, label="Emenda PCHIP (00:00)")
        
        ax.set_title(titulo, fontsize=12, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc="lower center", fontsize=9)
        
        # Ajusta labels para mostrar as "horas" do zoom
        ax.set_xticks([inicio, meia_noite, fim])
        ax.set_xticklabels(['21:00\n(Noite)', '00:00', '03:00\n(Madrugada)'])

    # -------------------------------------------------------------
    # Gráficos Inferiores (Zooms)
    # -------------------------------------------------------------
    # Emenda 1 (Seg->Ter)
    ax_z1 = fig.add_subplot(gs[1, 0])
    plot_zoom_emenda(ax_z1, 1, "Transição: Seg ➔ Ter (Dias Úteis)")
    
    # Emenda 5 (Sex->Sáb)
    ax_z2 = fig.add_subplot(gs[1, 1])
    plot_zoom_emenda(ax_z2, 5, "Transição: Sex ➔ Sáb (Fim de Semana)")
    
    # Emenda 6 (Sáb->Dom)
    ax_z3 = fig.add_subplot(gs[1, 2])
    plot_zoom_emenda(ax_z3, 6, "Transição: Sáb ➔ Dom (Fim de Semana)")
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
