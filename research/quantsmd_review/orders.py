"""Bar-by-bar single-asset sleeve simulator for the O-series order strategies.

Each ETF (SPY, QQQ, IWM) is an independent sleeve that is 100% invested when
in a position and in T-bills otherwise; the portfolio is the equal-weight
average of sleeve returns (the library instead sizes 10-18% of NAV per name
and leaves the rest in zero-yield cash, which is why its CAGRs look tiny).

Fill rules on the bar AFTER the decision bar:
  market     -> open +/- slippage
  stop buy   -> open if open>=S else S if high>=S   (+ slippage)
  stop sell  -> open if open<=S else S if low<=S    (- slippage)
  limit buy  -> open if open<=L else L if low<L     (no slippage, must trade through)
  limit sell -> open if open>=L else L if high>L
  stop-limit -> stop trigger, but no fill if the open gaps past the limit
  same-bar stop & target both touched -> stop assumed first (conservative)
"""
from engine import *

ETF3 = ["SPY", "QQQ", "IWM"]


def sleeve(strategy, o, h, l, c, raw, rf, ind, slip_bps=5.0, comm=True, cap0=CAPITAL / 3):
    n = len(c)
    slip = slip_bps / 1e4
    eq = np.empty(n); eq[0] = cap0
    cash = cap0; sh = 0.0
    st = dict(pos=False, entry=None, pend=[], bars_in=0, hh=None, prev=0, i=0, nfill=0, trades=[])

    def fee(shares, px_raw):
        if not comm or shares == 0:
            return 0.0
        return min(max(1.0, 0.005 * abs(shares)), 0.01 * abs(shares) * px_raw)

    for t in range(1, n):
        cash *= (1 + rf[t])
        adjr = c[t] / raw[t] if raw[t] > 0 else 1.0
        # --- process pending orders on bar t
        new_pend = []
        filled_side = None
        for od in st["pend"]:
            if filled_side is not None and od.get("oco") and od["side"] == filled_side:
                continue  # OCO sibling cancelled
            typ, side = od["type"], od["side"]
            px = None
            if side == "buy" and st["pos"]:
                continue
            if side == "sell" and not st["pos"]:
                continue
            if typ == "mkt":
                px = o[t] * (1 + slip if side == "buy" else 1 - slip)
            elif typ == "stop":
                S = od["S"]
                if side == "buy":
                    if o[t] >= S: px = o[t] * (1 + slip)
                    elif h[t] >= S: px = S * (1 + slip)
                else:
                    if o[t] <= S: px = o[t] * (1 - slip)
                    elif l[t] <= S: px = S * (1 - slip)
            elif typ == "limit":
                L = od["L"]
                if side == "buy":
                    if o[t] <= L: px = o[t]
                    elif l[t] < L: px = L
                else:
                    if o[t] >= L: px = o[t]
                    elif h[t] > L: px = L
            elif typ == "stoplimit":
                S, L = od["S"], od["L"]
                if side == "buy":
                    if o[t] >= S:
                        if o[t] <= L: px = o[t] * (1 + slip)
                    elif h[t] >= S:
                        px = S * (1 + slip)
                else:
                    if od.get("armed"):
                        if o[t] >= L: px = o[t]
                        elif h[t] > L: px = L
                    elif o[t] <= S:
                        if o[t] >= L: px = o[t] * (1 - slip)
                        else: od["armed"] = True  # gapped through: now a resting limit
                    elif l[t] <= S:
                        px = S * (1 - slip)
            elif typ == "trail":
                stop = st["hh"] * (1 - od["p"])
                if o[t] <= stop: px = o[t] * (1 - slip)
                elif l[t] <= stop: px = stop * (1 - slip)
            if px is not None:
                if side == "buy":
                    sh = cash / px
                    f = fee(sh, px / adjr); sh = (cash - f) / px; cash = 0.0
                    st.update(pos=True, entry=px, bars_in=0, hh=max(h[t], px)); st["nfill"] += 1
                    filled_side = "buy"
                    # bracket children become active immediately (same bar check, stop first)
                    for ch in od.get("children", []):
                        new_pend.append(dict(ch))
                    br = [x for x in new_pend if x.get("bracket")]
                    if br:
                        S = [x for x in br if x["type"] == "stop"][0]["S"]; L = [x for x in br if x["type"] == "limit"][0]["L"]
                        if l[t] <= S:
                            px2 = S * (1 - slip); f = fee(sh, px2 / adjr); cash = sh * px2 - f
                            st["trades"].append(px2 / st["entry"] - 1); sh = 0.0; st.update(pos=False); st["nfill"] += 1
                            new_pend = [x for x in new_pend if not x.get("bracket")]
                        elif h[t] > L:
                            px2 = L; f = fee(sh, px2 / adjr); cash = sh * px2 - f
                            st["trades"].append(px2 / st["entry"] - 1); sh = 0.0; st.update(pos=False); st["nfill"] += 1
                            new_pend = [x for x in new_pend if not x.get("bracket")]
                else:
                    f = fee(sh, px / adjr); cash = sh * px - f
                    st["trades"].append(px / st["entry"] - 1)
                    sh = 0.0; st.update(pos=False); st["nfill"] += 1
                    new_pend = [x for x in new_pend if x["side"] != "sell"]
                    filled_side = "sell"
                continue
            od["age"] = od.get("age", 0) + 1
            if od.get("exp") is None or od["age"] < od["exp"]:
                new_pend.append(od)
        # bracket children handling on later bars
        if st["pos"]:
            br = [x for x in new_pend if x.get("bracket") and x.get("age", 0) >= 0]
            st["pend"] = new_pend
        else:
            st["pend"] = [x for x in new_pend if not x.get("bracket") and x["side"] == "buy"]
        if st["pos"]:
            st["bars_in"] += 1
            st["hh"] = max(st["hh"], h[t])
        eq[t] = cash + sh * c[t]
        st["i"] = t
        strategy(st, t, o, h, l, c, ind)
    return eq, st


def drop_side(st, side):
    st["pend"] = [x for x in st["pend"] if x["side"] != side]


# ---------------------------------------------------------------- strategies
def mk_cross(exit_kind=None, **p):
    """SMA(20/50) cross entries with optional protective exits (O01,O06,O08,O09,O11,O12)."""
    def f(st, t, o, h, l, c, ind):
        fast, slow = ind["f"][t], ind["s"][t]
        if np.isnan(slow):
            return
        sig = 1 if fast > slow else 0
        prev = st["prev"]
        if sig == 1 and prev == 0 and not st["pos"] and not any(x["side"] == "buy" for x in st["pend"]):
            od = dict(type="mkt", side="buy")
            if exit_kind == "bracket":
                od["children"] = [dict(type="stop", side="sell", S=c[t] * (1 - p["sl"]), bracket=True),
                                  dict(type="limit", side="sell", L=c[t] * (1 + p["tp"]), bracket=True)]
            st["pend"].append(od)
        elif st["pos"] and sig == 0 and prev == 1:
            st["pend"] = [dict(type="mkt", side="sell")]
        elif st["pos"] and exit_kind in ("stop", "stoplimit", "trail") and not any(x["side"] == "sell" for x in st["pend"]):
            if exit_kind == "stop":
                st["pend"].append(dict(type="stop", side="sell", S=st["entry"] * (1 - p["sl"])))
            elif exit_kind == "stoplimit":
                st["pend"].append(dict(type="stoplimit", side="sell", S=st["entry"] * (1 - p["sl"]), L=st["entry"] * (1 - p["sl"] - 0.005)))
            else:
                st["pend"].append(dict(type="trail", side="sell", p=p["trail"]))
        st["prev"] = sig
    return f


def mk_rsi(lo, hi, exit_kind=None, **p):
    """RSI entries (O02, O10, O13)."""
    def f(st, t, o, h, l, c, ind):
        r = ind["rsi"][t]
        if np.isnan(r):
            return
        if not st["pos"] and r < lo and not any(x["side"] == "buy" for x in st["pend"]):
            od = dict(type="mkt", side="buy")
            if exit_kind == "bracket":
                od["children"] = [dict(type="stop", side="sell", S=c[t] * (1 - p["sl"]), bracket=True),
                                  dict(type="limit", side="sell", L=c[t] * (1 + p["tp"]), bracket=True)]
            st["pend"].append(od)
        elif st["pos"] and exit_kind == "trail" and not any(x["side"] == "sell" for x in st["pend"]):
            st["pend"].append(dict(type="trail", side="sell", p=p["trail"]))
        if st["pos"] and r > hi:
            st["pend"] = [dict(type="mkt", side="sell")]
    return f


def o03(st, t, o, h, l, c, ind):
    r = ind["rsi"][t]
    if np.isnan(r):
        return
    pend = len(st["pend"]) > 0
    if not st["pos"] and not pend and r < 40:
        st["pend"].append(dict(type="limit", side="buy", L=c[t] * 0.985, exp=3))
    elif st["pos"] and not pend:
        st["pend"].append(dict(type="limit", side="sell", L=st["entry"] * 1.03, exp=3))


def o04(st, t, o, h, l, c, ind):
    tr = ind["s"][t]
    if np.isnan(tr):
        return
    pend = len(st["pend"]) > 0
    if not st["pos"] and not pend and c[t] > tr:
        st["pend"].append(dict(type="limit", side="buy", L=c[t] * 0.99, exp=2))
    elif st["pos"] and c[t] < tr:
        st["pend"] = [dict(type="mkt", side="sell")]
    elif st["pos"] and not pend:
        st["pend"].append(dict(type="limit", side="sell", L=st["entry"] * 1.04, exp=5))


def mk_breakout(stoplimit=False, hold=10):
    def f(st, t, o, h, l, c, ind):
        if t < 21:
            return
        if st["pos"] and st["bars_in"] >= hold:
            st["pend"] = [dict(type="mkt", side="sell")]
            return
        if not st["pos"] and not st["pend"]:
            S = c[t - 20:t].max() * 1.002
            if stoplimit:
                st["pend"].append(dict(type="stoplimit", side="buy", S=S, L=S * 1.004, exp=5))
            else:
                st["pend"].append(dict(type="stop", side="buy", S=S, exp=5))
    return f


def o14(st, t, o, h, l, c, ind):
    if st["pos"] and st["bars_in"] >= 10:
        st["pend"] = [dict(type="mkt", side="sell")]
        return
    if not st["pos"] and not st["pend"] and t % 5 == 0:
        # stop listed first => if both touch on the same bar we take the worse (higher) stop fill
        st["pend"] += [dict(type="stop", side="buy", S=c[t] * 1.02, exp=5, oco=True),
                       dict(type="limit", side="buy", L=c[t] * 0.98, exp=5, oco=True)]


O_DEFS = {
    "O01": (lambda: mk_cross(None), "SMA20/50 cross, market"),
    "O02": (lambda: mk_rsi(35, 60), "RSI<35 buy, >60 sell"),
    "O03": (lambda: o03, "RSI<40 limit -1.5%, exit limit +3% (no stop)"),
    "O04": (lambda: o04, "Close>SMA50, limit -1%, TP +4%, exit <SMA50"),
    "O05": (lambda: mk_breakout(False, 10), "Buy-stop 20d high, 10-bar exit"),
    "O06": (lambda: mk_cross("stop", sl=0.05), "SMA cross + 5% stop"),
    "O07": (lambda: mk_breakout(True, 12), "Stop-limit 20d high, 12-bar exit"),
    "O08": (lambda: mk_cross("stoplimit", sl=0.04), "SMA cross + 4% stop-limit"),
    "O09": (lambda: mk_cross("trail", trail=0.04), "SMA cross + 4% trailing"),
    "O10": (lambda: mk_rsi(38, 65, "trail", trail=0.05), "RSI<38 + 5% trailing, exit RSI>65"),
    "O11": (lambda: mk_cross("trail", trail=0.045), "SMA cross + 4% trail-limit (approx)"),
    "O12": (lambda: mk_cross("bracket", tp=0.06, sl=0.03), "SMA cross + bracket +6/-3"),
    "O13": (lambda: mk_rsi(35, 70, "bracket", tp=0.04, sl=0.02), "RSI<35 bracket +4/-2"),
    "O14": (lambda: o14, "OCO dip -2% / breakout +2%, 10-bar exit"),
}


def run_O(code, tickers=ETF3, start="2001-01-03", end=None, slip_bps=5.0, comm=True, strat=None):
    P = panel(tickers, start, end)
    eqs = []; tr = []; fills = 0; expo = []
    for x in tickers:
        o, h, l, c, raw = (P[k][x].values for k in ("o", "h", "l", "c", "raw"))
        cs = P["c"][x]
        ind = dict(f=sma(cs, 20).values, s=sma(cs, 50).values, rsi=rsi(cs).values)
        fn = strat or O_DEFS[code][0]()
        eq, st = sleeve(fn, o, h, l, c, raw, P["rf"].values, ind, slip_bps=slip_bps, comm=comm)
        eqs.append(pd.Series(eq, index=P["c"].index)); tr += st["trades"]; fills += st["nfill"]
    rets = pd.concat([e.pct_change() for e in eqs], axis=1).mean(axis=1).fillna(0)
    nav = CAPITAL * (1 + rets).cumprod()
    return nav, np.array(tr), fills, P
