import pandas as pd

mults = [0.5] * 168
idx_1h = pd.date_range("2026-01-01", periods=169, freq="h")
mults_wrap = mults + [mults[0]]
s = pd.Series(mults_wrap, index=idx_1h)

idx_10min = pd.date_range("2026-01-01", periods=1009, freq="10min")
s_interp = s.reindex(idx_10min).interpolate(method='pchip')
s_final = s_interp.iloc[:-1].clip(lower=0.0).round(6)

print(len(s_final))
