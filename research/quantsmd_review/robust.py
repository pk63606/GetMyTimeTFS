import warnings; warnings.filterwarnings("ignore")
from strats_w import *
from orders import run_O, ETF3
import pickle
pd.set_option("display.width",250)
def m_sub(nav, rf, a, b):
    s=nav.loc[a:b]; return metrics(s, rf)
periods=[("2001-01-01","2012-12-31"),("2013-01-01","2025-12-31"),("2026-01-01","2026-12-31")]
def summarize(label, nav, rf, bnav):
    out={"Strat":label}
    for a,b in periods:
        m=m_sub(nav,rf,a,b); mb=m_sub(bnav,rf,a,b)
        tag=a[:4]+"-"+b[2:4]
        out[f"Sh {tag}"]=m["Sharpe"]; out[f"Bm {tag}"]=mb["Sharpe"]
        if a.startswith("2026"): out["2026 ret"]=nav.loc[a:b].iloc[-1]/nav.loc[a:b].iloc[0]-1; out["2026 bm"]=bnav.loc[a:b].iloc[-1]/bnav.loc[a:b].iloc[0]-1
    # active return t-stat vs benchmark (monthly)
    r=nav.resample("ME").last().pct_change().dropna(); rb=bnav.resample("ME").last().pct_change().reindex(r.index)
    act=(r-rb).dropna(); out["IR t-stat"]=act.mean()/act.std()*np.sqrt(len(act))
    # Sharpe t-stat (Lo 2002 approx)
    d=nav.pct_change().dropna()-rf.reindex(nav.index).fillna(0).iloc[1:]; sr=d.mean()/d.std()*np.sqrt(252); yrs=len(d)/252
    out["Sharpe t"]=sr*np.sqrt(yrs)
    return out
rows=[]
navw=pickle.load(open("navs_w.pkl","rb")); navo=pickle.load(open("navs_o.pkl","rb"))
P=panel(SECT,"1999-01-01"); rf=P["rf"]
bm={"SECT":navw[("EW_SECT","base")],"MULTI":navw[("EW_MULTI","base")]}
_,T,R,kw=bench(ETF3,"2001-01-03"); P3=panel(ETF3,"2001-01-03"); bm["ETF3"]=sim_weights(P3,T,R,slip_bps=5)["nav"]
for s,u in [("W01","SECT"),("W02","MULTI"),("W05","MULTI"),("W10","MULTI"),("W11","MULTI"),("W17","MULTI"),("W18","MULTI"),("W19","MULTI"),("W20","SECT"),("W21","SECT"),("W03","SECT")]:
    rows.append(summarize(s,navw[(s,"base")],RF_D,bm[u]))
for s in ["O01","O04","O05","O12","O14"]:
    rows.append(summarize(s,navo[(s,"base")],RF_D,bm["ETF3"]))
print(pd.DataFrame(rows).set_index("Strat").round(2).to_string())
