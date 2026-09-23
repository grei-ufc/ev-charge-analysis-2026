import pandas as pd
import matplotlib.pyplot as plt
import random
from pathlib import Path

# Caminho do arquivo gerado pelo Orquestrador
CSV_PATH = Path("data/datasets/veiculos-eletricos/ev_loadshapes_normalized.csv")

# ========= CONFIGURAÇÕES =========
SEED = 8  # Mude este número para ver conjuntos diferentes de curvas!
# =================================

def plotar_curvas_aleatorias(seed: int):
    if not CSV_PATH.exists():
        print(f"Erro: O arquivo {CSV_PATH} não foi encontrado. Rode o orquestrador primeiro.")
        return

    print(f"Lendo dados das curvas...")
    df = pd.read_csv(CSV_PATH)
    
    todas_colunas = df.columns.tolist()
    
    print("Calculando os picos máximos de todas as curvas para encontrar as maiores sobreposições...")
    # Calcula o máximo de cada coluna e ordena do maior pro menor
    picos_por_coluna = df.max().sort_values(ascending=False)
    
    # Pega as 16 colunas com os maiores valores absolutos
    colunas_sorteadas = picos_por_coluna.head(16).index.tolist()
    
    print("\nAs 16 curvas com os maiores picos:")
    for c in colunas_sorteadas:
        print(f" -> {c} (Pico: {picos_por_coluna[c]:.2f})")
        
    # Cria a figura com 16 subplots (matriz 4x4)
    # sharex e sharey limpam a poluição visual dos eixos repetidos
    fig, axes = plt.subplots(4, 4, figsize=(18, 12), sharex=True, sharey=True)
    fig.suptitle("As 16 Curvas de VEs com Maiores Picos (Exposição de Sobreposição)", fontsize=18, fontweight='bold')
    
    # Matemática do Eixo X: 1 semana = 7 dias. Cada dia tem 144 pontos de 10 min.
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    ticks_x = [i * 144 for i in range(7)]
    
    # Encontra o pico absoluto de todo o dataset para travar o eixo Y
    # Isso evita que o matplotlib auto-escale para 1.1 se a amostra de 16 não tiver sobreposições
    pico_global = df.max().max()
    limite_y = pico_global * 1.1 if pico_global > 1.0 else 1.1
    
    # axes.flatten() transforma a matriz 4x4 numa lista linear para o laço
    for ax, nome_curva in zip(axes.flatten(), colunas_sorteadas):
        # A curva de carga
        ax.plot(df.index, df[nome_curva], color='#2ca02c', linewidth=1.5)
        
        # Preenchimento estético abaixo da curva
        ax.fill_between(df.index, df[nome_curva], color='#2ca02c', alpha=0.2)
        
        # Customizações do gráfico
        ax.set_title(f"{nome_curva}", fontsize=9, loc='center')
        ax.set_ylim(0, limite_y)  # Trava o topo baseado no máximo global do arquivo
        ax.grid(True, linestyle='--', alpha=0.5)
        
        # Formatação do Eixo X
        ax.set_xticks(ticks_x)
        ax.set_xticklabels(dias_semana)
        ax.set_xlim(0, 1007)
        
    # Coloca o label Y apenas no centro à esquerda da figura inteira
    fig.text(0.01, 0.5, 'Potência (Normalizada)', va='center', rotation='vertical', fontsize=12)
    
    plt.tight_layout(rect=[0.02, 0, 1, 0.98])  # Dá um pequeno respiro para o texto lateral e título
    plt.show()

if __name__ == "__main__":
    plotar_curvas_aleatorias(SEED)
