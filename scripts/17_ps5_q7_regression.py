"""PS5 task 7: bivariate regression (2022) of childcare-worker wages on female college share.

  wage_i = a + b * female_college_share_i + e_i
  wage: OEWS SOC 39-9011 mean annual wage, 2022 dollars (= nominal 2022)
  female_college_share: share of women 25+ with bachelor's or higher (0-1 scale), ACS 5-year 2022

Y is measured per OEWS metro area, X per county. Versions:
  A. county level, standard OLS SEs (literal reading of the task; county dataset)
  B. county level, SEs clustered by metro area (counties in a metro share one wage -> not independent)
  C. metro-area level: X aggregated to the metro = sum of college-educated women 25+ / sum of women 25+
     over the metro's counties (ACS counts), regressed on the metro's wage
Scale: X is a share (0-1), so b is the predicted wage change for a move from 0% to 100%; b/10 is the
change per 10 percentage points.

Inputs:  data/analysis/county_costs_metro_2015_2022_real.csv, data/interim/acs5_county_2015_2022.csv
Outputs: output/tables/ps5_q7_regression.csv, output/figures/ps5_q7_scatter.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data/analysis/county_costs_metro_2015_2022_real.csv", dtype={"fips": str, "oews_area": str})
c = d[(d.year == 2022)].dropna(subset=["childcare_wage", "female_college_share"]).copy()

rows = []
X = sm.add_constant(c["female_college_share"])
fit_a = sm.OLS(c["childcare_wage"], X).fit()
fit_b = sm.OLS(c["childcare_wage"], X).fit(cov_type="cluster", cov_kwds={"groups": c["oews_area"]})
G = c["oews_area"].nunique()

# metro-level aggregation with ACS counts
raw = pd.read_csv(ROOT / "data/interim/acs5_county_2015_2022.csv", dtype={"fips": str})
raw = raw[raw.year == 2022]
raw["fem_college"] = raw[["B15002_032E", "B15002_033E", "B15002_034E", "B15002_035E"]].sum(axis=1)
mc = c[["fips", "oews_area", "metro_area", "childcare_wage"]].merge(
    raw[["fips", "fem_college", "B15002_019E"]], on="fips", how="left", validate="one_to_one")
m = mc.groupby(["oews_area", "metro_area"]).agg(childcare_wage=("childcare_wage", "first"),
                                                 fem_college=("fem_college", "sum"),
                                                 fem_25plus=("B15002_019E", "sum"),
                                                 n_counties=("fips", "size")).reset_index()
m["female_college_share"] = m["fem_college"] / m["fem_25plus"]
fit_c = sm.OLS(m["childcare_wage"], sm.add_constant(m["female_college_share"])).fit()

for lab, fit, n, df_t in [("A. County, standard OLS SE", fit_a, len(c), fit_a.df_resid),
                          ("B. County, SE clustered by metro area", fit_b, len(c), G - 1),
                          ("C. Metro area (aggregated X)", fit_c, len(m), fit_c.df_resid)]:
    b, se = fit.params["female_college_share"], fit.bse["female_college_share"]
    t = b / se
    p = 2 * stats.t.sf(abs(t), df_t)
    h = stats.t.ppf(0.975, df_t) * se
    rows.append({"version": lab, "n": n, "a": fit.params["const"], "se_a": fit.bse["const"], "b": b, "se_b": se,
                 "t_b": t, "df": df_t, "p_b": p, "b_ci_low": b - h, "b_ci_high": b + h,
                 "b_per_10pp": b / 10, "r2": fit.rsquared})
res = pd.DataFrame(rows)
res.to_csv(ROOT / "output/tables/ps5_q7_regression.csv", index=False)
(ROOT / "output/tables/ps5_q7_regression_county_ols.txt").write_text(fit_a.summary().as_text(), encoding="utf-8")
(ROOT / "output/tables/ps5_q7_regression_metro_ols.txt").write_text(fit_c.summary().as_text(), encoding="utf-8")

pd.set_option("display.width", 230, "display.float_format", lambda v: f"{v:,.4f}")
print(res.to_string(index=False))
print(f"\nCounties: {len(c)}, metro areas among them: {G}; metro-level N: {len(m)}")
print("X summary county 2022:", c["female_college_share"].describe()[["mean", "std", "min", "max"]].round(4).to_dict())
print("X summary metro 2022:", m["female_college_share"].describe()[["mean", "std", "min", "max"]].round(4).to_dict())
print(f"SD(wage) county {c['childcare_wage'].std():,.2f}; corr county {c['childcare_wage'].corr(c['female_college_share']):.4f}; "
      f"corr metro {m['childcare_wage'].corr(m['female_college_share']):.4f}")

# --- figure: county and metro scatter --------------------------------------------------------------
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COL = "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.parse_math": False})
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True, facecolor=SURFACE)
for ax, (df_, fit, lab, size, se_note) in zip(axes, [
        (c, fit_a, f"Counties (N = {len(c):,}): versions A/B (B chosen)", 10,
         f"SE(b): {fit_a.bse['female_college_share']:,.0f} standard, {fit_b.bse['female_college_share']:,.0f} clustered by metro"),
        (m, fit_c, f"Metro areas (N = {len(m)}): version C", 18,
         f"SE(b): {fit_c.bse['female_college_share']:,.0f}")]):
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.scatter(df_["female_college_share"] * 100, df_["childcare_wage"], s=size, color=COL, alpha=0.4, linewidths=0)
    xs = np.linspace(df_["female_college_share"].min(), df_["female_college_share"].max(), 50)
    ax.plot(xs * 100, fit.params["const"] + fit.params["female_college_share"] * xs, color=TEXT, linewidth=2)
    b = fit.params["female_college_share"]
    ax.text(0.03, 0.97, f"Fitted: wage = {fit.params['const']:,.0f} + {b:,.0f} × share\n"
            f"= +${b / 10:,.0f} per 10 pp of female college share\n{se_note}\nR² = {fit.rsquared:.3f}",
            transform=ax.transAxes, va="top", fontsize=9.5, color=TEXT,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=SURFACE, edgecolor=GRID))
    ax.set_title(lab, loc="left", fontsize=11.5, fontweight="bold", color=TEXT)
    ax.set_xlabel("Women 25+ with bachelor's degree or higher (%)", color=TEXT2)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    for s_ in ["top", "right"]:
        ax.spines[s_].set_visible(False)
    ax.tick_params(colors=TEXT2)
axes[0].set_ylabel("Childcare-worker mean annual wage (2022)", color=TEXT2)
fig.suptitle("Childcare-worker wages vs. female college share, 2022", x=0.01, ha="left",
             fontsize=13, fontweight="bold", color=TEXT)
fig.text(0.01, 0.005, "Sources: BLS OEWS (SOC 39-9011) and ACS 5-year 2022. Left: each county carries its metro area's wage. "
         "Right: female college share aggregated to the metro area (sum of counts).", fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(ROOT / "output/figures/ps5_q7_scatter.png", dpi=200, facecolor=SURFACE)
