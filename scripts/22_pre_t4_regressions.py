"""Pre-analysis task 4: 2022 regressions of the median preschool price on (a) wages, (b) rent, (c) both.

Sample: 2022 analysis dataset (998 counties; identical for a, b, c).
Units: price = NDCP median weekly center-based preschool price (2022 $); wage per $1,000 of annual
childcare-worker wage; rent per $100 of monthly median gross rent (2022 $).
Standard errors: standard OLS, clustered by metro area (counties in a metro share one OEWS wage),
clustered by state (NDCP prices are often set by state rate zones). Coefficients are identical across SE types.
Also reported: the auxiliary regression of wage on rent (for the omitted-variable explanation).

Input:  data/analysis/analysis_dataset_2015_2022.csv
Output: output/tables/pre_t4_regressions.csv, output/tables/pre_t4_regression_c_summary.txt
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d = a[a.year == 2022].copy()
d["price"] = d["price_preschool_real2022"]
d["wage_k"] = d["childcare_wage_real2022"] / 1000
d["rent_100"] = d["median_gross_rent_real2022"] / 100

SPECS = {"(a) wage": ["wage_k"], "(b) rent": ["rent_100"], "(c) wage + rent": ["wage_k", "rent_100"]}
SE = {"OLS": {}, "metro": {"cov_type": "cluster", "cov_kwds": {"groups": d["oews_area"]}},
      "state": {"cov_type": "cluster", "cov_kwds": {"groups": d["state_abbr"]}}}
G = {"OLS": None, "metro": d["oews_area"].nunique(), "state": d["state_abbr"].nunique()}

rows = []
for spec, xs in SPECS.items():
    X = sm.add_constant(d[xs])
    base = sm.OLS(d["price"], X).fit()
    for se_name, kw in SE.items():
        f = sm.OLS(d["price"], X).fit(**kw)
        df_t = f.df_resid if G[se_name] is None else G[se_name] - 1
        for v in ["const"] + xs:
            t = f.params[v] / f.bse[v]
            rows.append({"spec": spec, "se_type": se_name, "term": v, "coef": f.params[v], "se": f.bse[v],
                         "t": t, "df": df_t, "p": 2 * stats.t.sf(abs(t), df_t),
                         "ci_low": f.params[v] - stats.t.ppf(0.975, df_t) * f.bse[v],
                         "ci_high": f.params[v] + stats.t.ppf(0.975, df_t) * f.bse[v],
                         "r2": base.rsquared, "adj_r2": base.rsquared_adj, "n": int(base.nobs),
                         "resid_sd": np.sqrt(base.mse_resid)})
    if spec == "(c) wage + rent":
        (ROOT / "output/tables/pre_t4_regression_c_summary.txt").write_text(
            sm.OLS(d["price"], X).fit(**SE["metro"]).summary().as_text(), encoding="utf-8")
res = pd.DataFrame(rows)
res.to_csv(ROOT / "output/tables/pre_t4_regressions.csv", index=False)

aux = sm.OLS(d["wage_k"], sm.add_constant(d["rent_100"])).fit()
aux2 = sm.OLS(d["rent_100"], sm.add_constant(d["wage_k"])).fit()
pd.set_option("display.width", 220, "display.float_format", lambda v: f"{v:,.4f}")
print(res[res.term != "const"].pivot_table(index=["spec", "term"], columns="se_type", values="se").round(3))
print()
print(res[(res.se_type == "metro")][["spec", "term", "coef", "se", "t", "p", "ci_low", "ci_high", "r2", "adj_r2", "n"]].to_string(index=False))
print(f"\nmetro clusters {G['metro']}, state clusters {G['state']}")
print(f"Auxiliary: wage_k = {aux.params['const']:.3f} + {aux.params['rent_100']:.4f} x rent_100 (R2 {aux.rsquared:.3f}); "
      f"rent_100 = {aux2.params['const']:.3f} + {aux2.params['wage_k']:.4f} x wage_k")
b = res[(res.se_type == "OLS") & (res.term != "const")].set_index(["spec", "term"])["coef"]
print("OVB check wage: b_a = b_c_wage + b_c_rent * delta(rent on wage):",
      round(b[("(c) wage + rent", "wage_k")] + b[("(c) wage + rent", "rent_100")] * aux2.params["wage_k"], 4), "vs", round(b[("(a) wage", "wage_k")], 4))
print("OVB check rent:", round(b[("(c) wage + rent", "rent_100")] + b[("(c) wage + rent", "wage_k")] * aux.params["rent_100"], 4),
      "vs", round(b[("(b) rent", "rent_100")], 4))
