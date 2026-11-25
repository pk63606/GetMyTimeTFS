import warnings; warnings.filterwarnings("ignore")
from strats_w import *
P=panel(MULTI,"2006-01-01"); c=P["c"]; R=sched(c.index,"M")
print("W05 inverse-vol lookback sweep (10bps):")
for lb in [21,42,63,126,252]:
    for cap in [0.35,1.0]:
        iv=1/(c.pct_change().rolling(lb).std()); w=iv.div(iv.sum(axis=1),axis=0).fillna(0).clip(upper=cap)
        r=sim_weights(P,w,R,slip_bps=10); m=metrics(r["nav"],P["rf"]); print(f"  lb={lb:3d} cap={cap}: CAGR {m['CAGR']:.3f} Sharpe {m['Sharpe']:.2f} MaxDD {m['MaxDD']:.2f}")
# static (non-timed) inverse vol from first 3y as control: is the edge just 'hold more bonds'?
w_static=pd.DataFrame(np.tile((1/c.pct_change().iloc[:756].std()).values/(1/c.pct_change().iloc[:756].std()).sum(),(len(c),1)),index=c.index,columns=c.columns)
r=sim_weights(P,w_static,R,slip_bps=10); m=metrics(r["nav"],P["rf"]); print(f"  static inv-vol weights (frozen 2006-08): Sharpe {m['Sharpe']:.2f} CAGR {m['CAGR']:.3f}")
print("\nW01 sector SMA fast/slow grid, Sharpe @10bps (passive EW_SECT 0.45):")
P=panel(SECT,"1999-01-01"); c=P["c"]; D=sched(c.index,"D"); M=sched(c.index,"M")
for f in [20,50,100]:
    row=[]
    for s in [100,150,200,250]:
        if f>=s: row.append("  -  "); continue
        T=eqw(sma(c,f)>sma(c,s),0.25); m=metrics(sim_weights(P,T,D,slip_bps=10)["nav"],P["rf"]); row.append(f"{m['Sharpe']:.2f}/{m['MaxDD']:.2f}")
    print(f"  fast {f:3d}: ", "  ".join(row))
print("\nW25 trend on ETF proxies (SPY,QQQ,IEF,TLT,GLD,DBC) 2006-2026, long/short, 5bps:")
P=panel(["SPY","QQQ","IEF","TLT","GLD","DBC"],"2006-01-01"); c=P["c"]
s=np.sign(sma(c,63)-sma(c,252)); vol=c.pct_change().rolling(63).std()*np.sqrt(252)
raw=s/vol; w=raw.div(raw.abs().sum(axis=1),axis=0).fillna(0)
for lab,ww in [("long/short",w),("long-only",w.clip(lower=0))]:
    r=sim_weights(P,ww,sched(c.index,"M"),slip_bps=5); m=metrics(r["nav"],P["rf"]); print(f"  {lab}: CAGR {m['CAGR']:.3f} Sharpe {m['Sharpe']:.2f} MaxDD {m['MaxDD']:.2f}")
    print("     2026 YTD:", round(r["nav"].loc["2026"].iloc[-1]/r["nav"].loc["2026"].iloc[0]-1,3))
