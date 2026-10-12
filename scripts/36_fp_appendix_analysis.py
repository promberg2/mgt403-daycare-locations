"""Appendix: supporting tables and figures (recomputed from the analysis data; nothing here changes the selection).

Tables (output/tables/app_*.csv)
  app_models_2022.csv        model "c" (L) and the three alternatives (LL, LS, LLS), 2022, metro-clustered SEs
  app_yearly_models.csv      the final model (LLS) estimated separately for every year 2015-2022
  app_candidates.csv         the 20-county candidate pool with every filter outcome and the score
  app_excluded_no2022.csv    counties that would enter the pool if a 2022 price were not required
  app_backtest_2018.csv      the ten counties the complete rule picks with data up to 2018, and their 2022 premium
  app_ndcp_quality_top10.csv direct NDCP survey years vs. interpolated/extrapolated years for the top 10
Figures (output/figures/app_*.png, rendered at their exact size on a Letter page, 7.0 in content width)
  app_A_timeline.png         which years enter which analysis
  app_B_models.png           model "c" vs. final model, actual vs. predicted, 2022 (top 10 = rank badges)
  app_B_yearly.png           wage and rent elasticities by year, 95% CI
  app_B_residuals.png        residual diagnostics of the final model, 2022
  app_D_persistence.png      survey-only persistence scatter + year-to-year correlation matrix
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
T, FIG = ROOT / "output/tables", ROOT / "output/figures"
ACCENT, ACCENT_LIGHT, ORANGE, TEAL = "#2b6cd0", "#a8c8ee", "#f56300", "#00a3a3"
INK, INK2, MUTED, GRID, CONTEXT, SURF = "#1d1d1f", "#6e6e73", "#86868b", "#ececf0", "#d2d2d7", "#ffffff"
RAMP = LinearSegmentedColormap.from_list("blue", ["#eef4fc", "#d3e3f7", "#a8c8ee", "#6fa2e0", "#3a7cd0", "#1d5aa6", "#0b3c7a"])
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8.5, "text.parse_math": False, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8,
                     "ytick.labelsize": 8, "axes.labelsize": 8.5})
W = 7.0  # content width of a Letter page with 0.75 in margins

a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str, "price_imp_code": str})
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
top = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
a["lp"], a["lw"], a["lr"] = np.log(a.price_preschool_real2022), np.log(a.childcare_wage_real2022), np.log(a.median_gross_rent_real2022)
a["wage_k"], a["rent_100"] = a.childcare_wage_real2022 / 1000, a.median_gross_rent_real2022 / 100
d22 = a[a.year == 2022].copy()
RANK = dict(zip(top.fips, top["rank"]))


def clean(ax, grid="y"):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis=grid, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(FIG / name, dpi=300, facecolor=SURF)
    plt.close(fig)


def fit(formula, df):
    return smf.ols(formula, data=df).fit(cov_type="cluster", cov_kwds={"groups": df.oews_area})


# ---------------- models 2022 ---------------------------------------------------------------------------------------
SPECS = {"L": ("price_preschool_real2022 ~ wage_k + rent_100", "wage_k", "rent_100", "Model “c”: level"),
         "LS": ("price_preschool_real2022 ~ wage_k + rent_100 + C(state_abbr)", "wage_k", "rent_100", "Level + state effects"),
         "LL": ("lp ~ lw + lr", "lw", "lr", "Log-log"),
         "LLS": ("lp ~ lw + lr + C(state_abbr)", "lw", "lr", "Log-log + state effects (final)")}
rows, fits = [], {}
for k, (f, w_, r_, lab) in SPECS.items():
    m = fit(f, d22)
    fits[k] = m
    rows.append({"model": k, "label": lab, "n": int(m.nobs), "wage": m.params[w_], "wage_se": m.bse[w_], "rent": m.params[r_],
                 "rent_se": m.bse[r_], "r2": m.rsquared, "adj_r2": m.rsquared_adj, "resid_sd": np.sqrt(m.mse_resid),
                 "n_state_dummies": d22.state_abbr.nunique() - 1 if "state" in f else 0})
pd.DataFrame(rows).to_csv(T / "app_models_2022.csv", index=False)

# ---------------- final model by year ------------------------------------------------------------------------------------
yr = []
for y, g in a.groupby("year"):
    m = fit("lp ~ lw + lr + C(state_abbr)", g)
    mc = fit("price_preschool_real2022 ~ wage_k + rent_100", g)
    yr.append({"year": y, "n": int(m.nobs), "states": g.state_abbr.nunique(), "metros": g.oews_area.nunique(),
               "wage_el": m.params["lw"], "wage_se": m.bse["lw"], "rent_el": m.params["lr"], "rent_se": m.bse["lr"],
               "r2": m.rsquared, "resid_sd": np.sqrt(m.mse_resid), "r2_model_c": mc.rsquared})
yr = pd.DataFrame(yr)
yr.to_csv(T / "app_yearly_models.csv", index=False)

# ---------------- candidate pool (exactly the rule in 27_fp_select_top10.py) ------------------------------------------------
h = p.groupby("fips")
d = p[p.year == 2022].copy()
d["n_years"], d["mean_prem"], d["mean_nat"] = d.fips.map(h.size()), d.fips.map(h.prem_LLS_pct.mean()), d.fips.map(h.prem_LL_pct.mean())
d["min_prem"] = d.fips.map(h.prem_LLS_pct.min())
d["years_positive"] = d.fips.map(h.prem_LLS_pct.apply(lambda s: (s > 0).sum()))
pool = d[(d.n_years >= 5) & (d.mean_nat > 0)].nlargest(20, "mean_prem").copy()
thr = d.kids_under6_allpar_lf.median()
pool["pass_persistence"] = pool.years_positive == pool.n_years
pool["pass_market"] = pool.kids_under6_allpar_lf >= thr
pool["final_rank"] = pool.fips.map(RANK)
pool["pool_rank"] = range(1, len(pool) + 1)
pool[["pool_rank", "fips", "county_name", "state_abbr", "mean_prem", "mean_nat", "min_prem", "n_years", "years_positive",
      "kids_under6_allpar_lf", "pass_persistence", "pass_market", "final_rank"]].to_csv(T / "app_candidates.csv", index=False)
assert set(pool[pool.pass_persistence & pool.pass_market].fips) == set(top.fips)
allc = pd.DataFrame({"n": h.size(), "avg": h.prem_LLS_pct.mean(), "nat": h.prem_LL_pct.mean(), "last_year": h.year.max(),
                     "county_name": h.county_name.first(), "state_abbr": h.state_abbr.first()})
excl = allc[(allc.n >= 5) & (allc.nat > 0) & (~allc.index.isin(d.fips)) & (allc.avg >= pool.mean_prem.min())]
excl.sort_values("avg", ascending=False).to_csv(T / "app_excluded_no2022.csv")

# ---------------- backtest picks as of 2018 (same rule as 28_fp_math_checks.py) -----------------------------------------------
d18 = p[p.year == 2018].copy()
h18 = p[p.year.isin(range(2015, 2019))].groupby("fips")
d18["n_years"], d18["mean_prem"], d18["mean_nat"] = d18.fips.map(h18.size()), d18.fips.map(h18.prem_LLS_pct.mean()), d18.fips.map(h18.prem_LL_pct.mean())
c18 = d18[(d18.n_years >= 3) & (d18.mean_nat > 0)].nlargest(20, "mean_prem").copy()
c18 = c18[c18.fips.map(h18.prem_LLS_pct.apply(lambda s: (s > 0).all())) & (c18.kids_under6_allpar_lf >= d18.kids_under6_allpar_lf.median())].copy()
dem = ["kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022"]
c18["score"] = 0.5 * c18.mean_prem.rank(pct=True) + 0.5 * c18[dem].rank(pct=True).mean(axis=1)
c18 = c18.sort_values("score", ascending=False).head(10)
p22 = p[p.year == 2022].set_index("fips").prem_LLS_pct
pr22 = p22.rank(pct=True)
c18["premium_2022"] = c18.fips.map(p22)
c18["pct_rank_2022"] = c18.fips.map(pr22)
c18["in_top10_today"] = c18.fips.isin(top.fips)
c18[["county_name", "state_abbr", "mean_prem", "score", "premium_2022", "pct_rank_2022", "in_top10_today"]].to_csv(
    T / "app_backtest_2018.csv", index=False)

# ---------------- NDCP data quality for the top 10 ---------------------------------------------------------------------------
q = p[p.fips.isin(top.fips)].copy()
q["survey"] = q.price_imp_code.str[4] == "0"
dq = q.groupby("fips").agg(county_name=("county_name", "first"), state_abbr=("state_abbr", "first"), years=("year", "size"),
                           survey_years=("survey", "sum"),
                           survey_list=("year", lambda s: ", ".join(str(y) for y in s[q.loc[s.index, "survey"]])),
                           mean_premium_survey_years=("prem_LLS_pct", lambda s: s[q.loc[s.index, "survey"]].mean()),
                           mean_premium_all_years=("prem_LLS_pct", "mean"))
dq["rank"] = dq.index.map(RANK)
dq.sort_values("rank").to_csv(T / "app_ndcp_quality_top10.csv")

# =============================== figures ======================================================================================
# A: timeline of data use
fig = plt.figure(figsize=(W, 3.15), facecolor=SURF)
ax = fig.add_axes([0.30, 0.24, 0.68, 0.74])
ROWS = [("Cost model and premium", "fitted separately for every year", [(2015, 2022, ACCENT)]),
        ("Selection: average premium", "mean of the yearly premiums (≥ 5 years)", [(2015, 2022, ACCENT_LIGHT)]),
        ("Persistence filter", "premium > 0 in every observed year", [(2015, 2022, ACCENT_LIGHT)]),
        ("Market size, demand score", "ACS 5-year 2022", [(2022, 2022, ACCENT)]),
        ("Validation of the cost model", "train 2015–20 → test 2022", [(2015, 2020, CONTEXT), (2022, 2022, ORANGE)]),
        ("Backtest of the full rule", "rule with 2015–18 → outcome 2022", [(2015, 2018, CONTEXT), (2022, 2022, ORANGE)]),
        ("Survey-only persistence", "two direct survey prices ≈ 4.7 years apart", [(2015, 2022, "#d3e3f7")]),
        ("Risk checks", "competition 2022; trends 2015/2019 → 2022", [(2015, 2015, CONTEXT), (2019, 2019, CONTEXT), (2022, 2022, ACCENT)])]
for i, (lab, sub, segs) in enumerate(ROWS):
    y = len(ROWS) - 1 - i
    for x0, x1, col in segs:
        ax.add_patch(plt.Rectangle((x0 - 0.42, y - 0.28), x1 - x0 + 0.84, 0.56, color=col, lw=0))
    fig.text(0.01, (0.24 + 0.74 * (y + 0.5) / len(ROWS)) + 0.012, lab, fontsize=8.3, color=INK, va="center")
    fig.text(0.01, (0.24 + 0.74 * (y + 0.5) / len(ROWS)) - 0.024, sub, fontsize=7, color=MUTED, va="center")
ax.axvspan(2020.58, 2021.42, color="#fde8d7", zorder=0, lw=0)
ax.set_xlim(2014.5, 2022.6)
ax.set_ylim(-0.6, len(ROWS) - 0.4)
ax.set_xticks(range(2015, 2023))
ax.set_yticks([])
clean(ax, "x")
for xx_, yy_, col_, txt_ in [(0.30, 0.075, ACCENT, "single year used"), (0.47, 0.075, ACCENT_LIGHT, "years averaged or all required"),
                             (0.72, 0.075, "#d3e3f7", "pairs of survey years"),
                             (0.30, 0.02, ORANGE, "test / outcome year"), (0.47, 0.02, CONTEXT, "training years (data the rule may use)"),
                             (0.72, 0.02, "#fde8d7", "2021: no prices for CA, NC, PA, VA")]:
    fig.patches.append(plt.Rectangle((xx_, yy_), 0.014, 0.035, color=col_, transform=fig.transFigure, figure=fig))
    fig.text(xx_ + 0.02, yy_ + 0.018, txt_, fontsize=7, color=INK2, va="center")
save(fig, "app_A_timeline.png")

# B1: model c vs final, actual vs predicted (rank badges for the top 10)
d22["pred_c"] = fits["L"].fittedvalues
d22["pred_f"] = np.exp(fits["LLS"].fittedvalues)
fig, axs = plt.subplots(1, 2, figsize=(W, 3.25), facecolor=SURF)
fig.subplots_adjust(left=0.085, right=0.99, bottom=0.14, top=0.9, wspace=0.18)
lim = (60, 520)
for ax, col, lc, title in [(axs[0], "pred_c", ORANGE, "Model “c”: price on wage and rent (R² 0.61)"),
                           (axs[1], "pred_f", INK2, "Final: logs + state effects (R² 0.81)")]:
    clean(ax, "both")
    ax.fill_between(lim, lim, lim[1], color=ACCENT, alpha=0.05, lw=0)
    o = d22[~d22.fips.isin(top.fips)]
    ax.scatter(o[col], o.price_preschool_real2022, s=6, color=CONTEXT, alpha=0.85, lw=0)
    ax.plot(lim, lim, color=lc, lw=1.6)
    t_ = d22[d22.fips.isin(top.fips)]
    ax.scatter(t_[col], t_.price_preschool_real2022, s=70, color=ACCENT, edgecolor=SURF, lw=0.9, zorder=4)
    for r in t_.itertuples():
        if col == "pred_f" and RANK[r.fips] in (4, 5, 6, 7, 8):
            continue  # clustered at ~$240 predicted: unlabeled to avoid overlap (see left panel)
        ax.text(getattr(r, col), r.price_preschool_real2022, str(RANK[r.fips]), fontsize=5.8, color=SURF, ha="center",
                va="center", fontweight="bold", zorder=5)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.set_xlabel("Predicted weekly price, 2022")
axs[0].set_ylabel("Actual weekly price, 2022")
save(fig, "app_B_models.png")

# B2: elasticities by year
fig, axs = plt.subplots(1, 3, figsize=(W, 2.2), facecolor=SURF)
fig.subplots_adjust(left=0.07, right=0.99, bottom=0.14, top=0.86, wspace=0.32)
for ax, (est, se, title, col) in zip(axs[:2], [("wage_el", "wage_se", "Wage elasticity (95% CI)", ACCENT),
                                              ("rent_el", "rent_se", "Rent elasticity (95% CI)", ACCENT)]):
    clean(ax)
    ax.errorbar(yr.year, yr[est], yerr=1.96 * yr[se], fmt="o", color=col, ms=4, capsize=0, elinewidth=1.4)
    ax.axhline(0, color=INK2, lw=0.6)
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.set_xticks(yr.year)
    ax.set_xticklabels([f"’{y % 100}" for y in yr.year])
    ax.set_ylim(-0.1, 0.9)
clean(axs[2])
axs[2].plot(yr.year, yr.r2, "o-", color=ACCENT, ms=4, lw=1.4, label="final model")
axs[2].plot(yr.year, yr.r2_model_c, "o-", color=ORANGE, ms=4, lw=1.4, label="model “c”")
axs[2].set_ylim(0.4, 0.95)
axs[2].set_title("R² by year", fontsize=8.5, color=INK, loc="left")
axs[2].set_xticks(yr.year)
axs[2].set_xticklabels([f"’{y % 100}" for y in yr.year])
axs[2].legend(frameon=False, fontsize=7.5, loc="lower left", labelcolor=INK2, handlelength=1.2)
save(fig, "app_B_yearly.png")

# B3: residual diagnostics (final model, 2022)
m = fits["LLS"]
res, fv = m.resid, m.fittedvalues
sd = np.sqrt(m.mse_resid)
fig, axs = plt.subplots(1, 3, figsize=(W, 2.35), facecolor=SURF)
fig.subplots_adjust(left=0.07, right=0.99, bottom=0.2, top=0.86, wspace=0.32)
ax = axs[0]
clean(ax, "both")
ax.axhspan(-1.96 * sd, 1.96 * sd, color=ACCENT, alpha=0.06, lw=0)
istop = d22.fips.isin(top.fips).values
ax.scatter(fv[~istop], res[~istop], s=5, color=CONTEXT, lw=0)
ax.scatter(fv[istop], res[istop], s=16, color=ACCENT, lw=0, zorder=3)
ax.axhline(0, color=INK2, lw=0.6)
ax.set_title("Residual vs. fitted (log)", fontsize=8.5, color=INK, loc="left")
ax.set_xlabel("Fitted log price")
ax = axs[1]
clean(ax)
ax.hist(res, bins=40, color=ACCENT_LIGHT, edgecolor=SURF, lw=0.4, density=True)
xs = np.linspace(res.min(), res.max(), 200)
ax.plot(xs, stats.norm.pdf(xs, 0, sd), color=INK2, lw=1.1)
ax.set_title("Distribution vs. normal", fontsize=8.5, color=INK, loc="left")
ax.set_xlabel("Residual (log points)")
ax.set_yticks([])
ax = axs[2]
clean(ax, "both")
(osm, osr), _ = stats.probplot(res / sd, dist="norm")
order = np.argsort(np.asarray(res))
top_sorted = np.asarray(istop)[order]
ax.scatter(osm[~top_sorted], osr[~top_sorted], s=5, color=CONTEXT, lw=0)
ax.scatter(osm[top_sorted], osr[top_sorted], s=16, color=ACCENT, lw=0, zorder=3)
ax.set_ylabel("Standardized residual")
ax.plot([-3.5, 3.5], [-3.5, 3.5], color=INK2, lw=0.8)
ax.set_title("Normal Q–Q plot", fontsize=8.5, color=INK, loc="left")
ax.set_xlabel("Theoretical quantile")
save(fig, "app_B_residuals.png")

# D: survey-only persistence + correlation matrix
sv = p[p.price_imp_code.str[4] == "0"][["fips", "year", "prem_LLS_log", "state_abbr"]].sort_values("year")
pairs = []
for f, g in sv.groupby("fips"):
    if len(g) >= 2 and g.year.iloc[-1] - g.year.iloc[0] >= 2:
        pairs.append({"fips": f, "state": g.state_abbr.iloc[0], "p1": g.prem_LLS_log.iloc[0], "p2": g.prem_LLS_log.iloc[-1]})
pairs = pd.DataFrame(pairs)
pf = smf.ols("p2 ~ p1", data=pairs).fit(cov_type="cluster", cov_kwds={"groups": pairs["state"]})
corr = pd.read_csv(T / "fp_d_corr_full.csv", index_col=0)
fig = plt.figure(figsize=(W, 2.9), facecolor=SURF)
ax = fig.add_axes([0.075, 0.15, 0.40, 0.75])
clean(ax, "both")
ax.scatter(pairs.p1 * 100, pairs.p2 * 100, s=6, color=CONTEXT, lw=0)
tp = pairs[pairs.fips.isin(top.fips)]
ax.scatter(tp.p1 * 100, tp.p2 * 100, s=18, color=ACCENT, lw=0, zorder=3)
xx = np.linspace(-60, 70, 50)
ax.plot(xx, (pf.params["Intercept"] + pf.params["p1"] * xx / 100) * 100, color=ACCENT, lw=1.6)
ax.plot(xx, xx, color=INK2, lw=0.7, ls=(0, (3, 2)))
ax.set_xlim(-60, 70)
ax.set_ylim(-60, 70)
ax.text(-56, 62, f"slope {pf.params['p1']:.2f} (dashed: 1.00 = no fading)", fontsize=7.5, color=ACCENT, va="top")
ax.set_title(f"First vs. last direct survey premium, {len(pairs):,} counties", fontsize=8.5, color=INK, loc="left")
ax.set_xlabel("Premium in first survey year (log points × 100)")
ax.set_ylabel("Premium ≈ 4.7 years later")
ax2 = fig.add_axes([0.6, 0.15, 0.37, 0.75])
im = ax2.imshow(corr.values, cmap=RAMP, vmin=0.4, vmax=1)
for i in range(8):
    for j in range(8):
        ax2.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=6,
                 color=SURF if corr.values[i, j] > 0.75 else INK)
ax2.set_xticks(range(8))
ax2.set_xticklabels([f"’{c[-2:]}" for c in corr.columns])
ax2.set_yticks(range(8))
ax2.set_yticklabels([f"’{c % 100}" for c in corr.index])
ax2.tick_params(length=0)
for s in ax2.spines.values():
    s.set_visible(False)
ax2.set_title("Correlation of county premiums across years", fontsize=8.5, color=INK, loc="left")
save(fig, "app_D_persistence.png")

print("models 2022:\n", pd.DataFrame(rows).round(3).to_string(index=False))
print("\nyearly:\n", yr.round(3).to_string(index=False))
print("\nexcluded (no 2022 price):\n", excl.round(1).to_string())
print("\nbacktest 2018 picks:\n", c18[["county_name", "state_abbr", "premium_2022", "in_top10_today"]].round(1).to_string(index=False))
print("\npersistence check slope", round(pf.params["p1"], 3), "n", len(pairs))

# ---------------- pre-analysis figures in the appendix style (tasks 3 and 4) ------------------------------------------------
fits_ = pd.read_csv(T / "pre_t3_fits.csv").set_index("x")
fig, axs = plt.subplots(1, 2, figsize=(W, 2.9), facecolor=SURF, sharey=True)
fig.subplots_adjust(left=0.085, right=0.99, bottom=0.16, top=0.9, wspace=0.08)
for ax, (col, lab, fmtx, scale, unit) in zip(axs, [("childcare_wage_real2022", "(a) Childcare-worker wage, $/year", lambda v, _: f"${v / 1000:.0f}k", 1000, "per $1,000"),
                                                   ("median_gross_rent_real2022", "(b) Median gross rent, $/month", lambda v, _: f"${v:,.0f}", 100, "per $100")]):
    clean(ax, "both")
    f_ = fits_.loc[col]
    ax.scatter(d22[col], d22.price_preschool_real2022, s=6, color=ACCENT, alpha=0.35, lw=0)
    xx = np.linspace(d22[col].min(), d22[col].max(), 50)
    ax.plot(xx, f_.intercept + f_.slope * xx, color=INK, lw=1.6)
    ax.text(0.03, 0.96, f"+${f_.slope_scaled:.2f}/week {unit}\nR² = {f_.r2:.3f} · r = {f_['corr']:.2f}", transform=ax.transAxes, fontsize=7.8,
            color=INK, va="top")
    ax.set_title(lab, fontsize=8.5, color=INK, loc="left")
    ax.xaxis.set_major_formatter(fmtx)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
axs[0].set_ylabel("Preschool price, $/week (2022)")
save(fig, "app_P3_scatter.png")

reg_ = pd.read_csv(T / "pre_t4_regressions.csv")
mm = reg_[reg_.se_type == "metro"].set_index(["spec", "term"])
ROWS4 = [("Wage alone · (a)", "(a) wage", "wage_k", False), ("Wage, rent held constant · (c)", "(c) wage + rent", "wage_k", True),
         ("Rent alone · (b)", "(b) rent", "rent_100", False), ("Rent, wage held constant · (c)", "(c) wage + rent", "rent_100", True)]
fig = plt.figure(figsize=(W, 2.15), facecolor=SURF)
ax = fig.add_axes([0.29, 0.2, 0.69, 0.76])
clean(ax, "x")
ys = [3.6, 2.6, 1.0, 0.0]
for y, (lab, sp, t_, filled) in zip(ys, ROWS4):
    r = mm.loc[(sp, t_)]
    ax.plot([r.ci_low, r.ci_high], [y, y], color=ACCENT, lw=2.2, solid_capstyle="round")
    ax.scatter(r.coef, y, s=55, color=ACCENT if filled else SURF, edgecolor=ACCENT, lw=1.6, zorder=3)
    ax.text(r.ci_high + 0.25, y, f"{r.coef:.2f}  [{r.ci_low:.2f}, {r.ci_high:.2f}]", fontsize=7.8, color=INK, va="center")
    ax.text(-0.3, y, lab, fontsize=8.2, color=INK, ha="right", va="center", transform=ax.get_yaxis_transform() if False else ax.transData)
for top_, bot_, sp_ in [(3.6, 2.6, "wage_k"), (1.0, 0.0, "rent_100")]:
    a1 = mm.loc[("(a) wage" if sp_ == "wage_k" else "(b) rent", sp_)].coef
    c1 = mm.loc[("(c) wage + rent", sp_)].coef
    ax.annotate("", (c1, bot_ + 0.18), (a1, top_ - 0.18), arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    ax.text(c1 - 0.6, (top_ + bot_) / 2, f"−{abs(c1 / a1 - 1) * 100:.0f}% when both are included", fontsize=7.6, color=INK2, ha="right", va="center")
ax.set_xlim(0, 17.5)
ax.set_ylim(-0.6, 4.2)
ax.set_yticks([])
ax.set_xlabel("$/week per $1,000 of annual wage, or per $100 of monthly rent (95% CI, metro-clustered SEs)", fontsize=8)
save(fig, "app_P4_coefficients.png")


# ---------------- (c) do the demand characteristics go with a higher premium? ------------------------------------------------
# Average within-state log premium (counties observed >= 5 years, in the 2022 data) on standardized 2022 demand characteristics,
# with state effects; SEs clustered by metro area. Second model adds the two ACS characteristics we did not use.
dd = d22.copy()
hh = p.groupby("fips")
dd = dd[dd.fips.map(hh.size()) >= 5].copy()
dd["avg_log"] = dd.fips.map(hh.prem_LLS_log.mean())
zs = lambda x: (x - x.mean()) / x.std()
dd["z_kids"], dd["z_share"], dd["z_inc"] = zs(np.log1p(dd.kids_under6_allpar_lf)), zs(dd.under6_careneed_share), zs(np.log(dd.per_capita_income_real2022))
dd["z_col"], dd["z_ft"] = zs(dd.female_college_share), zs(dd.female_ftyr_share)
LABD = {"z_kids": "Children needing care (log)", "z_share": "Care-need share", "z_inc": "Income per capita (log)",
        "z_col": "Female college share", "z_ft": "Female full-time share"}
rows_d = []
for name, f in [("Used in the score", "avg_log ~ z_kids + z_share + z_inc"),
                ("+ the two unused ACS shares", "avg_log ~ z_kids + z_share + z_inc + z_col + z_ft")]:
    m_ = smf.ols(f + " + C(state_abbr)", data=dd).fit(cov_type="cluster", cov_kwds={"groups": dd.oews_area})
    for v in [t for t in m_.params.index if t.startswith("z_")]:
        rows_d.append({"model": name, "variable": LABD[v], "coef_pct_per_sd": (np.exp(m_.params[v]) - 1) * 100, "se_log": m_.bse[v],
                       "p": m_.pvalues[v], "n": int(m_.nobs), "r2_within": None})
    rows_d.append({"model": name, "variable": "R² (with state effects) / N", "coef_pct_per_sd": m_.rsquared, "se_log": None, "p": None,
                   "n": int(m_.nobs), "r2_within": None})
pd.DataFrame(rows_d).to_csv(T / "app_demand_premium.csv", index=False)
corr_ = d22[["female_college_share", "female_ftyr_share", "per_capita_income_real2022", "under6_careneed_share"]].corr()
corr_.to_csv(T / "app_demand_correlations.csv")

# ---------------- the Northern Virginia cluster ---------------------------------------------------------------------------
cl = pd.DataFrame({"n": hh.size(), "avg": hh.prem_LLS_pct.mean(), "nat": hh.prem_LL_pct.mean(), "county_name": hh.county_name.first(),
                   "state_abbr": hh.state_abbr.first(), "metro": hh.metro_area.first()})
cl = cl[(cl.n >= 5) & cl.metro.str.startswith("Washington-Arlington")].sort_values("avg", ascending=False)
cl["kids_2022"] = cl.index.map(d22.set_index("fips").kids_under6_allpar_lf)
cl["in_top10"] = cl.index.isin(top.fips)
cl.to_csv(T / "app_washington_counties.csv")
q20 = p[p.year <= 2020]
spread = q20.groupby("state_abbr").agg(sd=("prem_LLS_log", "std"), counties=("fips", "nunique"))
spread = spread[spread.counties >= 10].sort_values("sd", ascending=False)
spread["rank"] = range(1, len(spread) + 1)
spread.to_csv(T / "app_state_premium_spread.csv")
print("demand regression and Washington cluster tables written")
