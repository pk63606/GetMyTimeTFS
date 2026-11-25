"""W18 deep-dive: yearly/monthly stats, drawdowns, holdings, crisis behaviour, live signal."""
import warnings; warnings.filterwarnings("ignore")
from strats_w import *
P = panel(MULTI, "2006-01-01"); c = P["c"]; ret = c.pct_change(); R = sched(c.index, "M")

def w18_weights(lb=126, top=3, tv=0.15, vlb=42, ml=1.0, cap=0.40):
    m = c / c.shift(lb) - 1
    base = eqw(m.where(m > 0).rank(axis=1, ascending=False) <= top, cap)
    pr = (base.shift(1) * ret).sum(axis=1); vol = pr.rolling(vlb).std() * np.sqrt(252)
    scale = (tv / vol).clip(upper=ml).fillna(0)
    return base.mul(scale, axis=0), base, scale, m

out = {}
for lab, ml in [("W18 unlevered (1.0x)", 1.0), ("W18 published (2.0x)", 2.0)]:
    W, base, scale, mom = w18_weights(ml=ml)
    r = sim_weights(P, W, R, slip_bps=10)
    out[lab] = dict(nav=r["nav"].loc["2007":], res=r, W=W, base=base, scale=scale, mom=mom)
spy = sim_weights(panel(["SPY"], "2006-01-01"), pd.DataFrame(1.0, index=c.index, columns=["SPY"]), R, slip_bps=0)["nav"].loc["2007":]
P6 = panel(["SPY", "IEF"], "2006-01-01")
s6040 = sim_weights(P6, pd.DataFrame({"SPY": .6, "IEF": .4}, index=P6["c"].index), sched(P6["c"].index, "M"), slip_bps=5)["nav"].loc["2007":]
navs = {k: v["nav"] for k, v in out.items()}; navs["SPY"] = spy; navs["60/40"] = s6040

pd.set_option("display.width", 220)
print("== Headline (2007-01 -> 2026-11-24, 10 bps slippage + IBKR commission)")
rows = []
for k, n in navs.items():
    m = metrics(n, RF_D); mr = n.resample("ME").last().pct_change().dropna()
    rows.append(dict(Strat=k, CAGR=m["CAGR"], Vol=m["Vol"], Sharpe=m["Sharpe"], MaxDD=m["MaxDD"], Calmar=m["Calmar"],
                     PosMonths=(mr > 0).mean(), BestM=mr.max(), WorstM=mr.min(), Skew=mr.skew()))
print(pd.DataFrame(rows).set_index("Strat").round(3).to_string())

print("\n== Calendar-year returns")
yr = pd.DataFrame({k: n.resample("YE").last().pct_change() for k, n in navs.items()})
first = {k: n.loc["2007"].iloc[-1] / n.iloc[0] - 1 for k, n in navs.items()}
yr.iloc[0] = pd.Series(first)
yr.index = yr.index.year
print((yr * 100).round(1).to_string())

print("\n== Worst drawdowns, unlevered W18")
n = navs["W18 unlevered (1.0x)"]; dd = n / n.cummax() - 1
eps = []; in_dd = False
for d, v in dd.items():
    if v < 0 and not in_dd: in_dd, start = True, d
    if in_dd and v == 0:
        seg = dd.loc[start:d]; eps.append((start.date(), seg.idxmin().date(), d.date(), seg.min(), (d - start).days)); in_dd = False
if in_dd:
    seg = dd.loc[start:]; eps.append((start.date(), seg.idxmin().date(), "not recovered", seg.min(), (dd.index[-1] - start).days))
print(pd.DataFrame(sorted(eps, key=lambda e: e[3])[:6], columns=["Start", "Trough", "Recovered", "Depth", "Days"]).round(3).to_string(index=False))

print("\n== Crisis windows (total return)")
crises = {"GFC 2007-10..2009-03": ("2007-10-09", "2009-03-09"), "2011 Euro/US downgrade": ("2011-04-29", "2011-10-03"),
          "2015-16 China/oil": ("2015-07-20", "2016-02-11"), "Q4 2018": ("2018-09-20", "2018-12-24"), "COVID crash": ("2020-02-19", "2020-03-23"),
          "2022 bear": ("2022-01-03", "2022-10-12"), "2023 regional banks": ("2023-03-08", "2023-03-24"),
          "Aug 2024 VIX spike": ("2024-07-16", "2024-08-07"), "Apr 2025 tariff shock": ("2025-02-19", "2025-04-08")}
cr = {}
for k, (a, b) in crises.items():
    cr[k] = {s: navs[s].loc[a:b].iloc[-1] / navs[s].loc[a:b].iloc[0] - 1 for s in navs}
print((pd.DataFrame(cr).T * 100).round(1).to_string())

print("\n== Behaviour (unlevered)")
o = out["W18 unlevered (1.0x)"]
mreb = o["W"][R].loc["2007":]
held = (mreb > 0)
print("avg names held:", round(held.sum(axis=1).mean(), 2), "| months fully in T-bills:", f"{(held.sum(axis=1) == 0).mean():.1%}",
      "| avg gross exposure:", f"{mreb.sum(axis=1).mean():.2f}", "| exposure <0.6 in", f"{(mreb.sum(axis=1) < 0.6).mean():.0%} of months")
print("share of months each ETF is held:"); print((held.mean() * 100).round(0).sort_values(ascending=False).to_string())
print("turnover/yr:", round(o["res"]["turnover"] / (len(P["c"].loc['2006':]) / 252), 2), "x | fills/yr:", round(o["res"]["trades"] / 20.8, 1))
mr = n.resample("ME").last().pct_change().dropna(); sm = spy.resample("ME").last().pct_change().reindex(mr.index)
beta = np.cov(mr, sm)[0, 1] / sm.var()
print(f"monthly corr to SPY {mr.corr(sm):.2f}, beta {beta:.2f}; down-capture (SPY<0 months): {mr[sm<0].mean()/sm[sm<0].mean():.2f}, up-capture: {mr[sm>0].mean()/sm[sm>0].mean():.2f}")
rs = (n.pct_change() - RF_D.reindex(n.index)).rolling(756)
roll = (rs.mean() / rs.std() * np.sqrt(252)).dropna()
print(f"rolling 3y Sharpe: min {roll.min():.2f} ({roll.idxmin().date()}), median {roll.median():.2f}, max {roll.max():.2f}, share <0: {(roll<0).mean():.0%}")

print("\n== Live signal (data through", c.index[-1].date(), ")")
m6 = (c.iloc[-1] / c.iloc[-127] - 1).sort_values(ascending=False)
print("6-month returns:", ", ".join(f"{k} {v:+.1%}" for k, v in m6.items()))
W, base, scale, mom = w18_weights(ml=1.0)
print("current vol-scale (1.0x cap):", round(scale.iloc[-1], 2), "| current target weights if month ended today:")
print((W.iloc[-1][W.iloc[-1] > 0] * 100).round(1).to_string())
last_reb = R[R].index[R[R].index <= c.index[-1]][-1]
print("held since last rebalance (", last_reb.date(), "):", ", ".join(f"{k} {v:.1%}" for k, v in W.loc[last_reb][W.loc[last_reb] > 0].items()))
pd.to_pickle(navs, "w18_navs.pkl")
