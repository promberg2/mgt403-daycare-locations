"""Final project step 4: methodological checks of the selection.

(A) Score scaling: premium strength and demand components on the same scale (percentile ranks among the
    candidates passing the filters) so that the 50/50 weighting is really 50/50. Compared with the previous
    mixed scaling.
(B) Statistical distinguishability: 2022 LLS model fit (log price ~ log wage + log rent + state FE); for each
    candidate the studentized residual and whether the price lies above the model's 95% prediction interval.
(C) Residual diagnostics for the 2022 LLS model: residual SD, skewness, residual-vs-fitted correlation,
    Breusch-Pagan test, residuals by county size.
(D) Full-rule backtest: apply the complete rule "as of 2018" (average premium and persistence 2015-2018, 2018 demand)
    and evaluate the selected counties' premiums in 2022 vs. all other counties.
(E) Data quality: for each top-10 county, number of years whose price is a direct survey value
    (NDCP imputation code without interpolation between survey years, 5th digit = 0).

Inputs:  data/analysis/fp_premiums_2015_2022.csv, data/analysis/analysis_dataset_2015_2022.csv
Outputs: output/tables/fp_checks_*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan

ROOT = Path(__file__).resolve().parents[1]
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
a["lp"], a["lw"], a["lr"] = (np.log(a.price_preschool_real2022), np.log(a.childcare_wage_real2022),
                             np.log(a.median_gross_rent_real2022))
T = ROOT / "output/tables"


def rule(year, prem_years, w_prem=0.5, pool=20, scaling="within", min_years=None):
    """Team rule (option 1): pool = top 20 by AVERAGE within-state premium over prem_years (avg national > 0)."""
    d = p[p.year == year].copy()
    h = p[p.year.isin(prem_years)].groupby("fips")
    min_years = min_years or max(3, len(prem_years) - 3)
    d["n_years"], d["mean_prem"], d["mean_nat"] = d.fips.map(h.size()), d.fips.map(h.prem_LLS_pct.mean()), d.fips.map(h.prem_LL_pct.mean())
    cand = d[(d.n_years >= min_years) & (d.mean_nat > 0)].nlargest(pool, "mean_prem").copy()
    cand["pass_pers"] = cand.fips.map(h.prem_LLS_pct.apply(lambda s: (s > 0).all()))
    cand = cand[cand.pass_pers & (cand.kids_under6_allpar_lf >= d.kids_under6_allpar_lf.median())].copy()
    dem = ["kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022"]
    if scaling == "within":
        cand["demand_index"] = cand[dem].rank(pct=True).mean(axis=1)
    else:  # earlier implementation: demand percentiles relative to the whole year sample
        cand["demand_index"] = np.mean([[(d[c] <= v).mean() for v in cand[c]] for c in dem], axis=0)
    cand["premium_strength"] = cand.mean_prem.rank(pct=True)
    cand["score"] = w_prem * cand.premium_strength + (1 - w_prem) * cand.demand_index
    return cand.sort_values("score", ascending=False)


# (A) scaling --------------------------------------------------------------------------------------
new = rule(2022, range(2015, 2023), scaling="within")
old = rule(2022, range(2015, 2023), scaling="sample")
comp = new[["county_name", "state_abbr", "premium_strength", "demand_index", "score"]].copy()
comp["rank_new"] = range(1, len(comp) + 1)
comp["rank_old"] = comp.index.map(dict(zip(old.index, range(1, len(old) + 1))))
comp.to_csv(T / "fp_checks_A_scaling.csv", index=False)
spread = pd.DataFrame({"old": old[["premium_strength", "demand_index"]].agg(["min", "max", "std"]).stack(),
                       "new": new[["premium_strength", "demand_index"]].agg(["min", "max", "std"]).stack()})

# (B) + (C) 2022 LLS model ------------------------------------------------------------------------------
d22 = a[a.year == 2022].reset_index(drop=True)
fit = smf.ols("lp ~ lw + lr + C(state_abbr)", data=d22).fit()
infl = fit.get_influence()
d22["resid"] = fit.resid
d22["student"] = infl.resid_studentized_external
pr = fit.get_prediction(d22).summary_frame(alpha=0.05)
d22["above_95pi"] = d22.lp > pr["obs_ci_upper"]
d22["pi_upper_pct"] = (np.exp(pr["obs_ci_upper"] - fit.fittedvalues) - 1) * 100
top10 = new.head(10)
b = d22[d22.fips.isin(top10.fips)][["county_name", "state_abbr", "resid", "student", "above_95pi", "pi_upper_pct"]]
b["premium_pct"] = (np.exp(b.resid) - 1) * 100
b.to_csv(T / "fp_checks_B_significance.csv", index=False)
# (B2) the selection uses the AVERAGE premium: how unusual is each top-10 county's average premium relative to the
# distribution of average premiums across all counties observed at least 5 years? (log points, within-state)
g = p.groupby("fips")
avg = pd.DataFrame({"mean_log": g.prem_LLS_log.mean(), "n": g.size()})
avg = avg[avg.n >= 5]
avg["z"] = (avg.mean_log - avg.mean_log.mean()) / avg.mean_log.std()
avg["pct_rank"] = avg.mean_log.rank(pct=True)
b2 = avg.loc[avg.index.intersection(top10.fips)].join(p.drop_duplicates("fips").set_index("fips")[["county_name", "state_abbr"]])
b2["mean_premium_pct"] = (np.exp(b2.mean_log) - 1) * 100
b2["above_p95"] = b2.pct_rank >= 0.95
b2.to_csv(T / "fp_checks_B2_average_premium.csv")
bp = het_breuschpagan(fit.resid, fit.model.exog)
size_q = pd.qcut(d22.pop_total, 4, labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"])
diag = {"n": int(fit.nobs), "r2": fit.rsquared, "resid_sd_log": np.sqrt(fit.mse_resid),
        "resid_skew": stats.skew(fit.resid), "resid_kurtosis": stats.kurtosis(fit.resid),
        "corr_resid_fitted": np.corrcoef(fit.resid, fit.fittedvalues)[0, 1], "breusch_pagan_p": bp[1],
        "share_above_95pi_all": d22.above_95pi.mean(), "n_above_95pi_all": int(d22.above_95pi.sum())}
pd.Series(diag).to_csv(T / "fp_checks_C_diagnostics.csv")
by_size = d22.groupby(size_q, observed=True).resid.agg(["mean", "std", "size"])

# (D) full-rule backtest as of 2018 ----------------------------------------------------------------------
sel18 = rule(2018, range(2015, 2019)).head(10)
y22 = p[p.year == 2022].set_index("fips")
y22["pct_rank"] = y22.prem_LLS_pct.rank(pct=True)
inn = y22[y22.index.isin(sel18.fips)]
out = y22[~y22.index.isin(sel18.fips)]
bt = pd.DataFrame([{"group": "Top 10 by full rule as of 2018", "n_in_2022": len(inn), "mean_premium_2022": inn.prem_LLS_pct.mean(),
                    "share_positive": (inn.prem_LLS_pct > 0).mean(), "share_top_quintile": (inn.pct_rank >= .8).mean(),
                    "overlap_with_2022_top10": len(set(sel18.fips) & set(top10.fips))},
                   {"group": "All other counties", "n_in_2022": len(out), "mean_premium_2022": out.prem_LLS_pct.mean(),
                    "share_positive": (out.prem_LLS_pct > 0).mean(), "share_top_quintile": (out.pct_rank >= .8).mean(),
                    "overlap_with_2022_top10": np.nan}])
# Same comparison without counties whose 2022 NDCP price is an extrapolation (CA and VA: no 2022 market-rate survey),
# because the team's own decision D2 does not rely on those prices.
EXTRAP = ("CA", "VA")
inn_x, out_x = inn[~inn.state_abbr.isin(EXTRAP)], out[~out.state_abbr.isin(EXTRAP)]
bt = pd.concat([bt, pd.DataFrame([
    {"group": "Top 10 by full rule as of 2018, excl. CA/VA (2022 prices extrapolated)", "n_in_2022": len(inn_x),
     "mean_premium_2022": inn_x.prem_LLS_pct.mean(), "share_positive": (inn_x.prem_LLS_pct > 0).mean(),
     "share_top_quintile": (inn_x.pct_rank >= .8).mean(), "overlap_with_2022_top10": np.nan},
    {"group": "All other counties, excl. CA/VA", "n_in_2022": len(out_x), "mean_premium_2022": out_x.prem_LLS_pct.mean(),
     "share_positive": (out_x.prem_LLS_pct > 0).mean(), "share_top_quintile": (out_x.pct_rank >= .8).mean(),
     "overlap_with_2022_top10": np.nan}])], ignore_index=True)
bt.to_csv(T / "fp_checks_D_backtest_full_rule.csv", index=False)

# (E) data quality ------------------------------------------------------------------------------------
q = p[p.fips.isin(top10.fips)].copy()
q["survey_year"] = q.price_imp_code.str[4] == "0"
e = q.groupby(["fips", "county_name", "state_abbr"]).agg(years=("year", "size"), survey_years=("survey_year", "sum"),
                                                         survey_list=("year", lambda s: ",".join(str(y) for y in s[q.loc[s.index, "survey_year"]])))
e.to_csv(T / "fp_checks_E_data_quality.csv")

pd.set_option("display.width", 250, "display.float_format", lambda v: f"{v:,.3f}")
print("(A) Component spread, old vs new scaling:\n", spread.to_string())
print(comp.to_string(index=False))
print("\n(B) 2022 significance of top-10 premiums:\n", b.to_string(index=False))
print(f"\n(B2) Average premium vs. all {len(avg)} counties with >= 5 years:\n",
      b2[["county_name", "state_abbr", "n", "mean_premium_pct", "z", "pct_rank", "above_p95"]].to_string())
print("\n(C) Diagnostics:", {k: round(v, 4) for k, v in diag.items()})
print("Residuals by county size quartile:\n", by_size.to_string())
print("\n(D) Full-rule backtest (as of 2018):", sel18.county_name.str.cat(sel18.state_abbr, sep=", ").tolist())
print(bt.to_string(index=False))
print("\n(E) Data quality:\n", e.to_string())
