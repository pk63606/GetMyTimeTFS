import warnings; warnings.filterwarnings("ignore")
from strats_w import *
P = panel(MULTI, "2006-01-01"); c=P["c"]; ret=c.pct_change(); R=sched(c.index,"M")
def w18(lbm=126, top=3, tv=0.15, vlb=42, ml=2.0, cap=0.40, posfilter=True):
    m=c/c.shift(lbm)-1
    mm=m.where(m>0) if posfilter else m
    base=eqw(mm.rank(axis=1,ascending=False)<=top, cap)
    pr=(base.shift(1)*ret).sum(axis=1); vol=pr.rolling(vlb).std()*np.sqrt(252)
    return base.mul((tv/vol).clip(upper=ml).fillna(0),axis=0)
rows=[]
for lbm in [63,126,189,252]:
  for top in [2,3,4]:
    for tv,ml in [(0.10,1.0),(0.15,1.0),(0.15,2.0),(0.20,2.0)]:
        T=w18(lbm,top,tv,42,ml, cap=max(0.40,1/top))
        r=sim_weights(P,T,R,slip_bps=10); m=metrics(r["nav"],P["rf"],r["turnover"])
        rows.append(dict(lb=lbm,top=top,tv=tv,maxlev=ml,CAGR=m["CAGR"],Sharpe=m["Sharpe"],MaxDD=m["MaxDD"],TurnY=m["TurnY"]))
df=pd.DataFrame(rows); pd.set_option("display.width",200)
print(df.pivot_table(index=["lb","top"],columns=["tv","maxlev"],values="Sharpe").round(2))
print("share of 48 variants with Sharpe > EW_MULTI 0.43:", (df.Sharpe>0.43).mean().round(2), " > SPY 0.53:", (df.Sharpe>0.533).mean().round(2))
print("no-leverage default (126,3,15%,1x):"); print(df[(df.lb==126)&(df.top==3)].round(3).to_string())
# breakeven slippage for W18 default
for b in [0,10,25,50,75,100]:
    r=sim_weights(P,w18(),R,slip_bps=b); m=metrics(r["nav"],P["rf"]); print(b,"bps -> Sharpe",round(m["Sharpe"],3),"CAGR",round(m["CAGR"],4))
