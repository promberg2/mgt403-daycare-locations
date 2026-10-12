"""Pre-analysis task 4 figure: wage and rent coefficients alone vs. together (2022, metro-clustered 95% CIs).

Input:  output/tables/pre_t4_regressions.csv
Output: output/figures/pre_t4_coefficients.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
r = pd.read_csv(ROOT / "output/tables/pre_t4_regressions.csv")
r = r[(r.se_type == "metro") & (r.term != "const")].set_index(["spec", "term"])

SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
WAGE, RENT = "#2a78d6", "#eb6834"
ROWS = [  # label, (spec, term), color, filled
    ("Wage alone: regression (a)", ("(a) wage", "wage_k"), WAGE, False),
    ("Wage, holding rent constant: (c)", ("(c) wage + rent", "wage_k"), WAGE, True),
    ("Rent alone: regression (b)", ("(b) rent", "rent_100"), RENT, False),
    ("Rent, holding wage constant: (c)", ("(c) wage + rent", "rent_100"), RENT, True),
]
Y = [3.4, 2.4, 1.0, 0.0]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.parse_math": False})
fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for (lab, key, col, filled), y in zip(ROWS, Y):
    row = r.loc[key]
    ax.plot([row.ci_low, row.ci_high], [y, y], color=col, linewidth=2.5, solid_capstyle="round")
    ax.scatter(row.coef, y, s=95, facecolor=col if filled else SURFACE, edgecolor=col, linewidth=2, zorder=3)
    ax.text(row.ci_high + 0.25, y, f"{row.coef:.2f}  [{row.ci_low:.2f}, {row.ci_high:.2f}]", va="center",
            fontsize=9.5, color=TEXT)
for key_a, key_c, ya, yc in [(("(a) wage", "wage_k"), ("(c) wage + rent", "wage_k"), Y[0], Y[1]),
                             (("(b) rent", "rent_100"), ("(c) wage + rent", "rent_100"), Y[2], Y[3])]:
    a_, c_ = r.loc[key_a].coef, r.loc[key_c].coef
    ax.annotate("", xy=(c_, yc + 0.18), xytext=(a_, ya - 0.18),
                arrowprops=dict(arrowstyle="->", color=TEXT2, linewidth=1))
    ax.text(min(a_, c_) - 0.35, (ya + yc) / 2, f"{(c_ / a_ - 1) * 100:+.0f}%", ha="right", va="center",
            fontsize=10, color=TEXT2, fontweight="bold")
ax.set_yticks(Y)
ax.set_yticklabels([x[0] for x in ROWS], color=TEXT)
ax.set_xlim(0, 17.5)
ax.set_ylim(-0.6, 4.0)
ax.set_xlabel("Change in weekly preschool price ($)\nper $1,000 of annual wage (blue) · per $100 of monthly rent (orange)",
              color=TEXT2)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(TEXT2)
ax.tick_params(colors=TEXT2, length=0)
fig.suptitle("Both cost coefficients shrink once wage and rent are in the same regression (2022)",
             x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=TEXT)
fig.text(0.01, 0.01, "Dependent variable: median weekly center-based preschool price (2022 $). N = 998 metro counties. "
         "\nDots: coefficient (open = alone, filled = together); lines: 95% CI, SEs clustered by metro area. "
         "R²: (a) wage 0.547 · (b) rent 0.460 · (c) both 0.608.", fontsize=8, color=TEXT2)
fig.tight_layout(rect=(0, 0.07, 1, 0.94))
fig.savefig(ROOT / "output/figures/pre_t4_coefficients.png", dpi=200, facecolor=SURFACE)
print("saved")
