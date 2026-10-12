"""Final project (d): are prices that exceed cost-based predictions stable over time?

Premium = within-state % premium (LLS), year-by-year fits (team decision). Analyses:
  1. Correlation matrix of county premiums across years; full sample and balanced panel (counties observed in
     all 8 years) to rule out composition effects (e.g. 2021: no NDCP prices for CA, NC, VA, PA).
  2. Persistence regressions (balanced panel): premium_2022 on premium_2015 / 2018 / 2019 (log points; slope < 1 =
     partial reversion to the mean), SEs clustered by state. Pooled one-year AR(1): premium_t on premium_{t-1}
     with year effects -> implied half-life of a premium shock.
  3. Quintile transitions: share of counties in the top premium quintile in 2015 (2018) that are still in the
     top quintile in 2022 (25-30% would be expected under no persistence... 20% exactly under independence).
  4. Interpolation check: NDCP interpolates prices between survey years, which mechanically smooths premiums.
     Re-estimate persistence using only pairs of years in which BOTH prices are direct survey values
     (5th imputation digit = 0) and at least 2 years apart.
  5. Top-10 premium paths 2015-2022, pre-COVID (2019) vs 2022, years positive, premium in survey years.

Inputs:  data/analysis/fp_premiums_2015_2022.csv, output/tables/fp_top10_final.csv
Outputs: output/tables/fp_d_*.csv
"""
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "output/tables"
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
p["lprem"] = p["prem_LLS_log"]
top10 = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
YEARS = list(range(2015, 2023))
w = p.pivot_table(index="fips", columns="year", values="lprem")
bal = w.dropna()
state = p.drop_duplicates("fips").set_index("fips").state_abbr

# 1. correlation matrices -------------------------------------------------------------------------
corr_full = w.corr()
corr_bal = bal.corr()
corr_full.round(3).to_csv(T / "fp_d_corr_full.csv")
corr_bal.round(3).to_csv(T / "fp_d_corr_balanced.csv")

# 2. persistence regressions -------------------------------------------------------------------------
rows = []
b = bal.copy()
b["state"] = state.reindex(b.index).values
for base in [2015, 2018, 2019, 2021]:
    dd = pd.DataFrame({"y": b[2022], "x": b[base], "state": b["state"]})
    f = smf.ols("y ~ x", data=dd).fit(cov_type="cluster", cov_kwds={"groups": dd["state"]})
    rows.append({"model": f"premium_2022 on premium_{base}", "n": int(f.nobs), "slope": f.params["x"],
                 "se_state_cluster": f.bse["x"], "r2": f.rsquared})
long = p.sort_values(["fips", "year"]).copy()
long["lag"] = long.groupby("fips")["lprem"].shift(1)
long["lag_year"] = long.groupby("fips")["year"].shift(1)
ar = long[(long.year - long.lag_year) == 1].dropna(subset=["lag"])
f = smf.ols("lprem ~ lag + C(year)", data=ar).fit(cov_type="cluster", cov_kwds={"groups": ar["state_abbr"]})
rho = f.params["lag"]
rows.append({"model": "pooled AR(1): premium_t on premium_t-1 + year effects", "n": int(f.nobs), "slope": rho,
             "se_state_cluster": f.bse["lag"], "r2": f.rsquared, "half_life_years": np.log(0.5) / np.log(rho)})
reg = pd.DataFrame(rows)
reg.to_csv(T / "fp_d_persistence_regressions.csv", index=False)

# 3. quintile transitions (balanced panel) -----------------------------------------------------------
q = bal.rank(pct=True)
trans = []
for base in [2015, 2018, 2019]:
    top_b = q[base] > 0.8
    trans.append({"from_year": base, "n_top_quintile": int(top_b.sum()),
                  "share_still_top_quintile_2022": (q.loc[top_b, 2022] > 0.8).mean(),
                  "share_still_above_median_2022": (q.loc[top_b, 2022] > 0.5).mean(),
                  "share_positive_premium_2022": (bal.loc[top_b, 2022] > 0).mean()})
trans = pd.DataFrame(trans)
trans.to_csv(T / "fp_d_quintile_transitions.csv", index=False)

# 4. survey-year-only persistence -------------------------------------------------------------------
sv = p[p.price_imp_code.str[4] == "0"][["fips", "year", "lprem", "state_abbr"]]
pairs = []
for fips, g in sv.groupby("fips"):
    g = g.sort_values("year")
    for (_, r1), (_, r2) in combinations(g.iterrows(), 2):
        if r2.year - r1.year >= 2:
            pairs.append({"fips": fips, "state": r1.state_abbr, "y1": r1.year, "y2": r2.year,
                          "gap": r2.year - r1.year, "p1": r1.lprem, "p2": r2.lprem})
pairs = pd.DataFrame(pairs)
# one pair per county: the widest gap (most demanding test)
widest = pairs.sort_values("gap").groupby("fips").tail(1)
fs = smf.ols("p2 ~ p1", data=widest).fit(cov_type="cluster", cov_kwds={"groups": widest["state"]})
survey = {"n_counties": len(widest), "n_states": widest.state.nunique(), "mean_gap_years": widest.gap.mean(),
          "corr": widest[["p1", "p2"]].corr().iloc[0, 1], "slope": fs.params["p1"], "se": fs.bse["p1"],
          "share_same_sign": (np.sign(widest.p1) == np.sign(widest.p2)).mean()}
pd.Series(survey).to_csv(T / "fp_d_survey_only.csv")

# 5. top-10 paths ------------------------------------------------------------------------------------------
t = p[p.fips.isin(top10.fips)].copy()
t["label"] = t.county_name.str.replace(" County", "").str.replace(" City", "") + ", " + t.state_abbr
path = t.pivot_table(index=["fips", "label"], columns="year", values="prem_LLS_pct").reindex(columns=YEARS)
path["years_obs"] = path[YEARS].notna().sum(axis=1)
path["years_pos"] = (path[YEARS] > 0).sum(axis=1)
path["min"] = path[YEARS].min(axis=1)
path["change_2019_2022_pp"] = path[2022] - path[2019]
t["survey"] = t.price_imp_code.str[4] == "0"
path["mean_survey_years"] = t[t.survey].groupby("fips").prem_LLS_pct.mean().reindex(path.index.get_level_values(0)).values
order = top10.fips.tolist()
path = path.reset_index().set_index("fips").loc[order].reset_index()
path.to_csv(T / "fp_d_top10_paths.csv", index=False)

pd.set_option("display.width", 260, "display.float_format", lambda v: f"{v:,.3f}")
print(f"Balanced panel: {len(bal)} counties observed in all 8 years")
print("Correlation with 2022 (full / balanced):",
      {y: (round(corr_full.loc[y, 2022], 3), round(corr_bal.loc[y, 2022], 3)) for y in YEARS[:-1]})
print("\nPersistence regressions:\n", reg.to_string(index=False))
print("\nQuintile transitions (balanced):\n", trans.to_string(index=False))
print("\nSurvey-years-only persistence:", {k: round(v, 3) for k, v in survey.items()})
print("\nTop-10 premium paths (% within-state):\n", path.drop(columns=["fips"]).round(1).to_string(index=False))
