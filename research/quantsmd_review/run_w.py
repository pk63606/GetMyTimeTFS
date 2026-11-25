import warnings; warnings.filterwarnings("ignore")
from strats_w import *
import pickle
names = ["W01","W02","W03","W04","W05","W06","W10","W11","W12","W13","W14","W15","W16","W17","W18","W19","W20","W21","W22","W23","W24","W25"]
rows=[]; navs={}
def run(label, P, T, R, kw):
    fxf = kw.get("comm", True) is False
    scen = {"gross":dict(slip_bps=0,comm=False),"lib1bp":dict(slip_bps=1,comm=False),
            "base":dict(slip_bps=(1 if fxf else 5),comm=not fxf),"stress":dict(slip_bps=(3 if fxf else 15),comm=not fxf)}
    for sc,cfg in scen.items():
        k=dict(kw); k.update(cfg)
        res=sim_weights(P,T,R,**k)
        m=metrics(res["nav"],P["rf"],res["turnover"],res["costs"],res["trades"],res["expo"])
        m.update(Strat=label,Scen=sc); rows.append(m); navs[(label,sc)]=res["nav"]
for n in names:
    P,T,R,kw,desc = W(n); run(n,P,T,R,kw)
for lab,uni,st in [("EW_SECT",SECT,"1999-01-01"),("EW_MULTI",MULTI,"2006-01-01"),("SPY",["SPY"],"1999-01-01"),("SPY_06",["SPY"],"2006-01-01")]:
    P,T,R,kw=bench(uni,st); run(lab,P,T,R,kw)
df=pd.DataFrame(rows); df.to_pickle("res_w.pkl"); pickle.dump(navs,open("navs_w.pkl","wb"))
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
piv=df.pivot_table(index="Strat",columns="Scen",values=["CAGR","Sharpe"],sort=False)[[("CAGR","gross"),("CAGR","lib1bp"),("CAGR","base"),("CAGR","stress"),("Sharpe","gross"),("Sharpe","base"),("Sharpe","stress")]]
print(piv.round(3).to_string())
b=df[df.Scen=="base"].set_index("Strat")[["ExCAGR","Vol","MaxDD","Calmar","TurnY","Fills/yr","AvgExpo","Years"]]
print(b.round(3).to_string())
