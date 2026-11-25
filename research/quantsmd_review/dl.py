import os, yfinance as yf, pandas as pd
os.makedirs("data", exist_ok=True)
T = ["SPY","QQQ","IWM","EFA","EEM","TLT","IEF","GLD","DBC","VNQ","XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY","KO","PEP","EWA","EWC","SHY","BIL",
     "EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","ES=F","NQ=F","ZN=F","CL=F","GC=F","ZC=F","^IRX"]
df = yf.download(T, start="1998-01-01", end="2026-11-25", auto_adjust=False, progress=False, group_by="column", threads=True)
df.to_pickle("data/raw.pkl")
for f in ["Open","High","Low","Close","Adj Close"]:
    print(f, df[f].shape)
c = df["Adj Close"]
print(c.apply(lambda s: s.first_valid_index()).to_string())
print(c.tail(2).T.head(40))

# XLP occasionally fails in the batch call; fetch it separately and merge
x = yf.download("XLP", start="1998-01-01", end="2026-11-25", auto_adjust=False, progress=False)
x.columns = x.columns.get_level_values(0)
for f in ["Open","High","Low","Close","Adj Close","Volume"]:
    df[(f,"XLP")] = x[f]
df.sort_index(axis=1).to_pickle("data/raw.pkl")
