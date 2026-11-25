import warnings; warnings.filterwarnings("ignore")
from orders import *
import pickle
rows=[]; navs={}
for code in O_DEFS:
    for sc,(sl,cm) in {"gross":(0,False),"lib":(5,True),"base":(5,True),"stress":(15,True)}.items():
        if sc=="lib": continue
        nav,tr,fills,P = run_O(code, slip_bps=sl, comm=cm)
        m = metrics(nav, P["rf"]); m.update(Strat=code, Scen=sc, Trades=len(tr), Win=(tr>0).mean() if len(tr) else np.nan,
              AvgTrade=tr.mean() if len(tr) else np.nan)
        rows.append(m); navs[(code,sc)]=nav
# benchmark: equal-weight SPY/QQQ/IWM buy & hold, monthly rebal
from strats_w import bench
P,T,R,kw = bench(ETF3,"2001-01-03")
for sc,(sl,cm) in {"gross":(0,False),"base":(5,True),"stress":(15,True)}.items():
    res=sim_weights(P,T,R,slip_bps=sl,comm=cm); m=metrics(res["nav"],P["rf"]); m.update(Strat="EW_3ETF",Scen=sc); rows.append(m)
df=pd.DataFrame(rows); df.to_pickle("res_o.pkl"); pickle.dump(navs,open("navs_o.pkl","wb"))
pd.set_option("display.width",250)
piv=df.pivot_table(index="Strat",columns="Scen",values=["CAGR","Sharpe"],sort=False)[[("CAGR","gross"),("CAGR","base"),("CAGR","stress"),("Sharpe","gross"),("Sharpe","base"),("Sharpe","stress")]]
print(piv.round(3).to_string())
print(df[df.Scen=="base"].set_index("Strat")[["ExCAGR","Vol","MaxDD","Calmar","Trades","Win","AvgTrade"]].round(4).to_string())
