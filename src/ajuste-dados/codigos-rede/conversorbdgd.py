from pathlib import Path
import inspect
import bdgd2opendss
from bdgd2opendss import settings

# Caminho dinâmico da sua BDGD (.gdb) e pasta onde deseja salvar os arquivos OpenDSS
base_dir = Path(__file__).resolve().parents[3]  # Raiz do projeto (ev-analysis-2026)
dados_rede_dir = base_dir.parent / "dados-da-rede"

bdgd_path = str(dados_rede_dir / "Enel_CE_39_2024-12-31_V11_20250822-1151.gdb")
output_folder = str(dados_rede_dir)
all_feeders = False
lst_feeders = ['ESB01S1', 'ESB01S2', 'ESB01S3', 'ESB01S4', 'ESB01S5', 'ESB01S6', 'ESB01S7', 'ESB01S8']

# Habilita a inclusão (redirects) das GDs nos arquivos Master!
settings.intAddGDs = True

# (Opcional) Listar os alimentadores disponíveis na BDGD
feeders = bdgd2opendss.get_feeder_list(bdgd_path)
# print("Alimentadores encontrados:", feeders)
feeders_sub = [f for f in feeders if "ESB" in f]
n_alimentadores_sub = len(feeders_sub)
print(f"Encontrados {n_alimentadores_sub} alimentadores na Subestação: {feeders_sub}")

# Executar a conversão 
bdgd2opendss.run(bdgd_path, output_folder, all_feeders, lst_feeders)

# print(dir(bdgd2opendss))

# for item in dir(bdgd2opendss):
#     if not item.startswith('_'):
#         atributo = getattr(bdgd2opendss, item)
#         if callable(atributo):
#             try:
#                 print(f"\n{'='*60}")
#                 print(f"📌 Código de: {item}")
#                 print('='*60)
#                 print(inspect.getsource(atributo))
#             except (OSError, TypeError):
#                 print(f"⚠️ {item}: código fonte não disponível")