"""Final project step 1: cost-based price models, historical validation, and the price premium.

Premium = how far a county's price lies above the price predicted from its costs (childcare-worker wage, rent).
Demand variables are deliberately NOT in the cost model: they are used later as selection criteria; putting
them in the model would remove demand-driven premiums from the residual.

Candidate cost models (all on the analysis dataset, real 2022 $):
  L   level:  price = a + b1*wage_k + b2*rent_100                     (= pre-analysis model "c")
  LL  log-log: log(price) = a + b1*log(wage) + b2*log(rent)          (premium in %; fits the fanning-out scatter)
  LS  level + state fixed effects                                     (robustness: level vs log)
  LLS log-log + state fixed effects                                  (premium relative to same-state counties)
Validation (historical):
  (1) temporal: fit on pooled 2015-2020 (+ year effects), predict 2022 -> out-of-sample RMSE / MAE in $/week
  (2) cross-sectional: 2022, 10-fold cross-validation grouped by metro area (no metro in train and test)
Premium per county-year from year-by-year fits (coefficients may change over time):
  level premium ($/week) = price - predicted;  log premium = log(price) - predicted log(price) -> % = exp()-1

Inputs:  data/analysis/analysis_dataset_2015_2022.csv
Outputs: data/analysis/fp_premiums_2015_2022.csv, output/tables/fp_model_validation.csv,
         output/tables/fp_top20_2022.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv",
                dtype={"fips": str, "oews_area": str, "price_imp_code": str})
a["price"] = a["price_preschool_real2022"]
a["wage_k"] = a["childcare_wage_real2022"] / 1000
a["rent_100"] = a["median_gross_rent_real2022"] / 100
a["lp"], a["lw"], a["lr"] = np.log(a["price"]), np.log(a["childcare_wage_real2022"]), np.log(a["median_gross_rent_real2022"])

MODELS = {"L": ("price ~ wage_k + rent_100", False),
          "LS": ("price ~ wage_k + rent_100 + C(state_abbr)", False),
          "LL": ("lp ~ lw + lr", True),
          "LLS": ("lp ~ lw + lr + C(state_abbr)", True)}


def to_dollars(pred, is_log, resid_var=0.0):
    return np.exp(pred + resid_var / 2) if is_log else pred  # smearing-type correction for log models


# --- (1) temporal validation: train 2015-2020, test 2022 ----------------------------------------------
train, test = a[a.year <= 2020], a[a.year == 2022]
rows = []
for name, (f, is_log) in MODELS.items():
    fit = smf.ols(f + " + C(year)", data=train).fit()
    te = test.copy()
    te["year"] = 2020  # use the latest training year effect for 2022 (2021 not in training)
    te = te[te.state_abbr.isin(train.state_abbr.unique())]
    pred = to_dollars(fit.predict(te), is_log, fit.mse_resid if is_log else 0)
    err = te["price"] - pred
    rows.append({"model": name, "validation": "temporal: train 2015-2020, test 2022", "n_test": len(te),
                 "rmse": np.sqrt((err ** 2).mean()), "mae": err.abs().mean(), "in_sample_r2": fit.rsquared})

# --- (2) cross-sectional grouped CV, 2022 ----------------------------------------------------------------
d22 = a[a.year == 2022].reset_index(drop=True)
gkf = GroupKFold(n_splits=10)
for name, (f, is_log) in MODELS.items():
    errs = []
    for tr, te_i in gkf.split(d22, groups=d22["oews_area"]):
        tr_d, te_d = d22.iloc[tr], d22.iloc[te_i]
        te_d = te_d[te_d.state_abbr.isin(tr_d.state_abbr.unique())]
        fit = smf.ols(f, data=tr_d).fit()
        pred = to_dollars(fit.predict(te_d), is_log, fit.mse_resid if is_log else 0)
        errs.append(te_d["price"] - pred)
    e = pd.concat(errs)
    full = smf.ols(f, data=d22).fit()
    rows.append({"model": name, "validation": "2022, 10-fold CV grouped by metro area", "n_test": len(e),
                 "rmse": np.sqrt((e ** 2).mean()), "mae": e.abs().mean(), "in_sample_r2": full.rsquared})
val = pd.DataFrame(rows)
val.to_csv(ROOT / "output/tables/fp_model_validation.csv", index=False)

# --- premiums per county-year (year-by-year fits) ----------------------------------------------------------
out = []
for y, g in a.groupby("year"):
    g = g.copy()
    for name, (f, is_log) in MODELS.items():
        fit = smf.ols(f, data=g).fit()
        if is_log:
            g[f"prem_{name}_log"] = fit.resid
            g[f"prem_{name}_pct"] = (np.exp(fit.resid) - 1) * 100
        else:
            g[f"prem_{name}_usd"] = fit.resid
            g[f"pred_{name}_usd"] = fit.fittedvalues
    out.append(g)
p = pd.concat(out)
keep = ["year", "fips", "county_name", "state_abbr", "metro_area", "oews_area", "price", "childcare_wage_real2022",
        "median_gross_rent_real2022", "pop_total", "kids_under6", "kids_under6_allpar_lf", "per_capita_income_real2022",
        "female_college_share", "female_ftyr_share", "under6_share", "under6_careneed_share", "price_imputed",
        "price_imp_code"] + [c for c in p.columns if c.startswith(("prem_", "pred_"))]
p[keep].to_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", index=False)

p22 = p[p.year == 2022]
top = p22.sort_values("prem_LL_pct", ascending=False).head(20)
top[["county_name", "state_abbr", "metro_area", "pop_total", "price", "pred_L_usd", "prem_L_usd", "prem_LL_pct",
     "prem_LLS_pct"]].to_csv(ROOT / "output/tables/fp_top20_2022.csv", index=False)

pd.set_option("display.width", 250, "display.float_format", lambda v: f"{v:,.2f}")
print(val.to_string(index=False))
print("\nRank correlation of 2022 premiums: L vs LL",
      round(p22.prem_L_usd.rank().corr(p22.prem_LL_pct.rank()), 3), "| LL vs LLS",
      round(p22.prem_LL_pct.rank().corr(p22.prem_LLS_pct.rank()), 3))
for col in ["prem_L_usd", "prem_LL_pct", "prem_LLS_pct"]:
    t20 = p22.nlargest(20, col)
    print(f"\nTop 20 by {col}: states {t20.state_abbr.value_counts().to_dict()}")
    print(t20[["county_name", "state_abbr", "pop_total", "price", col]].to_string(index=False))
