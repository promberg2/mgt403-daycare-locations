"""PS4 Q2: distribution of 2022 median weekly center-based prices by child age group (metro sample).

For each age group (infant 0-23 mo, toddler 24-35 mo, preschool 36-54 mo) we report
N, mean, SD (sample, ddof=1), and a 95% t-based confidence interval for the mean:
    mean +/- t_{0.975, N-1} * SD / sqrt(N)
The unit of observation is the county (unweighted); each age group uses all counties with a
non-missing price for that group.

Supplements:
  - paired within-county differences between age groups (same counties), with 95% CIs;
  - robustness: 95% CI with standard errors clustered by state, because NDCP prices are often set
    by state rate zones (many counties in a state share one price), so counties are not independent.

Inputs:  data/analysis/ndcp_metro_2015_2022.csv
Outputs: output/tables/ps4_q2_summary_2022.csv
         output/tables/ps4_q2_paired_differences_2022.csv
         output/figures/ps4_q2_histograms_2022.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "output/figures").mkdir(parents=True, exist_ok=True)
YEAR = 2022
AGES = [("MCINFANT", "Infant (0–23 months)"),
        ("MCTODDLER", "Toddler (24–35 months)"),
        ("MCPRESCHOOL", "Preschool (36–54 months)")]

df = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d = df[df["year"] == YEAR]


def mean_ci(x: pd.Series, level: float = 0.95) -> dict:
    x = x.dropna()
    n, mean, sd = len(x), x.mean(), x.std(ddof=1)
    se = sd / np.sqrt(n)
    t = stats.t.ppf(1 - (1 - level) / 2, df=n - 1)
    return {"n": n, "mean": mean, "sd": sd, "se": se, "t_crit": t,
            "ci_low": mean - t * se, "ci_high": mean + t * se}


def cluster_ci(frame: pd.DataFrame, col: str, level: float = 0.95) -> dict:
    """Mean with state-clustered SE (robustness: NDCP prices are set by state rate zones, so
    counties in the same state are not independent). OLS of price on a constant, CR1 SEs,
    t critical value with G-1 degrees of freedom (G = number of states)."""
    x = frame[[col, "state_abbr"]].dropna()
    fit = sm.OLS(x[col], np.ones(len(x))).fit(cov_type="cluster",
                                              cov_kwds={"groups": x["state_abbr"]})
    g = x["state_abbr"].nunique()
    se = fit.bse.iloc[0]
    t = stats.t.ppf(1 - (1 - level) / 2, df=g - 1)
    m = fit.params.iloc[0]
    return {"n_states": g, "se_cluster": se, "ci_low_cluster": m - t * se, "ci_high_cluster": m + t * se}


# --- Summary table ----------------------------------------------------------------------
rows = []
for col, label in AGES:
    r = {"age_group": label, **mean_ci(d[col])}
    r.update(median=d[col].median(), min=d[col].min(), max=d[col].max(),
             distinct_prices=d[col].nunique(), **cluster_ci(d, col))
    rows.append(r)
summary = pd.DataFrame(rows)
summary.round(2).to_csv(ROOT / "output/tables/ps4_q2_summary_2022.csv", index=False)

# --- Paired within-county differences ---------------------------------------------------
pairs = [("MCINFANT", "MCTODDLER"), ("MCTODDLER", "MCPRESCHOOL"), ("MCINFANT", "MCPRESCHOOL")]
prow = []
for a, b in pairs:
    both = d[[a, b, "state_abbr"]].dropna()
    both["diff"] = both[a] - both[b]
    diff = both["diff"]
    r = mean_ci(diff)
    r.update(comparison=f"{a} - {b}", pct_of_second=diff.mean() / both[b].mean() * 100,
             share_counties_first_higher=(diff > 0).mean(), share_equal=(diff == 0).mean(),
             **cluster_ci(both, "diff"))
    prow.append(r)
paired = pd.DataFrame(prow)[["comparison", "n", "mean", "sd", "se", "ci_low", "ci_high",
                             "se_cluster", "ci_low_cluster", "ci_high_cluster",
                             "pct_of_second", "share_counties_first_higher", "share_equal"]]
paired.round(3).to_csv(ROOT / "output/tables/ps4_q2_paired_differences_2022.csv", index=False)

# --- Histograms (small multiples, shared bins and x-axis) --------------------------------
SERIES = "#2a78d6"      # categorical slot 1 (single series per panel)
SURFACE = "#fcfcfb"
TEXT, TEXT2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

allvals = pd.concat([d[c] for c, _ in AGES]).dropna()
bins = np.arange(np.floor(allvals.min() / 20) * 20, allvals.max() + 20, 20)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "text.parse_math": False})  # "$" is a currency sign, not math
fig, axes = plt.subplots(3, 1, figsize=(8, 8.5), sharex=True, sharey=True, facecolor=SURFACE)
for ax, (col, label), s in zip(axes, AGES, rows):
    ax.set_facecolor(SURFACE)
    ax.hist(d[col].dropna(), bins=bins, color=SERIES, edgecolor=SURFACE, linewidth=1.5)
    ax.axvline(s["mean"], color=TEXT, linewidth=1.5)
    ax.axvspan(s["ci_low"], s["ci_high"], color=TEXT, alpha=0.12, linewidth=0)
    ax.set_title(label, loc="left", fontsize=11, color=TEXT, fontweight="bold")
    ax.text(0.99, 0.92,
            f"Mean ${s['mean']:.2f}   SD ${s['sd']:.2f}   N = {s['n']:,}\n"
            f"95% CI [${s['ci_low']:.2f}, ${s['ci_high']:.2f}]",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5, color=TEXT2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT2)
    ax.tick_params(colors=TEXT2, length=0)
    ax.set_ylabel("Counties", color=TEXT2)
axes[-1].set_xlabel("Median weekly full-time price, center-based care (nominal $, 2022)", color=TEXT2)
axes[-1].xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
fig.suptitle("2022 childcare prices across metro counties, by age group",
             x=0.02, ha="left", fontsize=13, fontweight="bold", color=TEXT)
fig.text(0.02, 0.005, "Source: DOL NDCP 2022; metro counties (OEWS area code 00…). Bins = $20.\n"
         "Black line = mean; grey band = 95% CI of the mean (narrow because N ≈ 1,000).",
         fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.035, 1, 0.97))
fig.savefig(ROOT / "output/figures/ps4_q2_histograms_2022.png", dpi=200, facecolor=SURFACE)

pd.set_option("display.width", 200)
print(summary.round(2).to_string(index=False))
print()
print(paired.round(3).to_string(index=False))
print("\nSkewness:", {c: round(stats.skew(d[c].dropna()), 2) for c, _ in AGES})
