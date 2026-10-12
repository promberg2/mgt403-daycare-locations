"""PS4 Q3: convert NDCP prices to constant 2022 dollars (CPI-U) and plot trends by age group.

Conversion: real_2022$ = nominal$ x CPI_2022 / CPI_year, with CPI-U = BLS CUUR0000SA0 annual
averages (data/interim/cpi_u_annual.csv, built by 01_get_cpi.py). All 12 NDCP price columns are
converted so later problem sets can reuse them.

Trend statistic: for each year and age group, the mean across metro counties of the NDCP median
weekly center-based price (as in Q2), with a 95% t-based CI. Robustness:
  - median across counties;
  - balanced panel: only counties with a non-missing price in all 8 years (removes composition
    changes, e.g. the drop to 918 priced counties in 2021).

Inputs:  data/analysis/ndcp_metro_2015_2022.csv, data/interim/cpi_u_annual.csv
Outputs: data/analysis/ndcp_metro_2015_2022_real.csv   (adds *_real2022 columns + cpi_u, to_2022_dollars)
         output/tables/ps4_q3_trends_real.csv          (year x age group: N, means, CI, medians, balanced)
         output/tables/ps4_q3_changes.csv              (% changes over key periods, nominal vs real)
         output/figures/ps4_q3_real_price_trends.png
         output/figures/ps4_q3_nominal_vs_real.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
AGES = [("MCINFANT", "Infant"), ("MCTODDLER", "Toddler"), ("MCPRESCHOOL", "Preschool")]
PRICE_COLS = [f"{p}{a}" for p in ["MC", "_75C", "MFCC", "_75FCC"] for a in ["INFANT", "TODDLER", "PRESCHOOL"]]
TEXT_COLS = {"fips": str, "oews_area": str, "MCINFANT_imp": str, "MCTODDLER_imp": str, "MCPRESCHOOL_imp": str}

df = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype=TEXT_COLS)
cpi = pd.read_csv(ROOT / "data/interim/cpi_u_annual.csv")
assert set(df["year"]) <= set(cpi["year"]), "CPI missing for some years"

# --- Convert to constant 2022 dollars -------------------------------------------------------
df = df.merge(cpi, on="year", how="left", validate="many_to_one")
for c in PRICE_COLS:
    df[f"{c}_real2022"] = df[c] * df["to_2022_dollars"]
df.to_csv(ROOT / "data/analysis/ndcp_metro_2015_2022_real.csv", index=False)


def mean_ci(x):
    x = x.dropna()
    n, m, sd = len(x), x.mean(), x.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
    return n, m, sd, m - h, m + h


# --- Yearly statistics ----------------------------------------------------------------------
rows = []
for col, lab in AGES:
    real = f"{col}_real2022"
    counts = df.dropna(subset=[col]).groupby("fips")["year"].nunique()
    balanced = set(counts[counts == df["year"].nunique()].index)
    for yr, g in df.groupby("year"):
        n, m, sd, lo, hi = mean_ci(g[real])
        gb = g[g["fips"].isin(balanced)]
        rows.append({"age_group": lab, "year": yr, "n": n,
                     "mean_nominal": g[col].mean(), "mean_real": m, "sd_real": sd,
                     "ci_low_real": lo, "ci_high_real": hi,
                     "median_nominal": g[col].median(), "median_real": g[real].median(),
                     "n_balanced": gb[real].notna().sum(), "mean_real_balanced": gb[real].mean(),
                     "cpi_u": g["cpi_u"].iloc[0], "to_2022_dollars": g["to_2022_dollars"].iloc[0]})
trend = pd.DataFrame(rows)
trend.round(3).to_csv(ROOT / "output/tables/ps4_q3_trends_real.csv", index=False)

# --- Percent changes over key periods -------------------------------------------------------
periods = [(2015, 2022), (2015, 2019), (2019, 2022), (2021, 2022)]
chg = []
for lab in trend["age_group"].unique():
    t = trend[trend["age_group"] == lab].set_index("year")
    for a, b in periods:
        r = {"age_group": lab, "period": f"{a}-{b}"}
        for s in ["mean_nominal", "mean_real", "median_real", "mean_real_balanced"]:
            r[f"pct_{s}"] = (t.loc[b, s] / t.loc[a, s] - 1) * 100
        r["change_real_dollars"] = t.loc[b, "mean_real"] - t.loc[a, "mean_real"]
        chg.append(r)
cpi_i = cpi.set_index("year")["cpi_u"]
for a, b in periods:
    chg.append({"age_group": "CPI-U (all items)", "period": f"{a}-{b}",
                "pct_mean_nominal": (cpi_i[b] / cpi_i[a] - 1) * 100})
changes = pd.DataFrame(chg)
changes.round(2).to_csv(ROOT / "output/tables/ps4_q3_changes.csv", index=False)

# --- Figures ----------------------------------------------------------------------------------
# Categorical slots 1-3 (validated with dataviz validate_palette.js; aqua < 3:1 contrast -> direct
# labels + distinct markers as secondary encoding).
COLORS = {"Infant": "#2a78d6", "Toddler": "#eb6834", "Preschool": "#1baf7a"}
MARKERS = {"Infant": "o", "Toddler": "s", "Preschool": "^"}
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.parse_math": False})
years = sorted(trend["year"].unique())


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT2)
    ax.tick_params(colors=TEXT2, length=0)
    ax.set_xticks(years)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")


# Figure 1: real mean price by age group, with 95% CI bands and direct labels
fig, ax = plt.subplots(figsize=(8.5, 5.2), facecolor=SURFACE)
style(ax)
for lab in COLORS:
    t = trend[trend["age_group"] == lab]
    ax.fill_between(t["year"], t["ci_low_real"], t["ci_high_real"], color=COLORS[lab], alpha=0.15, linewidth=0)
    ax.plot(t["year"], t["mean_real"], color=COLORS[lab], linewidth=2, marker=MARKERS[lab],
            markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5, label=lab)
    first, last = t.iloc[0], t.iloc[-1]
    ax.text(last["year"] + 0.12, last["mean_real"], f"{lab}  ${last['mean_real']:.0f}",
            va="center", color=TEXT, fontsize=10)
    ax.text(first["year"] - 0.12, first["mean_real"], f"${first['mean_real']:.0f}",
            va="center", ha="right", color=TEXT2, fontsize=9)
ax.set_xlim(years[0] - 0.6, years[-1] + 1.3)
inf21 = trend[(trend["year"] == 2021) & (trend["age_group"] == "Infant")]["mean_real"].item()
ax.annotate("2021: no NDCP prices for CA, NC, VA, PA\n(214 above-average-price counties)\n→ dip is a sample-composition effect",
            xy=(2020.93, inf21), xytext=(2016.5, 211), fontsize=8, color=TEXT2, va="top",
            arrowprops=dict(arrowstyle="-", color=TEXT2, linewidth=0.8))
ax.set_ylabel("Mean weekly price (2022 dollars)", color=TEXT2)
ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=9, labelcolor=TEXT2)
ax.set_title("Real childcare prices, metro counties, 2015–2022", loc="left",
             fontsize=13, fontweight="bold", color=TEXT, pad=26)
ax.text(0, 1.03, "Mean across counties of NDCP median weekly center-based price, CPI-U deflated to 2022 dollars",
        transform=ax.transAxes, fontsize=9, color=TEXT2)
fig.text(0.01, 0.01, "Shaded bands: 95% CI of the mean. Source: DOL NDCP; BLS CPI-U (CUUR0000SA0, annual avg.). "
         "N per year: 918–1,063 counties.", fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(ROOT / "output/figures/ps4_q3_real_price_trends.png", dpi=200, facecolor=SURFACE)

# Figure 2: nominal vs real, one panel per age group (shared y-axis)
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=True, facecolor=SURFACE)
for ax, lab in zip(axes, COLORS):
    style(ax)
    t = trend[trend["age_group"] == lab]
    ax.plot(t["year"], t["mean_real"], color=COLORS[lab], linewidth=2, marker=MARKERS[lab],
            markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.2)
    ax.plot(t["year"], t["mean_nominal"], color=TEXT2, linewidth=1.5, linestyle="--",
            marker="o", markersize=4, markerfacecolor=SURFACE)
    ax.text(2022.15, t["mean_real"].iloc[-1], "Real\n(2022 $)", va="bottom", color=TEXT, fontsize=8.5)
    t18 = t.set_index("year").loc[2018, "mean_nominal"]
    ax.text(2018.2, t18 - 3, "Nominal", va="top", color=TEXT2, fontsize=8.5)
    ax.set_title(lab, loc="left", fontsize=11, fontweight="bold", color=TEXT)
    ax.set_xticks([2015, 2018, 2022])
    ax.set_xlim(2014.6, 2023.4)
axes[0].set_ylabel("Mean weekly price", color=TEXT2)
fig.suptitle("Nominal vs. real (2022 $) childcare prices, metro counties", x=0.01, ha="left",
             fontsize=13, fontweight="bold", color=TEXT)
fig.text(0.01, 0.01, "Lines converge in 2022 by construction (2022 is the base year). The gap in earlier years is inflation.",
         fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(ROOT / "output/figures/ps4_q3_nominal_vs_real.png", dpi=200, facecolor=SURFACE)

# Figure 3 (robustness): full sample vs balanced panel, real dollars
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=False, facecolor=SURFACE)
for ax, lab in zip(axes, COLORS):
    style(ax)
    t = trend[trend["age_group"] == lab]
    ax.plot(t["year"], t["mean_real"], color=COLORS[lab], linewidth=2, marker=MARKERS[lab],
            markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.2)
    ax.plot(t["year"], t["mean_real_balanced"], color=TEXT2, linewidth=1.5, linestyle="--",
            marker="o", markersize=4, markerfacecolor=SURFACE)
    ax.text(2022.15, t["mean_real"].iloc[-1], f"All priced\n(N {t['n'].min()}–{t['n'].max()})",
            va="center", color=TEXT, fontsize=8)
    ax.text(2022.15, t["mean_real_balanced"].iloc[-1], f"Balanced\n(N {t['n_balanced'].iloc[0]})",
            va="center", color=TEXT2, fontsize=8)
    ax.set_title(lab, loc="left", fontsize=11, fontweight="bold", color=TEXT)
    ax.set_xticks([2015, 2018, 2022])
    ax.set_xlim(2014.6, 2024.2)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10], integer=True))
axes[0].set_ylabel("Mean weekly price (2022 dollars)", color=TEXT2)
fig.suptitle("Robustness: all priced counties vs. balanced panel (priced in all 8 years)", x=0.01,
             ha="left", fontsize=13, fontweight="bold", color=TEXT)
fig.text(0.01, 0.01, "Balanced panel = counties with a price in every year 2015–2022 (34 states; excludes e.g. CA, NC, VA, PA). "
         "Separate y-axes per panel.", fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(ROOT / "output/figures/ps4_q3_balanced_panel.png", dpi=200, facecolor=SURFACE)

# Composition check: counties priced in 2020 but not 2021
p = df.pivot_table(index=["fips", "state_abbr"], columns="year", values="MCPRESCHOOL_real2022").reset_index()
gone = p[p[2020].notna() & p[2021].isna()]
print(f"Priced in 2020 but not 2021: {len(gone)} counties {gone['state_abbr'].value_counts().to_dict()}; "
      f"their 2020 real preschool mean ${gone[2020].mean():.2f} vs all ${p[2020].mean():.2f}")
bal = p.dropna(subset=years)
print(f"Balanced panel (preschool): {len(bal)} counties in {bal['state_abbr'].nunique()} states")

pd.set_option("display.width", 220)
print(trend[["age_group", "year", "n", "mean_nominal", "mean_real", "ci_low_real", "ci_high_real",
             "median_real", "n_balanced", "mean_real_balanced"]].round(2).to_string(index=False))
print()
print(changes.round(2).to_string(index=False))
