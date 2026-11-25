"""Combine strategies into a portfolio: hindsight top-5 vs walk-forward top-5."""
import warnings; warnings.filterwarnings("ignore")
import pickle
from strats_w import *
nw = pickle.load(open("navs_w.pkl", "rb")); no = pickle.load(open("navs_o.pkl", "rb"))
SC = "base"  # 5 bps slippage + IBKR commission inside every sleeve
pool = {k[0]: v for k, v in {**nw, **no}.items() if k[1] == SC and not k[0].startswith(("EW_", "SPY", "W23", "W24", "W25"))}
R = pd.DataFrame({k: v.pct_change() for k, v in pool.items()}).loc["2007-01-01":].dropna(how="any")
rf = RF_D.reindex(R.index).fillna(0)
print(f"pool: {R.shape[1]} strategies, {R.index[0].date()} -> {R.index[-1].date()}")

def combine(Wm):
    """Wm: monthly weights (index = month-end decision dates). Monthly rebalanced, weights drift within month,
    5 bps switching cost on sleeve changes."""
    nav = [1.0]; idx = [R.index[0]]
    months = R.index.to_period("M").unique()
    w_prev = None
    for m in months:
        rr = R[R.index.to_period("M") == m]
        dec = Wm[Wm.index.to_period("M") < m]
        if dec.empty: continue
        w = dec.iloc[-1].values.astype(float)
        if w.sum() == 0: continue
        cost = 0 if w_prev is None else np.abs(w - w_prev).sum() * 5e-4
        v = w * nav[-1] * (1 - cost)
        for d, row in rr.iterrows():
            v = v * (1 + row.values); nav.append(v.sum()); idx.append(d)
        w_prev = v / v.sum()
    return pd.Series(nav, index=idx)

def sh(r):
    e = r - rf.reindex(r.index).fillna(0); return e.mean() / e.std() * np.sqrt(252)
me = R.resample("ME").last().index
full_sh = R.apply(sh).sort_values(ascending=False)
print("\nfull-sample Sharpe ranking (base costs):"); print(full_sh.head(8).round(2).to_string())
print("\ncorrelation of top-8:"); print(R[full_sh.index[:8]].corr().round(2).to_string())

out = {}
# 1) HINDSIGHT top 5, equal weight
top5 = list(full_sh.index[:5])
Wm = pd.DataFrame(0.0, index=me, columns=R.columns); Wm[top5] = 0.2
out["Hindsight top-5 (EW)"] = combine(Wm)
# 1b) hindsight top 5, inverse-vol (risk parity across sleeves), trailing 126d
vol = R.rolling(126).std().resample("ME").last()
Wiv = (1 / vol[top5]).div((1 / vol[top5]).sum(axis=1), axis=0).reindex(columns=R.columns).fillna(0)
out["Hindsight top-5 (inv-vol)"] = combine(Wiv)
# 2) WALK-FORWARD: each January pick top 5 by trailing 3y / 5y Sharpe, equal weight
for lb in (3, 5):
    Wwf = pd.DataFrame(0.0, index=me, columns=R.columns)
    for d in me:
        hist = R.loc[:d].iloc[-252 * lb:]
        if len(hist) < 252 * 2: continue
        if d.month == 12 or Wwf.loc[:d].iloc[:-1].sum().sum() == 0:  # pick at year-end (or first eligible)
            pick = hist.apply(sh).nlargest(5).index
            cur = pd.Series(0.0, index=R.columns); cur[pick] = 0.2
        Wwf.loc[d] = cur if 'cur' in dir() else 0
    out[f"Walk-forward top-5 ({lb}y lookback)"] = combine(Wwf)
# 3) all strategies equal weight (no selection at all)
Wall = pd.DataFrame(1 / R.shape[1], index=me, columns=R.columns); out["All strategies EW"] = combine(Wall)
# benchmarks on same dates
for lab, uni in [("Passive 8-ETF EW", MULTI), ("SPY", ["SPY"])]:
    P, T, Rb, kw = bench(uni, "2006-01-01"); n = sim_weights(P, T, Rb, slip_bps=5)["nav"]
    out[lab] = n.loc[R.index[0]:]
P = panel(["SPY", "IEF"], "2006-01-01"); n6040 = sim_weights(P, pd.DataFrame({"SPY": 0.6, "IEF": 0.4}, index=P["c"].index), sched(P["c"].index, "M"), slip_bps=5)["nav"]
out["60/40 SPY/IEF"] = n6040.loc[R.index[0]:]

rows = []
for k, nav in out.items():
    nav = nav.dropna(); m = metrics(nav, RF_D)
    y26 = nav.loc["2026"]; h1 = metrics(nav.loc[:"2016"], RF_D)["Sharpe"]; h2 = metrics(nav.loc["2017":"2025"], RF_D)["Sharpe"]
    rows.append(dict(Portfolio=k, CAGR=m["CAGR"], Vol=m["Vol"], Sharpe=m["Sharpe"], MaxDD=m["MaxDD"], Calmar=m["Calmar"],
                     **{"Sh 07-16": h1, "Sh 17-25": h2, "2026 YTD": y26.iloc[-1] / y26.iloc[0] - 1}))
pd.set_option("display.width", 250)
print("\n", pd.DataFrame(rows).set_index("Portfolio").round(3).to_string())
print("\nhindsight top-5 =", top5)
pickle.dump(out, open("combo_navs.pkl", "wb"))
