import warnings; warnings.filterwarnings("ignore")
from strats_w import *
def lo_trend(uni, start, f, s, vlb=63, slip=10):
    P=panel(uni,start); c=P["c"]
    sg=np.sign(sma(c,f)-sma(c,s)); vol=c.pct_change().rolling(vlb).std()*np.sqrt(252)
    raw=(sg/vol); w=raw.div(raw.abs().sum(axis=1),axis=0).fillna(0).clip(lower=0)
    r=sim_weights(P,w,sched(c.index,"M"),slip_bps=slip); return metrics(r["nav"],P["rf"],r["turnover"]), r["nav"], P
U6=["SPY","QQQ","IEF","TLT","GLD","DBC"]
print("fast/slow grid (Sharpe/MaxDD) @10bps, U6 2006-2026:")
for f in [21,42,63,126]:
    print(f"  f={f:3d}", "  ".join(f"{lo_trend(U6,'2006-01-01',f,s)[0]['Sharpe']:.2f}/{lo_trend(U6,'2006-01-01',f,s)[0]['MaxDD']:.2f}" for s in [126,189,252,315]))
m,nav,P=lo_trend(U6,"2006-01-01",63,252)
for a,b in [("2006","2012"),("2013","2019"),("2020","2025"),("2026","2026")]:
    mm=metrics(nav.loc[a:b],RF_D); print(f"  {a}-{b}: CAGR {mm['CAGR']:.3f} Sharpe {mm['Sharpe']:.2f} MaxDD {mm['MaxDD']:.2f}")
print("  turnover/yr", round(m["TurnY"],2))
# passive inverse-vol hold of same 6 for comparison
P=panel(U6,"2006-01-01"); c=P["c"]; iv=1/c.pct_change().rolling(63).std(); w=iv.div(iv.sum(axis=1),axis=0).fillna(0)
mm=metrics(sim_weights(P,w,sched(c.index,"M"),slip_bps=10)["nav"],P["rf"]); print(f"  control: untimed inverse-vol same 6 ETFs: Sharpe {mm['Sharpe']:.2f} MaxDD {mm['MaxDD']:.2f} CAGR {mm['CAGR']:.3f}")
print("universe swap -> MULTI 8 ETFs:", {k:round(v,2) for k,v in lo_trend(MULTI,'2006-01-01',63,252)[0].items() if k in ('CAGR','Sharpe','MaxDD')})
print("universe swap -> sectors:", {k:round(v,2) for k,v in lo_trend(SECT,'1999-01-01',63,252)[0].items() if k in ('CAGR','Sharpe','MaxDD')})
