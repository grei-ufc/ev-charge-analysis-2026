import pandas as pd
from pathlib import Path

csv_path = Path("data/datasets/geradores-fv/solar_station/PS_001.csv")
df = pd.read_csv(csv_path)

start = 96
npts = 672 # 7 days * 24 * 4 = 672
data_slice = slice(start, npts + start + 1)
print(data_slice)

irrad = df['poa_irradiance_wm2'].iloc[data_slice] / 1000
temp = df['panel_temperature_celsius'].iloc[data_slice]

print("Irrad min/max:", irrad.min(), irrad.max())
print("Irrad hasna:", irrad.isna().sum())
print("Temp min/max:", temp.min(), temp.max())
print("Temp hasna:", temp.isna().sum())

