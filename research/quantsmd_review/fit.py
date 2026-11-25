"""How W18 fits next to the live SPX options books (OptionOmega backtests, month-end net liquidity)."""
import warnings; warnings.filterwarnings("ignore")
from strats_w import *
navs = pd.read_pickle("w18_navs.pkl")
w18 = navs["W18 unlevered (1.0x)"]; w18L = navs["W18 published (2.0x)"]; spy = navs["SPY"]
rf_m = (1 + RF_D).cumprod()
books = {k: pd.read_csv(f"optionomega/{k}_LIVE_monthly.csv", parse_dates=["date"]).set_index("date")["netLiquidity"] for k in ["4814", "5359", "6849", "8038"]}

def at(s, dates):  # value of a daily series as of each date
    return s.reindex(s.index.union(dates)).ffill().reindex(dates)

def stats(r, rfr):
    ex = r - rfr; nav = (1 + r).cumprod()
    yrs = len(r) / 12
    return dict(CAGR=nav.iloc[-1] ** (1 / yrs) - 1, Vol=r.std() * np.sqrt(12), Sharpe=ex.mean() / ex.std() * np.sqrt(12),
                MaxDD_m=(nav / nav.cummax() - 1).min(), WorstM=r.min())

pd.set_option("display.width", 230)
corr_rows, blend_rows, stress_rows = [], [], []
for k, b in books.items():
    d = b.index
    rb = b.pct_change().dropna()
    rw = at(w18, d).pct_change().dropna(); rwL = at(w18L, d).pct_change().dropna(); rs = at(spy, d).pct_change().dropna()
    rfr = at(rf_m, d).pct_change().dropna()
    corr_rows.append(dict(Book=k, Months=len(rb), Span=f"{d[0]:%Y-%m}..{d[-1]:%Y-%m}",
                          **{"corr(book,W18)": rb.corr(rw), "corr(book,SPY)": rb.corr(rs), "corr(W18,SPY)": rw.corr(rs)}))
    # stress: book's 6 worst months
    worst = rb.nsmallest(6).index
    for dt in worst:
        stress_rows.append(dict(Book=k, Month=f"{dt:%Y-%m}", Book_ret=rb[dt], W18_ret=rw[dt], SPY_ret=rs[dt]))
    # blends
    for mode, x in [("book only", 0), ("split 10% W18", .10), ("split 20% W18", .20), ("split 30% W18", .30),
                    ("overlay +25% W18", .25), ("overlay +50% W18", .50)]:
        if mode.startswith("split") or x == 0:
            r = (1 - x) * rb + x * rw
        else:  # W18 bought with cash the book holds anyway: adds W18 excess over T-bills
            r = rb + x * (rw - rfr)
        blend_rows.append(dict(Book=k, Mix=mode, **stats(r, rfr)))

print("== Correlations of monthly returns")
print(pd.DataFrame(corr_rows).set_index("Book").round(2).to_string())
print("\n== W18 in each book's 6 worst months (%)")
st = pd.DataFrame(stress_rows); st[["Book_ret", "W18_ret", "SPY_ret"]] *= 100
print(st.round(1).to_string(index=False))
print("W18 positive in", f"{(st.W18_ret > 0).mean():.0%}", "of the books' worst months; avg W18", round(st.W18_ret.mean(), 2), "% vs book", round(st.Book_ret.mean(), 2), "%")
print("\n== Blends (monthly data; MaxDD from month-ends understates intramonth drawdowns)")
bl = pd.DataFrame(blend_rows)
for c_ in ["CAGR", "Vol", "MaxDD_m", "WorstM"]: bl[c_] = (bl[c_] * 100).round(1)
print(bl.round(2).to_string(index=False))

# daily check on 4814 worst days (W18 daily return same day)
print("\n== W18 / SPY on each book's worst DAYS (%)")
for k in books:
    wd = pd.read_csv(f"optionomega/{k}_LIVE_worstdays.csv", parse_dates=["date"]).head(10)
    wr = w18.pct_change().reindex(wd.date) * 100; sr = spy.pct_change().reindex(wd.date) * 100
    print(f"{k}: book avg {wd.profitLossPercentage.mean():.2f} | W18 avg {wr.mean():.2f} (pos {(wr>0).mean():.0%}) | SPY avg {sr.mean():.2f}")
