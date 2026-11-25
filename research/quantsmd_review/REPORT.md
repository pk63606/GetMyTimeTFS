# quants.md / hft.md strategy library: independent re-test with realistic costs

*Run 2026-11-25. Data: Yahoo Finance daily, total-return adjusted, 1999 → 2026-11-24.*
*The library's own backtests end 2026-01-01, so 2026 YTD is a true out-of-sample stretch.*

## What was reviewed

- **hft.md** is a quant-education site. Its "books" are a reading list (Kahneman,
  Hull, Natenberg, Zhou's green book…) with no testable rules; the only trading
  content is conceptual HFT/market-making lessons.
- **The tradeable material is its sister site quants.md**: 50 strategies + 1
  sentiment demo, code in `QuantJourneyOrg/quantjourney-bt` (Apache-2.0).
  Every strategy with rules that could be re-run on public data was re-implemented here (49 of 51).
  Skipped: W26 (needs a proprietary sentiment feed) and the WF01–05 walk-forward
  wrappers (they re-validate W01/W03, covered below).

## Problems with the library's published numbers

1. **Weight strategies (W01–W25), including every headline winner, are charged
   1 bp per trade and zero slippage** (`TRANSACTION_COST_BPS = 1bp`,
   `FixedBpsWeightCostModel`), even the ones that rebalance daily.
2. **Order strategies size only 10–18 % of NAV per ETF across 3 ETFs, and idle cash earns 0 %.**
   That is why their CAGRs are 1–3 % and Sharpes negative. It says nothing about the signals.
3. **O03 "100 % win rate / profit factor ∞"** comes from having no stop. It sells
   only at +3 % and rode a -46 % drawdown.
4. **Intraday strategies were "tested" over 6 days to 9 weeks.** That is statistically meaningless.
5. **W01's published SMA(50/200) sits at the best point of the parameter grid.**
6. **FX tests ignore carry, and the futures tests use continuous series with roll gaps.**

## Method

- Signal at close *t*, fill at the open of *t+1*. Stops and limits are checked
  against the next bar's open, high and low, with gap-through fills at the open.
  When a stop and a target are both touched on the same bar, the stop is assumed first.
- **Commissions:** IBKR Fixed, $0.005/share, $1 minimum, 1 % maximum, on a $100k account.
- **Slippage, per side, on traded notional:** 0 (gross) / 5 bps (base) / 15 bps (stress),
  plus a full 0–100 bps sweep to find each strategy's break-even.
- **Financing:** cash earns T-bills (^IRX), leverage pays T-bill + 1 %, and shorts pay a 0.5 %/yr borrow fee.
- **Sizing for O-strategies:** each ETF is a full 1/3 sleeve, so the signals can be judged
  rather than the library's cash drag.
- **Survival bar:**
  1. Positive excess return after base costs.
  2. Sharpe ≥ simply holding the same universe passively (equal-weight, monthly).
  3. Holds in 2001–12 and 2013–25.
  4. Not a parameter spike.

Sharpe ratios in this report are *excess over T-bills*.

## Scorecard (base costs = 5 bps slippage + IBKR commission)

Passive benchmarks:
- Equal-weight sectors (1999–2026): Sharpe **0.45**, CAGR 9.0 %, max drawdown -54 %
- Equal-weight 8 multi-asset ETFs (2006–2026): Sharpe **0.43**, CAGR 6.4 %, max drawdown -38 %
- Equal-weight SPY/QQQ/IWM (2001–2026): Sharpe **0.43**, CAGR 9.1 %, max drawdown -55 %

"Break-even" is the slippage (bps per side) at which the strategy's Sharpe falls to its passive benchmark.

| ID | Strategy | CAGR | Sharpe | MaxDD | Turnover/yr | Break-even | Verdict |
|---|---|---|---|---|---|---|---|
| **W18** | Vol-target momentum (top-3 6m) | 11.1 % | **0.63** | -30 % | 9.3x | **39 bps** | **Survives** (see caveats) |
| **W05** | Inverse-vol 63d monthly | 6.0 % | **0.53** | -22 % | 0.9x | 97 bps | Survives, but the edge is mostly static allocation |
| W01 | Sector SMA50>200 daily | 7.8 % | 0.46 | -36 % | 4.0x | 7 bps | Same Sharpe as passive; cuts drawdown only |
| W11 | Top-3 6m momentum quarterly | 6.9 % | 0.43 | -29 % | 3.1x | 3 bps | ≈ passive |
| W20 | ERC sectors, 25 % cap | 8.3 % | 0.44 | -50 % | 0.6x | 0 | ≈ passive (no edge) |
| W02 | Multi-asset trend + drift band | 5.6 % | 0.41 | -20 % | 3.7x | 0 | Below passive; halves drawdown |
| W21 | Bollinger reversion | 7.1 % | 0.41 | -36 % | 19.9x | 2 bps | Cost-sensitive; fails |
| W03 | Weekly RSI reversion | 7.0 % | 0.38 | -53 % | 9.0x | 0 | Fails |
| W19 | Risk parity multi-asset | 5.4 % | 0.36 | -30 % | 3.5x | 0 | Fails |
| W10 | Trend + 15 % DD breaker | 4.6 % | 0.32 | -21 % | 3.2x | 0 | Fails |
| W17 | Vol-target trend 10 % | 4.8 % | 0.32 | -28 % | 3.7x | 0 | Fails |
| W25 | Futures trend (roll-gapped data) | 4.1 % | 0.32 | -18 % | 2.9x | n/a | Weak; see ETF-proxy variant |
| W06 | SPY 200d risk-on/off | 5.0 % | 0.31 | -29 % | 10.9x | 0 | Fails |
| W12 | Sector momentum tilt | 4.1 % | 0.21 | -43 % | 13.4x | 0 | Fails |
| W13 | KO/PEP pairs | 3.0 % | 0.17 | -23 % | 8.8x | 18 bps vs cash | Fails |
| W04 | Dual momentum quarterly | 2.6 % | 0.13 | -45 % | 3.0x | 0 | Fails |
| W14 | EWA/EWC pairs | 2.2 % | 0.05 | -14 % | 6.1x | 10 bps vs cash | Fails |
| W22 | MACD trend daily | 0.8 % | -0.02 | -63 % | 48x | 4 bps vs cash | **Killed by costs** |
| W15 | XS momentum L/S | 1.2 % | -0.07 | -34 % | 5.6x | 0 | Negative before costs |
| W16 | XS reversal L/S weekly | 0.6 % | -0.14 | -34 % | 34x | 2 bps vs cash | **Killed by costs** |
| W23/W24 | FX momentum | ~0.5 % | -0.1/-0.2 | -27/-33 % | | | Negative before costs |
| O12 | SMA cross + bracket +6/-3 | 4.2 % | 0.47 | -13 % | | 10 bps | Marginal; low exposure, small drawdown |
| O04 | Trend pullback limit | 6.0 % | 0.45 | -18 % | | 7 bps | Marginal |
| O05 | 20d breakout buy-stop | 5.7 % | 0.46 | -34 % | | 6 bps | Fails at stress (0.20) |
| O14 | OCO dip/breakout | 7.4 % | 0.43 | -40 % | | 5 bps | Fails |
| O01/O18 | SMA20/50 cross | 6.5 % | 0.42 | -27 % | | 1 bp | ≈ passive |
| O09/O11 | SMA cross + trailing stop | 4.1 % | 0.41/0.39 | -13/-15 % | | 2/0 bps | Fails |
| O07 | Stop-limit breakout | 5.1 % | 0.38 | -16 % | | 3 bps | Fails |
| O03 | RSI dip limit, no stop | 6.8 % | 0.36 | -46 % | | 0 | Fails ("100 % win rate" is an artifact) |
| O06/O08 | SMA cross + stop / stop-limit | 4.7/5.1 % | 0.32/0.35 | -31/-27 % | | 0 | Fails |
| O02 | RSI 35/60 market | 3.7 % | 0.20 | -43 % | | 0 | Fails |
| O10 | RSI + trailing stop | 2.2 % | 0.10 | -51 % | | 0 | Fails |
| O13 | RSI bracket +4/-2 | 1.2 % | -0.05 | -31 % | | 3 bps vs cash | **Killed by costs** |
| W07/W08/W09/O15/O16 | Intraday | | | | | | **All negative after 1–2 bps** (W09: +3.4 % gross over 2 years → negative at 2 bps; others negative gross on 60 days) |

## Survivors in detail

### 1. W18: Vol-targeted momentum (the only real candidate)

**Rules:**
- Universe: SPY, EFA, EEM, TLT, IEF, GLD, DBC, VNQ.
- At each month-end, hold the top 3 by 6-month return, only those with a positive return, equal-weighted.
- Scale the book so its 42-day realised volatility is 15 %.

**Results:**
- At base costs: CAGR 11.1 %, Sharpe 0.63, max drawdown -30 %.
- Benchmarks: passive Sharpe 0.43; SPY Sharpe 0.53 over the same period.
- It beat its benchmark in **both** halves: Sharpe 0.80 vs 0.46 in 2001–12, and 0.61 vs 0.44 in 2013–25.
- **83 % of 48 parameter variants** beat the passive benchmark. The tested ranges were lookback 63–252, top 2–4, and volatility target 10–20 %, with and without leverage.
- Break-even is about 39 bps per side against the benchmark. Sharpe is still 0.51 at 25 bps.
- **The unlevered version is better:** with max leverage 1.0x, Sharpe is 0.66, CAGR 9.2 % and max drawdown -21 %, at half the turnover. Use that version.

**Caveats:**
- The monthly information-ratio t-stat is **1.84, which is not significant at 95 %.**
- The published 126-day/top-3 setting sits near the best region of the grid. 63-day and 252-day lookbacks are weaker (Sharpe 0.45–0.55).
- **2026 out-of-sample: -5 %**, against +4 % for the passive basket.

### 2. W05: Inverse-volatility allocation

- Sharpe 0.53 vs 0.43 passive, and it survives any realistic cost: turnover is 0.9x a year, with break-even above 90 bps.
- **However, a frozen set of inverse-vol weights scores 0.49.** The edge is "hold more bonds and less EM/commodities," not timing.
- It underperformed in 2013–25 (Sharpe 0.39 vs 0.44) and was flat in 2026.
- It is a reasonable *allocation*, not an alpha source.

### 3. Trend filters (W01, W02, O12, O04): drawdown control, not alpha

They roughly match passive Sharpe and cut max drawdown by a third to three quarters. However:
- W01's published 50/200 setting is the best of a 3×4 grid. Most neighbouring settings score 0.24–0.41, below passive.
- They survive costs only because they trade rarely.

### Not in the library: long-only trend on six ETF proxies

The W25 trend rule (63/252 SMA sign, inverse-vol weights) was run on ETFs instead of
roll-gapped futures, keeping only the long side. The six ETFs were SPY, QQQ, IEF, TLT, GLD and DBC.

**Results:**
- Sharpe 0.80, max drawdown -10 %, turnover 1.5x a year.
- Sharpe was 0.70–0.80 across almost the whole fast/slow grid, and positive in every sub-period.

**But:**
- The **untimed** inverse-vol mix of the same six ETFs already scores 0.72, with a -19 % drawdown. Most of the Sharpe is hindsight in picking the universe (QQQ, GLD, bonds).
- On the library's 8-ETF universe the variant scores 0.53; on sectors it scores 0.44.
- The trend overlay's real contribution is about +0.08 Sharpe and a halved drawdown.

## Bottom line

- **Nothing in the library is a free-money edge once costs are realistic.**
- **About 20 of the 49 strategies tested are negative, cost-killed, or no better than holding their own universe.**
- **What survives is portfolio construction rather than prediction:** momentum selection with volatility targeting (W18, unlevered), inverse-vol weighting (W05), and slow trend filters that trade lower return for much smaller drawdowns.
- **Short-horizon strategies fail at retail costs:** mean reversion, MACD, breakouts with time exits, pairs, cross-sectional L/S and every intraday strategy.
- **W18 itself is not statistically proven:** its t-stat is 1.84 and it lost money in 2026 out-of-sample.
- **Paper-trade W18 unlevered before committing capital.**

## Reproduce

```bash
pip install yfinance pandas numpy
python3 dl.py            # downloads data/raw.pkl
python3 run_w.py         # weight strategies, 4 cost scenarios
python3 run_o.py         # order strategies, 3 cost scenarios
python3 breakeven.py     # break-even slippage table
python3 robust.py        # sub-periods, 2026 OOS, t-stats
python3 w18grid.py       # W18 parameter/leverage/cost grid
python3 misc.py; python3 lotrend.py; python3 intraday.py
```

*Educational research, not investment advice.*
