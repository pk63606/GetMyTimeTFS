"""Independent re-test engine for the quants.md / QuantJourney strategy library.

Conventions
- Decisions use data up to and including the close of day t.
- Fills happen at the OPEN of day t+1 (market / MOO). Stops and limits are
  checked against the t+1 bar's open/high/low (gap-through fills at the open).
- Prices are total-return adjusted (Adj Close ratio applied to O/H/L).
- Costs per fill = slippage_bps * notional + IBKR Fixed commission
  ($0.005/share, $1 min, 1% max) computed on the unadjusted share price.
- Idle cash earns the 13-week T-bill (^IRX). Borrowed cash (leverage) pays
  T-bill + 1%. Short positions pay a 0.5%/yr borrow fee (ETFs, GC names).
"""
from __future__ import annotations
import numpy as np, pandas as pd

import os
RAW = pd.read_pickle(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw.pkl"))
ADJ = RAW["Adj Close"]
CLOSE = RAW["Close"]
RATIO = ADJ / CLOSE
OPEN = RAW["Open"] * RATIO
HIGH = RAW["High"] * RATIO
LOW = RAW["Low"] * RATIO
RF_D = (RAW["Close"]["^IRX"].ffill().fillna(0) / 100.0 / 252.0)
CAPITAL = 100_000.0


def panel(tickers, start, end=None):
    idx = ADJ[tickers].dropna(how="any").loc[start:end].index
    f = lambda d: d.loc[idx, tickers].ffill()
    return dict(c=f(ADJ), o=f(OPEN), h=f(HIGH), l=f(LOW), raw=f(CLOSE), rf=RF_D.reindex(idx).ffill().fillna(0))


# ---------------------------------------------------------------- indicators
def sma(x, n):
    return x.rolling(n, min_periods=n).mean()


def rsi(x, n=14):
    d = x.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


# ---------------------------------------------------------------- weight engine
def commission(trade_dollars, px):
    sh = np.abs(trade_dollars) / px
    c = np.maximum(1.0, 0.005 * sh)
    c = np.minimum(c, 0.01 * np.abs(trade_dollars))
    return np.where(np.abs(trade_dollars) > 0, c, 0.0)


def sim_weights(P, target, rebal, slip_bps=5.0, comm=True, min_trade=0.0025,
                drift_band=None, partial=False, short_fee=0.005, lev_spread=0.01,
                breaker=None):
    """target: DataFrame of target weights decided at close t (index = P dates).
    rebal: bool Series, True where a rebalance decision is taken at close t.
    drift_band: if set, also rebalance (any day) when |w - target| > band.
    partial: only trade the names outside the band.
    breaker: (dd_trigger, cooldown_days) -> flatten on drawdown, re-enter after cooldown at next rebal.
    """
    c, o, raw, rf = P["c"].values, P["o"].values, P["raw"].values, P["rf"].values
    T = target.reindex(P["c"].index).fillna(0.0).values
    R = rebal.reindex(P["c"].index).fillna(False).values
    n, k = c.shape
    h = np.zeros(k); cash = CAPITAL
    nav = np.empty(n); nav[0] = CAPITAL
    pending = None; pmask = None
    turnover = 0.0; costs = 0.0; ntr = 0; expo = np.zeros(n)
    peak = CAPITAL; flat_until = -1; flat = False
    for t in range(1, n):
        # overnight move on held positions, cash accrual / financing
        h = h * (o[t] / c[t - 1])
        r = rf[t]
        cash = cash * (1 + r) if cash >= 0 else cash * (1 + r + lev_spread / 252)
        h = np.where(h < 0, h * (1 + short_fee / 252), h)  # borrow fee grows short liability
        # execute pending orders at the open
        if pending is not None:
            NAV = h.sum() + cash
            desired = pending * NAV
            trade = desired - h
            mask = np.abs(trade) >= min_trade * NAV
            if pmask is not None:
                mask &= pmask
            trade = np.where(mask, trade, 0.0)
            cst = np.abs(trade).sum() * slip_bps / 1e4
            if comm:
                cst += commission(trade, raw[t - 1]).sum()
            h = h + trade
            cash -= trade.sum() + cst
            turnover += np.abs(trade).sum() / NAV
            costs += cst; ntr += int(mask.sum())
            pending = None
        # intraday move
        h = h * (c[t] / o[t])
        NAV = h.sum() + cash
        nav[t] = NAV
        expo[t] = np.abs(h).sum() / NAV
        # decision at close
        w_now = h / NAV
        if breaker is not None:
            peak = max(peak, NAV)
            if not flat and NAV < peak * (1 - breaker[0]):
                flat = True; flat_until = t + breaker[1]
                pending = np.zeros(k); pmask = None
                continue
            if flat:
                if t < flat_until:
                    continue
                if R[t]:
                    flat = False; peak = NAV
                else:
                    continue
        if R[t]:
            pending = T[t].copy(); pmask = None
        elif drift_band is not None:
            out = np.abs(w_now - T[t]) > drift_band
            if out.any():
                pending = T[t].copy()
                pmask = out if partial else None
    s = pd.Series(nav, index=P["c"].index)
    return dict(nav=s, turnover=turnover, costs=costs, trades=ntr, expo=pd.Series(expo, index=s.index))


def sched(idx, kind):
    s = pd.Series(idx, index=idx)
    if kind == "D":
        return pd.Series(True, index=idx)
    if kind == "W":  # Friday (or last day of the week)
        wk = s.dt.to_period("W-FRI")
        return wk != wk.shift(-1)
    if kind == "M":
        m = s.dt.to_period("M")
        return m != m.shift(-1)
    if kind == "Q":
        q = s.dt.to_period("Q")
        return q != q.shift(-1)
    raise ValueError(kind)


# ---------------------------------------------------------------- metrics
def metrics(nav, rf, turnover=None, costs=None, trades=None, expo=None):
    nav = nav.dropna()
    r = nav.pct_change().dropna()
    rfr = rf.reindex(r.index).fillna(0)
    yrs = len(r) / 252
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    ex = r - rfr
    sharpe = ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan
    dd = (nav / nav.cummax() - 1).min()
    rf_cagr = (1 + rfr).prod() ** (1 / yrs) - 1
    out = dict(CAGR=cagr, ExCAGR=cagr - rf_cagr, Vol=r.std() * np.sqrt(252), Sharpe=sharpe, MaxDD=dd,
               Calmar=cagr / abs(dd) if dd < 0 else np.nan, Years=yrs)
    if turnover is not None:
        out["TurnY"] = turnover / yrs
    if costs is not None:
        out["CostDragY"] = costs / CAPITAL / yrs  # rough, $ of starting capital
    if trades is not None:
        out["Fills/yr"] = trades / yrs
    if expo is not None:
        out["AvgExpo"] = expo.iloc[1:].mean()
    return out
