"""PS5 task 5: convert dollar values to constant 2022 dollars (CPI-U) and plot trends in childcare-worker
wages and rents.

Conversion: real_2022$ = nominal$ x CPI_2022 / CPI_year  (CPI-U CUUR0000SA0 annual averages).
  - OEWS wages: survey year (May reference period) -> CPI of that year.
  - ACS 5-year rent and per-capita income are published "in <vintage-year> inflation-adjusted dollars"
    (variable labels), so they use the CPI of the vintage year.
Trend statistic: mean across metro counties (unweighted) with 95% t-based CI. The metro county set is
the same in every year (1,233-1,235 counties), so trends are not driven by sample composition.

Inputs:  data/analysis/county_costs_metro_2015_2022.csv, data/interim/cpi_u_annual.csv
Outputs: data/analysis/county_costs_metro_2015_2022_real.csv  (adds *_real2022 columns)
         output/tables/ps5_q5_trends.csv, output/tables/ps5_q5_changes.csv
         output/figures/ps5_q5_wage_rent_trends.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data/analysis/county_costs_metro_2015_2022.csv", dtype={"fips": str, "oews_area": str})
cpi = pd.read_csv(ROOT / "data/interim/cpi_u_annual.csv")
d = d.merge(cpi, on="year", how="left", validate="many_to_one")
DOLLARS = ["childcare_wage", "childcare_wage_hourly", "median_gross_rent", "per_capita_income"]
for c in DOLLARS:
    d[f"{c}_real2022"] = d[c] * d["to_2022_dollars"]
d.to_csv(ROOT / "data/analysis/county_costs_metro_2015_2022_real.csv", index=False)


def mean_ci(x):
    x = x.dropna()
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return len(x), m, m - h, m + h


rows = []
for y, g in d.groupby("year"):
    r = {"year": y, "cpi_u": g["cpi_u"].iloc[0], "to_2022_dollars": g["to_2022_dollars"].iloc[0]}
    for c, short in [("childcare_wage", "wage"), ("median_gross_rent", "rent")]:
        n, m, lo, hi = mean_ci(g[f"{c}_real2022"])
        r.update({f"{short}_n": n, f"{short}_nominal": g[c].mean(), f"{short}_real": m,
                  f"{short}_real_ci_low": lo, f"{short}_real_ci_high": hi,
                  f"{short}_real_median": g[f"{c}_real2022"].median()})
    rows.append(r)
tr = pd.DataFrame(rows)
tr.to_csv(ROOT / "output/tables/ps5_q5_trends.csv", index=False)

t = tr.set_index("year")
chg = []
for a, b in [(2015, 2022), (2015, 2019), (2019, 2022), (2021, 2022)]:
    chg.append({"period": f"{a}-{b}",
                "wage_nominal_pct": (t.loc[b, "wage_nominal"] / t.loc[a, "wage_nominal"] - 1) * 100,
                "wage_real_pct": (t.loc[b, "wage_real"] / t.loc[a, "wage_real"] - 1) * 100,
                "rent_nominal_pct": (t.loc[b, "rent_nominal"] / t.loc[a, "rent_nominal"] - 1) * 100,
                "rent_real_pct": (t.loc[b, "rent_real"] / t.loc[a, "rent_real"] - 1) * 100,
                "cpi_pct": (t.loc[b, "cpi_u"] / t.loc[a, "cpi_u"] - 1) * 100})
chg = pd.DataFrame(chg)
chg.to_csv(ROOT / "output/tables/ps5_q5_changes.csv", index=False)

# --- Figure ----------------------------------------------------------------------------------------
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
WAGE, RENT = "#2a78d6", "#eb6834"      # categorical slots 1-2
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.parse_math": False})
yrs = t.index.values


def style(ax, money=True):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(TEXT2)
    ax.tick_params(colors=TEXT2, length=0)
    ax.set_xticks(yrs)
    ax.set_xticklabels([str(y) if y in (2015, 2017, 2019, 2022) else "" for y in yrs])
    if money:
        ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")


fig, axes = plt.subplots(1, 3, figsize=(14, 4.9), facecolor=SURFACE, gridspec_kw={"wspace": 0.28})
for ax, short, col, title, unit in [(axes[0], "wage", WAGE, "Childcare-worker wage", "mean annual wage"),
                                    (axes[1], "rent", RENT, "Median gross rent", "monthly rent incl. utilities")]:
    style(ax)
    ax.fill_between(yrs, t[f"{short}_real_ci_low"], t[f"{short}_real_ci_high"], color=col, alpha=0.18, linewidth=0)
    ax.plot(yrs, t[f"{short}_real"], color=col, linewidth=2.2, marker="o", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=1.3)
    ax.plot(yrs, t[f"{short}_nominal"], color=TEXT2, linewidth=1.3, linestyle="--", marker="o", markersize=3.5,
            markerfacecolor=SURFACE)
    lo = min(t[f"{short}_nominal"].min(), t[f"{short}_real_ci_low"].min())
    hi = t[f"{short}_real_ci_high"].max()
    ax.set_ylim(lo - (hi - lo) * 0.12, hi + (hi - lo) * 0.22)
    ax.text(yrs[-1] + 0.18, t[f"{short}_real"].iloc[-1], f"${t[f'{short}_real'].iloc[-1]:,.0f}\nReal (2022 $)",
            va="center", fontsize=8.5, color=col, fontweight="bold")
    ax.text(yrs[0] + 0.1, t[f"{short}_nominal"].iloc[0], "Nominal", va="top", ha="left", fontsize=8.5, color=TEXT2)
    ax.annotate(f"${t[f'{short}_real'].iloc[0]:,.0f}", (yrs[0], t[f"{short}_real"].iloc[0]),
                xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5, color=TEXT)
    ax.set_xlim(yrs[0] - 0.4, yrs[-1] + 1.9)
    ax.set_title(f"{title}\n", loc="left", fontsize=11.5, fontweight="bold", color=TEXT)
    ax.text(0, 1.02, f"{unit}, mean across metro counties", transform=ax.transAxes, fontsize=8.5, color=TEXT2)

ax = axes[2]
style(ax, money=False)
ax.axhline(100, color=TEXT2, linewidth=0.8)
for short, col, lab, dy in [("wage", WAGE, "Wage", 0.3), ("rent", RENT, "Rent", -0.3)]:
    idx = t[f"{short}_real"] / t[f"{short}_real"].iloc[0] * 100
    ax.plot(yrs, idx, color=col, linewidth=2.2, marker="o", markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.3)
    ax.text(yrs[-1] + 0.18, idx.iloc[-1] + dy, f"{lab} {idx.iloc[-1]:.1f}", va="center", fontsize=9, color=col,
            fontweight="bold")
ax.text(2015.1, 106.6, "Over 2015–2022 both rose\n≈ 5.9% in real terms", fontsize=8.5, color=TEXT2, va="center")
ax.set_xlim(yrs[0] - 0.4, yrs[-1] + 1.6)
ax.set_title("Real growth compared\n", loc="left", fontsize=11.5, fontweight="bold", color=TEXT)
ax.text(0, 1.02, "index, 2015 = 100 (2022 dollars)", transform=ax.transAxes, fontsize=8.5, color=TEXT2)

fig.suptitle("Childcare cost drivers in metro counties, 2015–2022", x=0.01, ha="left", y=1.02,
             fontsize=14, fontweight="bold", color=TEXT)
fig.text(0.01, -0.06, "Real = CPI-U deflated to 2022 dollars (BLS CUUR0000SA0, annual averages). Shaded bands: 95% CI of the "
         "mean. Wages: BLS OEWS mean annual wage, Childcare Workers (SOC 39-9011), metro area assigned to its counties.\n"
         "Rent: ACS 5-year median gross rent (vintage year = end of the 5-year window). N = 1,233–1,235 metro counties per year.",
         fontsize=8, color=TEXT2)
fig.savefig(ROOT / "output/figures/ps5_q5_wage_rent_trends.png", dpi=200, facecolor=SURFACE, bbox_inches="tight")

pd.set_option("display.width", 220, "display.float_format", lambda v: f"{v:,.2f}")
print(tr[["year", "to_2022_dollars", "wage_n", "wage_nominal", "wage_real", "rent_n", "rent_nominal", "rent_real"]].to_string(index=False))
print()
print(chg.to_string(index=False))
