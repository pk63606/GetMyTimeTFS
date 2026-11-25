import warnings; warnings.filterwarnings("ignore")
import yfinance as yf, numpy as np, pandas as pd
from engine import rsi, sma
T=["SPY","QQQ","IWM"]
def get(iv, period):
    d=yf.download(T, period=period, interval=iv, auto_adjust=True, progress=False)
    return d["Open"].dropna(), d["Close"].dropna()
def run(o, c, sig, slip_bps, per_share=True, cap=1/3):
    # long-only per name, equal 1/3 sleeves; signal at close of bar t -> trade at open of bar t+1
    pos=sig.shift(1).fillna(0)  # held during bar t+1
    # return of bar = held from open to close + gap from prev close to open if held previous bar
    r_intr=(c/o-1); r_gap=(o/c.shift(1)-1)
    ret=pos*r_intr + pos.shift(1).fillna(0)*pos*r_gap  # approx: gap counted only if held across
    trades=pos.diff().abs().fillna(pos.abs())
    comm = (0.005/c)*1e4 if per_share else 0  # $0.005/sh in bps of price
    cost=trades*(slip_bps + comm)/1e4
    port=((ret-cost)*cap).sum(axis=1)
    gross=(ret*cap).sum(axis=1)
    return port, gross, trades.sum().sum()
res=[]
o,c=get("60m","730d")
s=(sma(c,10)>sma(c,30)).astype(float)
for slip in [1,2,5]:
    p,g,n=run(o,c,s,slip); res.append(("W09 SMA10/30 1h (2y)",slip,g.sum(),p.sum(),n, (p.mean()/p.std()*np.sqrt(len(p)/2)) ))
o,c=get("15m","60d")
r=rsi(c); s=((r<30).astype(float))  # equal-weight basket when oversold, held while RSI<50 approx
st=np.zeros(r.shape); cur=np.zeros(r.shape[1],bool)
for i,row in enumerate(r.values):
    cur=np.where(~cur&(row<30),True,np.where(cur&(row>50),False,cur)); st[i]=cur
s=pd.DataFrame(st,index=r.index,columns=r.columns)
for slip in [1,2,5]:
    p,g,n=run(o,c,s,slip); res.append(("W07-style RSI 15m (60d)",slip,g.sum(),p.sum(),n,np.nan))
o,c=get("30m","60d")
hi=c.rolling(12).max().shift(1); s=(c>hi).astype(float)
# hold 4 bars after breakout signal
s=s.rolling(4,min_periods=1).max()
for slip in [1,2,5]:
    p,g,n=run(o,c,s,slip); res.append(("O16-style 12-bar breakout 30m (60d)",slip,g.sum(),p.sum(),n,np.nan))
o,c=get("5m","60d")
ema9=c.ewm(span=9,adjust=False).mean(); ema21=c.ewm(span=21,adjust=False).mean(); s=(ema9>ema21).astype(float)
for slip in [1,2,5]:
    p,g,n=run(o,c,s,slip); res.append(("W08-style EMA9/21 scalp, 5m (60d)",slip,g.sum(),p.sum(),n,np.nan))
df=pd.DataFrame(res,columns=["Strategy","slip bps/side","Gross ret","Net ret","Fills","Sharpe(ann)"])
pd.set_option("display.width",200); print(df.round(4).to_string(index=False))
