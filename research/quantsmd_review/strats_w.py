from engine import *

SECT = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
MULTI = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]
FX = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"]
FUT = ["ES=F", "NQ=F", "ZN=F", "CL=F", "GC=F", "ZC=F"]
END = None  # run through latest data (2026-11-24); library stops 2026-01-01


def eqw(active, cap=1.0):
    a = active.astype(float)
    return a.div(a.sum(axis=1), axis=0).fillna(0.0).clip(upper=cap)


def hold_state(enter, exit_):
    """Stateful long flag: enter when enter=True, stay until exit_=True."""
    E, X = enter.values, exit_.values
    out = np.zeros(E.shape)
    st = np.zeros(E.shape[1], bool)
    for i in range(len(E)):
        st = np.where(~st & E[i], True, np.where(st & X[i], False, st))
        out[i] = st
    return pd.DataFrame(out, index=enter.index, columns=enter.columns)


def erc(cov, iters=200):
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(iters):
        m = cov @ w
        rc = w * m
        w = w * (rc.mean() / np.maximum(rc, 1e-12)) ** 0.5
        w /= w.sum()
    return w


def W(name, **kw):
    """Return (P, target, rebal, sim kwargs, description)."""
    if name == "W01":
        P = panel(SECT, "1999-01-01", END); c = P["c"]
        sig = (sma(c, 50) > sma(c, 200))
        return P, eqw(sig, 0.25), sched(c.index, "D"), {}, "Sector SMA50>200, daily"
    if name == "W02":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]
        sig = (sma(c, 50) > sma(c, 200))
        return P, eqw(sig, 0.30), sched(c.index, "M"), dict(drift_band=0.05), "Multi SMA50>200, monthly + 5% drift"
    if name == "W03":
        P = panel(SECT, "1999-01-01", END); c = P["c"]; r = rsi(c)
        sig = hold_state(r < kw.get("lo", 35), r > kw.get("hi", 60))
        return P, eqw(sig, 0.25), sched(c.index, "W"), {}, "Sector RSI<35 / >60, weekly"
    if name == "W04":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]; m = c / c.shift(252) - 1
        rk = m.where(m > 0).rank(axis=1, ascending=False)
        return P, eqw(rk <= 2, 0.5), sched(c.index, "Q"), {}, "Dual mom top2 12m, quarterly"
    if name == "W05":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]
        iv = 1 / (c.pct_change().rolling(63).std() * np.sqrt(252))
        w = iv.div(iv.sum(axis=1), axis=0).fillna(0).clip(upper=0.35)
        return P, w, sched(c.index, "M"), {}, "Inverse-vol 63d, monthly"
    if name == "W06":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]
        on = c["SPY"] > sma(c["SPY"], 200)
        a = pd.DataFrame(False, index=c.index, columns=c.columns)
        for x in ["SPY", "EFA", "EEM", "DBC", "VNQ"]:
            a[x] = on
        for x in ["TLT", "IEF", "GLD"]:
            a[x] = ~on
        a[sma(c["SPY"], 200).isna()] = False
        w = eqw(a, 0.5)
        chg = (w.diff().abs().sum(axis=1) > 0.01)
        return P, w, chg, {}, "SPY>200d risk-on else TLT/IEF/GLD"
    if name == "W10":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]
        sig = (sma(c, 50) > sma(c, 200))
        return P, eqw(sig, 0.30), sched(c.index, "M"), dict(breaker=(0.15, 10)), "Multi trend monthly + 15% DD breaker"
    if name == "W11":
        P = panel(MULTI, "2006-01-01", END); c = P["c"]; m = c / c.shift(126) - 1
        rk = m.rank(axis=1, ascending=False)
        return P, eqw(rk <= 3, 0.4), sched(c.index, "Q"), {}, "Top3 6m mom, quarterly (TE gate omitted)"
    if name == "W12":
        P = panel(SECT, "1999-01-01", END); c = P["c"]; m = (c / c.shift(63) - 1)
        mm = m.clip(lower=0).where(m > 0, 0)
        w = mm.div(mm.sum(axis=1), axis=0).fillna(0).clip(upper=0.35)
        return P, w, pd.Series(False, index=c.index), dict(drift_band=0.10, partial=True), "Sector 3m mom tilt, 10% drift band"
    if name in ("W13", "W14"):
        pair = ["KO", "PEP"] if name == "W13" else ["EWA", "EWC"]
        P = panel(pair, "1999-01-01", END); c = P["c"]
        la, lb = np.log(c[pair[0]]), np.log(c[pair[1]])
        if name == "W13":
            sp = la - lb
        else:
            beta = la.rolling(60).cov(lb) / lb.rolling(60).var(); sp = la - beta * lb
        z = (sp - sp.rolling(60).mean()) / sp.rolling(60).std()
        st = 0; s = np.zeros(len(z))
        for i, zi in enumerate(z.values):
            if np.isnan(zi): st = 0
            elif st == 0: st = -1 if zi > 2 else (1 if zi < -2 else 0)
            elif abs(zi) < 0.5: st = 0
            s[i] = st
        w = pd.DataFrame({pair[0]: s * 0.5, pair[1]: -s * 0.5}, index=c.index)
        chg = w.diff().abs().sum(axis=1) > 0
        return P, w, chg, {}, f"Pairs {pair[0]}/{pair[1]} z 2/0.5"
    if name in ("W15", "W16"):
        P = panel(SECT, "1999-01-01", END); c = P["c"]
        lb = 252 if name == "W15" else 21
        m = c / c.shift(lb) - 1
        rk = m.rank(axis=1, ascending=False); rk_lo = m.rank(axis=1, ascending=True)
        top, bot = (rk <= 3), (rk_lo <= 3)
        if name == "W16": top, bot = bot, top
        w = eqw(top) * 0.5 - eqw(bot) * 0.5
        w[m.isna().any(axis=1)] = 0
        return P, w, sched(c.index, "M" if name == "W15" else "W"), {}, ("XS mom L/S 12m monthly" if name == "W15" else "XS reversal L/S 1m weekly")
    if name in ("W17", "W18"):
        P = panel(MULTI, "2006-01-01", END); c = P["c"]; ret = c.pct_change()
        if name == "W17":
            base = eqw(sma(c, 50) > sma(c, 200), 0.34); tv, lb, ml = 0.10, 63, 1.5
        else:
            m = c / c.shift(126) - 1
            base = eqw(m.where(m > 0).rank(axis=1, ascending=False) <= 3, 0.40); tv, lb, ml = 0.15, 42, 2.0
        pr = (base.shift(1) * ret).sum(axis=1)  # realised vol of the held book
        vol = pr.rolling(lb).std() * np.sqrt(252)
        scale = (tv / vol).clip(upper=ml).fillna(0)
        return P, base.mul(scale, axis=0), sched(c.index, "M"), {}, f"Vol-target {int(tv*100)}% max {ml}x"
    if name in ("W19", "W20"):
        uni, lb, cap, start = (MULTI, 63, 1.0, "2006-01-01") if name == "W19" else (SECT, 126, 0.25, "1999-01-01")
        P = panel(uni, start, END); c = P["c"]; ret = c.pct_change()
        reb = sched(c.index, "M")
        w = pd.DataFrame(0.0, index=c.index, columns=c.columns)
        for i in np.where(reb.values)[0]:
            if i < lb: continue
            cv = ret.iloc[i - lb + 1:i + 1].cov().values
            ww = np.minimum(erc(cv), cap)
            w.iloc[i] = ww
        return P, w, reb, {}, f"ERC {lb}d, cap {cap}"
    if name == "W21":
        P = panel(SECT, "1999-01-01", END); c = P["c"]
        mid = sma(c, 20); lo = mid - 2 * c.rolling(20).std()
        sig = hold_state(c < lo, c > mid)
        return P, eqw(sig, 0.25), sched(c.index, "D"), {}, "Bollinger(20,2) buy lower, exit mid"
    if name == "W22":
        P = panel(SECT, "1999-01-01", END); c = P["c"]
        macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
        sig = macd > macd.ewm(span=9, adjust=False).mean()
        return P, eqw(sig, 0.25), sched(c.index, "D"), {}, "MACD>signal, daily"
    if name in ("W23", "W24"):
        P = panel(FX, "2004-01-01", END); c = P["c"]
        if name == "W23":
            m = c.pct_change(126); sgn = np.sign(m).fillna(0)
            iv = 1 / (c.pct_change().rolling(63).std() * np.sqrt(252))
            raw = sgn * iv; w = raw.div(raw.abs().sum(axis=1), axis=0).fillna(0)
        else:
            m = c.pct_change(63)
            w = eqw(m.rank(axis=1, ascending=False) <= 1) * 0.5 - eqw(m.rank(axis=1) <= 1) * 0.5
            w[m.isna().any(axis=1)] = 0
        return P, w, sched(c.index, "M"), dict(comm=False, short_fee=0.0), "FX spot (no carry)"
    if name == "W25":
        uni = kw.get("uni", FUT)
        P = panel(uni, kw.get("start", "2001-01-01"), END); c = P["c"]
        s = np.sign(sma(c, 63) - sma(c, 252))
        vol = c.pct_change().rolling(63).std() * np.sqrt(252)
        raw = s / vol; w = raw.div(raw.abs().sum(axis=1), axis=0).fillna(0)
        return P, w, sched(c.index, "M"), dict(comm=False, short_fee=0.0), "Futures trend 63/252 inv-vol"
    raise KeyError(name)


def bench(uni, start, kind="EW"):
    P = panel(uni, start, END); c = P["c"]
    w = pd.DataFrame(1.0 / len(uni), index=c.index, columns=c.columns)
    return P, w, sched(c.index, "M"), {}
