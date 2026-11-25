import warnings; warnings.filterwarnings("ignore")
from strats_w import *
from orders import run_O, O_DEFS, ETF3
grid=[0,2,5,10,15,20,30,50,75,100]
def be(sharpes, target):
    s=np.array(sharpes)
    if s[0] < target: return 0.0
    for i in range(1,len(grid)):
        if s[i] < target:
            return grid[i-1]+(grid[i]-grid[i-1])*(s[i-1]-target)/(s[i-1]-s[i])
    return 100.0
bms={}
for lab,uni,st in [("SECT",SECT,"1999-01-01"),("MULTI",MULTI,"2006-01-01"),("ETF3",ETF3,"2001-01-03")]:
    P,T,R,kw=bench(uni,st); bms[lab]=metrics(sim_weights(P,T,R,slip_bps=5)["nav"],P["rf"])["Sharpe"]
uni_of={"W01":"SECT","W02":"MULTI","W03":"SECT","W04":"MULTI","W05":"MULTI","W06":"MULTI","W10":"MULTI","W11":"MULTI","W12":"SECT","W13":None,"W14":None,"W15":None,"W16":None,"W17":"MULTI","W18":"MULTI","W19":"MULTI","W20":"SECT","W21":"SECT","W22":"SECT"}
rows=[]
for n,u in uni_of.items():
    P,T,R,kw,desc=W(n); sh=[]; ex=[]
    for b in grid:
        k=dict(kw); k["slip_bps"]=b; r=sim_weights(P,T,R,**k); m=metrics(r["nav"],P["rf"]); sh.append(m["Sharpe"])
    rows.append(dict(Strat=n,Desc=desc,Sh0=sh[0],Sh10=sh[3],BE_vs_cash=be(sh,0.0),BE_vs_passive=(be(sh,bms[u]) if u else np.nan),Passive=bms.get(u,0)))
for n in O_DEFS:
    sh=[]
    for b in grid:
        nav,tr,f,P=run_O(n,slip_bps=b); sh.append(metrics(nav,P["rf"])["Sharpe"])
    rows.append(dict(Strat=n,Desc=O_DEFS[n][1],Sh0=sh[0],Sh10=sh[3],BE_vs_cash=be(sh,0.0),BE_vs_passive=be(sh,bms["ETF3"]),Passive=bms["ETF3"]))
df=pd.DataFrame(rows).set_index("Strat"); df.to_pickle("be.pkl")
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",45)
print(df.round(2).to_string())
