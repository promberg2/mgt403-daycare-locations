"""Pre-analysis task 3: scatter plots of the preschool price against (a) childcare-worker wages and (b) rents,
2022 analysis dataset, each with the fitted line from a bivariate OLS regression.

Price: NDCP median weekly center-based preschool price (2022 $). Wage: OEWS mean annual wage, SOC 39-9011.
Rent: ACS median gross rent per month. Axes in natural units; the slope is also shown per $1,000 of annual
wage and per $100 of monthly rent for readability.

Input:  data/analysis/analysis_dataset_2015_2022.csv
Output: output/figures/pre_t3_scatter_price_wage_rent.png, output/tables/pre_t3_fits.csv
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d = a[a.year == 2022].copy()
Y = "price_preschool_real2022"

PANELS = [("childcare_wage_real2022", "(a) Childcare-worker wage", "Childcare-worker mean annual wage (2022 $)",
           1000, "per $1,000 of annual wage", "#2a78d6"),
          ("median_gross_rent_real2022", "(b) Median gross rent", "Median gross rent per month (2022 $)",
           100, "per $100 of monthly rent", "#eb6834")]

SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.parse_math": False})
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharey=True, facecolor=SURFACE)
rows = []
for ax, (x, title, xlab, scale, unit, col) in zip(axes, PANELS):
    fit = sm.OLS(d[Y], sm.add_constant(d[x])).fit()
    a0, b = fit.params["const"], fit.params[x]
    rows.append({"x": x, "n": int(fit.nobs), "intercept": a0, "slope": b, "slope_scaled": b * scale,
                 "scale": scale, "r2": fit.rsquared, "corr": d[Y].corr(d[x])})
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.scatter(d[x], d[Y], s=11, color=col, alpha=0.4, linewidths=0)
    xs = np.linspace(d[x].min(), d[x].max(), 50)
    ax.plot(xs, a0 + b * xs, color=TEXT, linewidth=2)
    ax.text(0.03, 0.97, f"Fitted line: price = {a0:,.2f} + {b:.4f} × x\n= +${b * scale:,.2f}/week {unit}\n"
            f"R² = {fit.rsquared:.3f}   N = {int(fit.nobs):,} counties", transform=ax.transAxes, va="top",
            fontsize=9.5, color=TEXT, bbox=dict(boxstyle="round,pad=0.4", facecolor=SURFACE, edgecolor=GRID))
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=TEXT)
    ax.set_xlabel(xlab, color=TEXT2)
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=TEXT2)
axes[0].set_ylabel("Preschool price, center-based median ($/week, 2022 $)", color=TEXT2)
fig.suptitle("Childcare prices vs. costs across metro counties, 2022", x=0.01, ha="left", fontsize=13.5,
             fontweight="bold", color=TEXT)
fig.text(0.01, 0.005, "Each dot is one metro county (analysis dataset, N = 998). Line: OLS fit. Sources: DOL NDCP, BLS OEWS "
         "(SOC 39-9011), ACS 5-year 2022.", fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(ROOT / "output/figures/pre_t3_scatter_price_wage_rent.png", dpi=200, facecolor=SURFACE)

res = pd.DataFrame(rows)
res.to_csv(ROOT / "output/tables/pre_t3_fits.csv", index=False)
pd.set_option("display.width", 200)
print(res.round(5).to_string(index=False))
print("corr(wage, rent) 2022:", round(d["childcare_wage_real2022"].corr(d["median_gross_rent_real2022"]), 3))
