"""Presentation figures (main deck), rendered at their EXACT slot size on the slide grid (no automatic cropping),
so that plot edges align with the slide grid and figure type matches slide type 1:1 (9-10.5 pt, min. 7.5 pt).

Deck-wide encoding: our top 10 = accent blue; all other counties = gray context; model "c" = orange;
"also promising" = teal; text in neutral ink. White background, 300 dpi.

Slide grid (inches, 13.333 x 7.5 slide): 12 columns, margins 0.6, gutter 0.25; content body 2.32 -> 6.62 (4.30 tall).

F1  top-10 range plot: average premium 2015-2022 -> expected premium (with 95% CI)                [6 cols x 4.30]
F1b US map of the top 10 (rank badges) + "also promising" (teal), Washington DC inset (bottom right) [6 cols x 4.30]
    (Census cartographic state/county boundaries 2022, Albers equal-area; positions = Gazetteer internal points)
F2c/F3c model "c" vs. final model: actual vs. predicted weekly price, 2022                       [4 cols x 3.50]
F3b market characteristics heatmap (percentile vs. all metro counties) + selection score          [7 cols x 4.30]
F4  backtest: 2022 premium of counties picked with 2015-2018 data vs. all other counties          [6 cols x 1.85]
F4b robustness grid: top 10 x 8 plausible design variants                                         [6 cols x 3.85]
F5  small multiples: premium path 2015-2022 of each top-10 county vs. 10th-90th percentile band   [7 cols x 3.85]
F2/F3 full-size model scatters (appendix)

Inputs: data/analysis/*.csv, output/tables/fp_*.csv, data/raw/geo/*
Output: output/figures/deck_*.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[1]
FIG, T = ROOT / "output/figures", ROOT / "output/tables"
ACCENT, ACCENT_LIGHT, ORANGE = "#2b6cd0", "#a8c8ee", "#f56300"   # softer blue / orange (validated, all pairs)
TEAL = "#00a3a3"  # "also promising" (validated all-pairs with ACCENT and ORANGE)
INK, INK2, MUTED, GRID, CONTEXT, SURF = "#1d1d1f", "#6e6e73", "#86868b", "#ececf0", "#d2d2d7", "#ffffff"
YALE = "#00356b"
SOFT, SOFT_BAR = "#d3e3f7", "#6fa2e0"  # muted fills for large blue areas (slide 4), same ramp
RAMP_HEX = ["#eef4fc", "#d3e3f7", "#a8c8ee", "#6fa2e0", "#3a7cd0", "#1d5aa6", "#0b3c7a"]  # one hue, light -> dark
RAMP = LinearSegmentedColormap.from_list("blue", RAMP_HEX)
LAND = "#f0f0f3"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9.5, "text.parse_math": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "xtick.labelsize": 9, "ytick.labelsize": 9, "axes.labelsize": 9.5})

# ---- slide grid (must match scripts/34_build_deck.py) ----
COLW, GUT = (12.133 - 11 * 0.25) / 12, 0.25
span = lambda n: n * COLW + (n - 1) * GUT
BODY_H = 4.30

top = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
exp = pd.read_csv(T / "fp_imp_expected_premium.csv", dtype={"fips": str})
prem = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str})
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str})
SHORT = {r.fips: (r.county_name.replace(" County", "").replace(" City", ""), r.state_abbr) for r in top.itertuples()}
METRO = {"51013": "Northern Virginia", "51510": "Northern Virginia", "51107": "Northern Virginia", "51059": "Northern Virginia",
         "06075": "San Francisco", "27109": "Rochester, MN", "41051": "Portland, OR", "24027": "Baltimore",
         "13139": "Gainesville, GA", "47163": "Kingsport–Bristol"}


def clean(ax, grid_axis="x"):
    for s in ["top", "right", "left", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def slot(w, h):
    """Figure of exactly w x h inches (the slot on the slide)."""
    return plt.figure(figsize=(w, h), facecolor=SURF)


def axes_in(fig, left, bottom, right, top_):
    """Axes placed by margins in inches."""
    w, h = fig.get_size_inches()
    return fig.add_axes([left / w, bottom / h, 1 - (left + right) / w, 1 - (bottom + top_) / h])


def inch_canvas(fig):
    """Axes covering the whole figure with data coordinates = inches from the top-left corner."""
    w, h = fig.get_size_inches()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.set_axis_off()
    return ax


def rbox(ax, x, y, w, h, fc, r=0.05, **kw):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", facecolor=fc,
                                edgecolor="none", **kw))


def save(fig, name, exact=True):
    if exact:
        fig.savefig(FIG / name, dpi=300, facecolor=SURF)
    else:
        fig.savefig(FIG / name, dpi=300, facecolor=SURF, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


# ---------------- F1 range plot [6 cols x 4.30] ----------------------------------------------------------------
e = exp.sort_values("rank", ascending=False).copy()  # rank 1 on top, as in every table
# average premium = arithmetic mean of the yearly % premiums, exactly as used for selection (heatmap, slide 6)
e["avg_premium_pct"] = e.fips.map(prem.groupby("fips").prem_LLS_pct.mean())
fig = slot(span(6), BODY_H)
ax = axes_in(fig, 1.45, 0.48, 0.12, 0.05)
clean(ax)
for i, r in enumerate(e.itertuples()):
    ax.plot([r.expected_premium_pct, r.avg_premium_pct], [i, i], color=ACCENT_LIGHT, linewidth=1.4, zorder=1)
    ax.plot([r.expected_low_pct, r.expected_high_pct], [i, i], color=ACCENT, linewidth=5, alpha=0.25,
            solid_capstyle="round", zorder=2)
    ax.scatter(r.avg_premium_pct, i, s=60, facecolor=SURF, edgecolor=ACCENT, linewidth=1.8, zorder=3)
    ax.scatter(r.expected_premium_pct, i, s=80, color=ACCENT, edgecolor=SURF, linewidth=1.4, zorder=4)
    ax.text(r.expected_low_pct - 1.3, i, f"+{r.expected_premium_pct:.0f}%", ha="right", va="center", fontsize=10,
            fontweight="bold", color=INK)
ax.set_yticks(range(len(e)))
ax.set_yticklabels([f"{int(rk)}  {SHORT[f][0]}, {SHORT[f][1]}" for rk, f in zip(e["rank"], e.fips)], fontsize=10, color=INK, va="bottom")
for i, f in enumerate(e.fips):
    ax.text(-0.012, i - 0.05, METRO[f], transform=ax.get_yaxis_transform(), ha="right", va="top", fontsize=8, color=MUTED)
ax.set_xlim(0, 66)
ax.xaxis.set_major_formatter(lambda v, _: f"+{v:.0f}%" if v else "0")
ax.set_xlabel("Price premium above what local wages and rents predict (within state)")
top_i = len(e) - 1
r = e.iloc[-1]
ax.annotate("Expected premium ≈ 5 years ahead\n(bar: range from slope uncertainty)", (r.expected_premium_pct, top_i),
            xytext=(r.expected_premium_pct - 4, top_i + 1.05), fontsize=8.5, color=ACCENT, ha="right", va="center",
            arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.8))
ax.annotate("Average premium\n2015–2022", (r.avg_premium_pct, top_i), xytext=(r.avg_premium_pct - 3, top_i + 1.05),
            fontsize=8.5, color=INK2, ha="center", va="center", arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_ylim(-0.6, len(e) + 0.65)
save(fig, "deck_F1_top10_premium.png")


# ---------------- F1b map [6 cols x 4.30], DC inset in the bottom-right corner ---------------------------------------
def albers(lon, lat, lon0=-96, lat0=37.5, p1=29.5, p2=45.5):
    lon, lat = np.radians(lon), np.radians(lat)
    lon0, lat0, p1, p2 = map(np.radians, (lon0, lat0, p1, p2))
    n = (np.sin(p1) + np.sin(p2)) / 2
    c = np.cos(p1) ** 2 + 2 * n * np.sin(p1)
    rho = np.sqrt(c - 2 * n * np.sin(lat)) / n
    rho0 = np.sqrt(c - 2 * n * np.sin(lat0)) / n
    th = n * (lon - lon0)
    return rho * np.sin(th), rho0 - rho * np.cos(th)


def draw_shapes(ax, reader, keep, face, edge, lw, face_of=None):
    for shp, rec in zip(reader.shapes(), reader.records()):
        if not keep(rec):
            continue
        pts = np.array(shp.points)
        fc = face_of(rec) if face_of else face
        for i0, i1 in zip(shp.parts, list(shp.parts[1:]) + [len(pts)]):
            x, y = albers(pts[i0:i1, 0], pts[i0:i1, 1])
            ax.add_patch(Polygon(np.c_[x, y], closed=True, facecolor=fc, edgecolor=edge, linewidth=lw))


def badge(ax, x, y, num, size=190, fs=8.5):
    ax.scatter([x], [y], s=size, color=ACCENT, edgecolor=SURF, linewidth=1.2, zorder=5)
    ax.text(x, y, str(num), ha="center", va="center", fontsize=fs, color=SURF, fontweight="bold", zorder=6)


def ring(ax, x, y, size=50):
    ax.scatter([x], [y], s=size, facecolor=SURF, edgecolor=TEAL, linewidth=1.8, zorder=5)


gaz = pd.read_csv(ROOT / "data/raw/geo/2022_Gaz_counties_national.txt", sep="\t", dtype={"GEOID": str})
gaz.columns = gaz.columns.str.strip()
gpos = {r.GEOID: albers(r.INTPTLONG, r.INTPTLAT) for r in gaz.itertuples()}
RANK = dict(zip(top.fips, top["rank"]))
DCAREA = {"51013", "51510", "51107", "51059", "24027"}
# "Also promising": selected under at least one plausible alternative design (fp_robustness.csv: excl. 2022,
# pre-COVID, $ premium, smaller markets, top-30 pool; fp_imp_wage_weight_robustness.csv: preschool-teacher wage)
# plus Washington DC (premium +71% in 2022, but NDCP prices for 2022 only).
OTHER = {"55079": "Milwaukee", "27123": "St. Paul", "25021": "Norfolk, MA", "51600": "Fairfax City",
         "13063": "Clayton, GA", "11001": "Washington, DC"}

MW, MH = span(6), BODY_H
fig = slot(MW, MH)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()
sf = shapefile.Reader(str(ROOT / "data/raw/geo/states/cb_2022_us_state_20m.shp"))
draw_shapes(ax, sf, lambda r: r["STUSPS"] not in ("AK", "HI", "PR"), LAND, SURF, 0.8)
# fit the contiguous US to the full slot width, anchored at the top
allx, ally = [], []
for shp, rec in zip(sf.shapes(), sf.records()):
    if rec["STUSPS"] not in ("AK", "HI", "PR"):
        px, py = albers(np.array(shp.points)[:, 0], np.array(shp.points)[:, 1])
        allx += [px.min(), px.max()]
        ally += [py.min(), py.max()]
X0, X1, ytop = min(allx), max(allx), max(ally)
upm = (X1 - X0) / (MW - 0.35)  # map units per inch
ax.set_xlim(X0 - 0.1 * upm, X0 - 0.1 * upm + MW * upm)
ax.set_ylim(ytop - MH * upm + 0.02 * upm, ytop + 0.02 * upm)
LBL = {"06075": ("San Francisco", 1, 0), "41051": ("Multnomah (Portland)", 1, 0), "27109": ("Olmsted (Rochester)", -1, 0),
       "13139": ("Hall (Gainesville)", -1, 0), "47163": ("Sullivan (Kingsport)", -1, 0)}
for f, (lab, hx, vy) in LBL.items():
    x, y = gpos[f]
    badge(ax, x, y, RANK[f])
    ax.text(x + hx * 0.15 * upm, y, lab, fontsize=9, color=INK, ha="left" if hx > 0 else "right", va="center")
TL = {"55079": (0.0, 0.0, "Milwaukee", 1), "27123": (-0.33, 0.2, "Ramsey (St. Paul)", -1),
      "25021": (0.0, 0.0, "Norfolk, MA", -1), "13063": (-0.3, -0.22, "Clayton, GA", -1)}  # offsets in inches
for f, (dx, dy, lab, hx) in TL.items():
    x, y = gpos[f]
    dx, dy = dx * upm, dy * upm
    if dx or dy:
        ax.plot([x, x + dx], [y, y + dy], color=TEAL, lw=0.7, zorder=4)
        ax.scatter([x], [y], s=6, color=TEAL, zorder=4)
    ring(ax, x + dx, y + dy)
    ax.text(x + dx + hx * 0.12 * upm, y + dy, lab, fontsize=8.5, color=INK2, ha="left" if hx > 0 else "right",
            va="center")
bx = np.array([gpos[f] for f in DCAREA | {"11001"}])
cx, cy = bx[:, 0].mean(), bx[:, 1].mean()
hb = 0.17 * upm
ax.add_patch(FancyBboxPatch((cx - hb, cy - hb), 2 * hb, 2 * hb, boxstyle=f"round,pad=0,rounding_size={0.04 * upm}",
                            facecolor=ACCENT, alpha=0.12, edgecolor=ACCENT, linewidth=1.0, zorder=5))
# inset (bottom-right corner of the slot)
IW, IH = 2.30, 1.55
ai = fig.add_axes([(MW - IW - 0.015) / MW, 0.015 / MH, IW / MW, IH / MH])
ai.set_axis_off()
ai.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", transform=ai.transAxes,
                            facecolor=SURF, edgecolor="none", zorder=0))
cty = shapefile.Reader(str(ROOT / "data/raw/geo/counties/cb_2022_us_county_5m.shp"))
TOPF, TEALF = "#cfe0f6", "#d4f0f0"
draw_shapes(ai, cty, lambda r: r["STATEFP"] in ("11", "24", "51", "54"), LAND, SURF, 0.6,
            face_of=lambda r: TOPF if r["GEOID"] in DCAREA else (TEALF if r["GEOID"] in OTHER else LAND))
_, y0 = albers(-77.3, 38.56)
_, y1 = albers(-77.3, 39.50)
xc, _ = albers(-77.10, 39.0)
U = (y1 - y0) / IH  # inset units per inch
x0, x1 = xc - IW / 2 * U, xc + IW / 2 * U
ai.set_xlim(x0, x1)
ai.set_ylim(y0, y1)
INS = {"51107": (0, 0), "51059": (0.06, -0.2), "24027": (0, 0), "51013": (0.32, 0.12), "51510": (0.32, -0.15)}
NAME = {"51107": "Loudoun", "51059": "Fairfax", "24027": "Howard", "51013": "Arlington", "51510": "Alexandria"}
for f, (dx, dy) in INS.items():
    x, y = gpos[f]
    dx, dy = dx * U, dy * U
    if dx or dy:
        ai.plot([x, x + dx], [y, y + dy], color=ACCENT, lw=0.7, zorder=4)
        ai.scatter([x], [y], s=6, color=ACCENT, zorder=4)
    badge(ai, x + dx, y + dy, RANK[f], size=150, fs=7.5)
    ai.text(x + dx + 0.1 * U, y + dy, NAME[f], fontsize=8, color=INK, ha="left", va="center", zorder=6)
for f, (dx, dy, ha) in {"11001": (0.18, 0.26, "left"), "51600": (-0.30, -0.02, "right")}.items():
    x, y = gpos[f]
    dx, dy = dx * U, dy * U
    ai.plot([x, x + dx], [y, y + dy], color=TEAL, lw=0.7, zorder=4)
    ai.scatter([x], [y], s=5, color=TEAL, zorder=4)
    ring(ai, x + dx, y + dy, size=40)
    ai.text(x + dx + (0.08 * U if ha == "left" else -0.08 * U), y + dy, "DC" if f == "11001" else OTHER[f], fontsize=8,
            color=INK2, ha=ha, va="center", zorder=6)
ai.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={0.06 * U}",
                            facecolor="none", edgecolor=ACCENT, linewidth=0.9, alpha=0.7, zorder=7))
ai.text(x0 + 0.1 * U, y1 - 0.08 * U, "WASHINGTON–BALTIMORE REGION", fontsize=7.5, color=ACCENT, fontweight="bold", ha="left",
        va="top", zorder=8)
# connector from the DC box on the map to the inset
ax.plot([cx, cx], [cy - hb, ytop - (MH - IH - 0.015) * upm], color=ACCENT, lw=0.7, alpha=0.6, zorder=4)
# legend (bottom-left)
ax.scatter([], [], s=90, color=ACCENT, label="Top 10 (number = rank)")
ax.scatter([], [], s=40, facecolor=SURF, edgecolor=TEAL, linewidth=1.8, label="Also promising: alternative designs, or DC (2022 only)")
ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.0), frameon=False, fontsize=8.5, labelcolor=INK2,
          handletextpad=0.3, borderaxespad=0.05)
save(fig, "deck_F1b_map.png")

# ---------------- model data (2022) ---------------------------------------------------------------------------------
d = a[a.year == 2022].copy()
X = sm.add_constant(pd.DataFrame({"w": d.childcare_wage_real2022 / 1000, "r": d.median_gross_rent_real2022 / 100}))
d["pred"] = sm.OLS(d.price_preschool_real2022, X).fit().fittedvalues
d["lp"], d["lw"], d["lr"] = (np.log(d.price_preschool_real2022), np.log(d.childcare_wage_real2022),
                             np.log(d.median_gross_rent_real2022))
d["pred_f"] = np.exp(smf.ols("lp ~ lw + lr + C(state_abbr)", data=d).fit().fittedvalues)
lim = (60, 520)
xs = np.array(lim)


# ---------------- F2 / F3 full-size scatters (appendix) ----------------------------------------------------------------
def full_scatter(pred, line_col, line_txt, head, xlabel, offsets, fname):
    fig, ax = plt.subplots(figsize=(7.0, 5.0), facecolor=SURF)
    clean(ax, "both")
    ax.fill_between(xs, xs, lim[1], color=ACCENT, alpha=0.05, linewidth=0)
    o = d[~d.fips.isin(top.fips)]
    ax.scatter(o[pred], o.price_preschool_real2022, s=12, color=CONTEXT, alpha=0.75, linewidths=0)
    ax.plot(xs, xs, color=line_col, linewidth=2)
    ax.text(355, 305, line_txt, color=line_col, fontsize=9.5, ha="left", va="top", fontweight="bold")
    ax.text(80, 495, head, color=ACCENT, fontsize=10.5, va="top", fontweight="bold")
    t_ = d[d.fips.isin(top.fips)]
    ax.scatter(t_[pred], t_.price_preschool_real2022, s=60, color=ACCENT, edgecolor=SURF, linewidth=1.3, zorder=4)
    for rr in t_.itertuples():
        dx, dy = offsets[rr.fips]
        ax.annotate(SHORT[rr.fips][0], (getattr(rr, pred), rr.price_preschool_real2022), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8.6, color=INK, ha="left" if dx > 0 else "right", va="center")
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel("Actual weekly preschool price (2022)", fontsize=10)
    save(fig, fname, exact=False)


full_scatter("pred", ORANGE, "Price justified\nby costs (model “c”)", "Parents pay MORE than\nwages and rents predict",
             "Predicted weekly price from wages and rent (model “c”)",
             {"51013": (8, 4), "51510": (8, -2), "06075": (8, -4), "51107": (8, -3), "27109": (8, 4), "51059": (8, -6),
              "41051": (-10, -8), "24027": (8, 6), "13139": (8, 4), "47163": (8, -6)}, "deck_F2_model_c.png")
full_scatter("pred_f", INK2, "Price justified by costs,\ncompared within the state",
             "Every top-10 county lies above\nthe line in its own state",
             "Predicted weekly price from wages, rent and state (final model)",
             {"51013": (8, 2), "51510": (8, -2), "06075": (8, 0), "51107": (-10, 9), "27109": (-10, 0), "51059": (12, 4),
              "41051": (12, -8), "24027": (10, 10), "13139": (-8, 4), "47163": (-8, 6)}, "deck_F3_final_model.png")


# ---------------- F2c / F3c compact scatters [4 cols x 3.50] -----------------------------------------------------------
def avp(pred, line_col, line_lbl, fname):
    fig = slot(span(4), 3.50)
    ax = axes_in(fig, 0.62, 0.48, 0.08, 0.05)
    clean(ax, "both")
    ax.fill_between(xs, xs, lim[1], color=ACCENT, alpha=0.05, linewidth=0)
    o = d[~d.fips.isin(top.fips)]
    ax.scatter(o[pred], o.price_preschool_real2022, s=9, color=CONTEXT, alpha=0.8, linewidths=0)
    ax.plot(xs, xs, color=line_col, linewidth=2)
    t_ = d[d.fips.isin(top.fips)]
    ax.scatter(t_[pred], t_.price_preschool_real2022, s=45, color=ACCENT, edgecolor=SURF, linewidth=1.1, zorder=4)
    for rr in t_.itertuples():
        if SHORT[rr.fips][0] in ("Hall", "Sullivan", "Arlington"):
            ax.annotate(SHORT[rr.fips][0], (getattr(rr, pred), rr.price_preschool_real2022), xytext=(6, 0),
                        textcoords="offset points", fontsize=9, color=INK, va="center")
    ax.text(510, 72, line_lbl, color=line_col, fontsize=9, ha="right", va="bottom", fontweight="bold")
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xticks([100, 200, 300, 400, 500])
    ax.set_yticks([100, 200, 300, 400, 500])
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.set_xlabel("Predicted weekly price")
    ax.set_ylabel("Actual weekly price (2022)")
    save(fig, fname)


avp("pred", ORANGE, "line = price costs justify", "deck_F2c_model_c.png")
avp("pred_f", INK2, "line = price costs justify\nwithin the same state", "deck_F3c_final.png")

# ---------------- F3b market characteristics heatmap [7 cols x 4.30], drawn in inch coordinates --------------------------
pall = prem.groupby("fips").agg(n=("year", "size"), avg=("prem_LLS_pct", "mean"), mn=("prem_LLS_pct", "min"))
pall = pall[pall.n >= 5]
d22h = a[a.year == 2022].set_index("fips")
COLS = [("Average premium\n2015–2022", lambda f: pall.loc[f, "avg"], pall["avg"], lambda v: f"+{v:.0f}%"),
        ("Weakest\nyear", lambda f: pall.loc[f, "mn"], pall["mn"], lambda v: f"+{v:.0f}%"),
        ("Children\nneeding care", lambda f: d22h.loc[f, "kids_under6_allpar_lf"], d22h["kids_under6_allpar_lf"],
         lambda v: f"{v / 1000:.1f}k"),
        ("Care-need\nshare", lambda f: d22h.loc[f, "under6_careneed_share"], d22h["under6_careneed_share"],
         lambda v: f"{v * 100:.1f}%"),
        ("Income\nper capita", lambda f: d22h.loc[f, "per_capita_income_real2022"], d22h["per_capita_income_real2022"],
         lambda v: f"${v / 1000:.0f}k")]
HW, HH = span(7), BODY_H
fig = slot(HW, HH)
ax = inch_canvas(fig)
LBLW, SCW, GRPGAP = 1.42, 1.28, 0.14
PITCH = (HW - LBLW - SCW - GRPGAP) / len(COLS)
TW = PITCH - 0.06
xcol = [LBLW + j * PITCH + (GRPGAP if j >= 2 else 0) for j in range(len(COLS))]
HEAD = 0.72
RP = (HH - HEAD) / len(top)
TH = RP - 0.05
for i, f in enumerate(top.fips):
    y = HEAD + i * RP
    for j, (_, get, dist, fmt) in enumerate(COLS):
        v = get(f)
        pct = (dist <= v).mean()
        rbox(ax, xcol[j], y, TW, TH, RAMP(pct), r=0.05)
        dark = pct > 0.55
        ax.text(xcol[j] + TW / 2, y + TH * 0.40, fmt(v), ha="center", va="center", fontsize=10, fontweight="bold",
                color=SURF if dark else INK)
        ax.text(xcol[j] + TW / 2, y + TH * 0.77, f"{pct * 100:.0f}th pct", ha="center", va="center", fontsize=7.5,
                color="#dbe7f7" if dark else INK2)
    r_ = top.set_index("fips").loc[f]
    ax.text(LBLW - 0.1, y + TH / 2, f"{r_['rank']}  {SHORT[f][0]}, {SHORT[f][1]}", ha="right", va="center",
            fontsize=10, color=INK)
    xb = HW - SCW + 0.12
    bw = SCW - 0.55
    rbox(ax, xb, y + TH / 2 - 0.07, bw, 0.14, "#f0f0f3", r=0.07)
    rbox(ax, xb, y + TH / 2 - 0.07, max(bw * r_.score, 0.14), 0.14, ACCENT, r=0.07)
    ax.text(xb + bw + 0.07, y + TH / 2, f"{r_.score:.2f}", ha="left", va="center", fontsize=9.5, fontweight="bold",
            color=INK)
for j, (lab, *_) in enumerate(COLS):
    ax.text(xcol[j] + TW / 2, HEAD - 0.06, lab, ha="center", va="bottom", fontsize=8.5, color=INK2, linespacing=1.05)
ax.text(HW - SCW + 0.12, HEAD - 0.06, "Score (0–1):\npremium + demand", ha="left", va="bottom", fontsize=8.5,
        color=INK2, linespacing=1.05)
for grp, j0, j1 in [("PRICE ADVANTAGE · 50%", 0, 1), ("DEMAND · 50%", 2, 4)]:
    xa, xb2 = xcol[j0], xcol[j1] + TW
    rbox(ax, xa, 0.0, xb2 - xa, 0.22, RAMP_HEX[0], r=0.11)
    ax.text((xa + xb2) / 2, 0.11, grp, ha="center", va="center", fontsize=8, color=ACCENT, fontweight="bold")
# colour key in the empty top-left corner
for k in range(7):
    ax.add_patch(plt.Rectangle((0.02 + k * 0.17, 0.33), 0.17, 0.09, color=RAMP(k / 6), lw=0))
ax.text(0.02, 0.47, "0", fontsize=7.5, color=INK2, va="top", ha="left")
ax.text(0.02 + 7 * 0.17, 0.47, "100th", fontsize=7.5, color=INK2, va="top", ha="right")
ax.text(0.02, 0.27, "Color = percentile among\nall metro counties", fontsize=7.5, color=INK2, va="bottom", ha="left",
        linespacing=1.0)
save(fig, "deck_F3b_characteristics.png")

# ---------------- F4 backtest [6 cols x 2.05]: all counties, and without the extrapolated CA/VA 2022 prices -----------------
bt = pd.read_csv(T / "fp_checks_D_backtest_full_rule.csv")
fig = slot(span(6), 2.05)
ax = axes_in(fig, 1.95, 0.42, 0.62, 0.02)
clean(ax)
ys = [3.6, 2.8, 1.2, 0.4]
vals = [bt.iloc[i].mean_premium_2022 for i in range(4)]
labs = [f"Picked in 2018 ({int(bt.iloc[0].n_in_2022)})", f"All other ({int(bt.iloc[1].n_in_2022):,})",
        f"Picked in 2018 ({int(bt.iloc[2].n_in_2022)})", f"All other ({int(bt.iloc[3].n_in_2022):,})"]
ax.barh(ys, vals, color=[SOFT_BAR, CONTEXT, SOFT_BAR, CONTEXT], height=0.62)
for y, v in zip(ys, vals):
    ax.text(v + 0.8, y, f"+{v:.1f}%", va="center", fontsize=11, fontweight="bold", color=INK)
ax.set_yticks(ys)
ax.set_yticklabels(labs, fontsize=9, color=INK)
for y, t in [(4.25, "All counties"), (1.85, "Without CA and VA, whose 2022 NDCP prices are extrapolated")]:
    ax.text(0.4, y, t, ha="left", va="center", fontsize=8.5, color=ACCENT, fontweight="bold")
ax.set_xlim(0, 50)
ax.set_ylim(-0.05, 4.5)
ax.xaxis.set_major_formatter(lambda v, _: f"+{v:.0f}%" if v else "0")
ax.set_xlabel("Average price premium in 2022 (within state)", fontsize=8.5)
save(fig, "deck_F4_backtest.png")

# ---------------- F4b robustness grid [6 cols x 3.85], inch coordinates ------------------------------------------------
rob = pd.read_csv(T / "fp_robustness.csv")
VAR = {"Average premium 2015-2020 (excludes NDCP 2022 extrapolation)": "Without\n2022 data",
       "Average premium 2015-2019 (pre-COVID)": "Pre-COVID\n2015–19",
       "Level instead of log premium (LS, $/week, state effects)": "Premium in\n$ not %",
       "Market threshold: 25th percentile": "Smaller\nmarkets",
       "Candidate pool: top 30 instead of top 20": "Top-30\npool"}  # the 5 variants that can change the list
full = {f"{r.county_name}, {r.state_abbr}": r.fips for r in top.itertuples()}
grid = []
for v in VAR:
    row = rob[rob.variant == v].iloc[0]
    dropped = set(str(row.dropped).split("; ")) if isinstance(row.dropped, str) else set()
    grid.append([0 if k in dropped else 1 for k in full])
G = np.array(grid).T
GW, GH = span(6), 3.3
fig = slot(GW, GH)
ax = inch_canvas(fig)
LW_, TOTW, GHEAD = 1.32, 0.5, 0.44
CP = (GW - LW_ - TOTW) / G.shape[1]
RPg = (GH - GHEAD) / G.shape[0]
for i in range(G.shape[0]):
    y = GHEAD + i * RPg
    ax.text(LW_ - 0.1, y + RPg / 2, f"{SHORT[list(full.values())[i]][0]}, {SHORT[list(full.values())[i]][1]}",
            ha="right", va="center", fontsize=9.5, color=INK)
    for j in range(G.shape[1]):
        ok = G[i, j] == 1
        rbox(ax, LW_ + j * CP + 0.03, y + 0.03, CP - 0.06, RPg - 0.06, SOFT if ok else "#f2f2f5", r=0.05)
        ax.text(LW_ + j * CP + CP / 2, y + RPg / 2, "✓" if ok else "–", ha="center", va="center", fontsize=10,
                fontfamily="Segoe UI Symbol", color=ACCENT if ok else MUTED, fontweight="bold")
    ax.text(GW - TOTW / 2, y + RPg / 2, f"{G[i].sum()}/{G.shape[1]}", ha="center", va="center", fontsize=9.5, color=INK,
            fontweight="bold")
for j, lab in enumerate(VAR.values()):
    ax.text(LW_ + j * CP + CP / 2, GHEAD - 0.05, lab, ha="center", va="bottom", fontsize=8, color=INK2, linespacing=1.0)
ax.text(GW - TOTW / 2, GHEAD - 0.05, "Kept", ha="center", va="bottom", fontsize=8, color=INK2)
save(fig, "deck_F4b_robustness_grid.png")

# ---------------- F5 stability: small multiples [7 cols x 3.85] ----------------------------------------------------------
band = prem.groupby("year").prem_LLS_pct.quantile([0.1, 0.5, 0.9]).unstack()
SW, SH = span(7), 3.85
fig = slot(SW, SH)
L_, R_, TOPM, BOTM, TITLE, WS = 0.52, 0.05, 0.40, 0.28, 0.40, 0.13
pw = (SW - L_ - R_ - 4 * WS) / 5
ph = (SH - TOPM - BOTM - TITLE) / 2
for k, r in enumerate(top.sort_values("rank").itertuples()):
    row, col = divmod(k, 5)
    left = L_ + col * (pw + WS)
    bottom = BOTM + (1 - row) * (ph + TITLE)
    ax = fig.add_axes([left / SW, bottom / SH, pw / SW, ph / SH])
    clean(ax, "y")
    ax.fill_between(band.index, band[0.1], band[0.9], color=CONTEXT, alpha=0.5, linewidth=0)
    ax.axhline(0, color=INK2, linewidth=0.6)
    gg = prem[prem.fips == r.fips].sort_values("year")
    yy, vv = gg.year.values, gg.prem_LLS_pct.values
    for kk in range(len(yy) - 1):  # dashed where a year is missing (2021 for CA/VA)
        gap = yy[kk + 1] - yy[kk] > 1
        ax.plot(yy[kk:kk + 2], vv[kk:kk + 2], color=ACCENT, linewidth=2, solid_capstyle="round",
                linestyle=(0, (1.5, 1.5)) if gap else "-")
    ax.scatter(yy, vv, s=8, color=ACCENT, zorder=3)
    ax.text(0, 1.0 + 0.20 / ph, f"{r.rank}  {SHORT[r.fips][0]}, {SHORT[r.fips][1]}", transform=ax.transAxes,
            fontsize=9, color=INK, va="bottom", ha="left")
    ax.text(0, 1.0 + 0.03 / ph, f"avg. +{vv.mean():.0f}%", transform=ax.transAxes, fontsize=8.5, color=INK2,
            va="bottom", ha="left")
    ax.set_ylim(-25, 110)
    ax.set_yticks([0, 50, 100])
    ax.set_xlim(2014.7, 2022.3)
    ax.set_xticks([2015, 2022])
    if col == 0:
        ax.yaxis.set_major_formatter(lambda v, _: f"+{v:.0f}%" if v else "0")
        ax.tick_params(axis="y", labelsize=8.5)
    else:
        ax.set_yticklabels([])
    if row == 1:
        ax.set_xticklabels(["2015", "2022"], fontsize=8.5)
        for tl, ha in zip(ax.get_xticklabels(), ["left", "right"]):
            tl.set_ha(ha)
    else:
        ax.set_xticklabels([])
    if k == 5:
        ax.text(2015.0, -13, "typical county", fontsize=7.5, color=INK2, va="center")
save(fig, "deck_F5_stability.png")
print("figures written:", sorted(p.name for p in FIG.glob("deck_*.png")))
