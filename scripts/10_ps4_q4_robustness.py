"""PS4 Q4 robustness: does the voucher test depend on the unit of observation / independence assumption?

Baseline (09_ps4_q4_voucher_test.py): county = observation, iid standard errors.
Robustness checks, both years (2022 voucher $706, 2015 voucher $473; nominal monthly = weekly x 4.33):
  (1) State-clustered SEs: NDCP prices are often set per state rate zone (many counties share one
      price), so counties within a state are not independent. OLS of monthly price on a constant,
      CR1 cluster-robust SE by state, t reference with G-1 df (G = number of states).
  (2) Metro-area level: the ACF claim refers to "the average metro area". Average county prices
      within each OEWS metro area (unweighted), then a one-sample t-test across metro areas.

Inputs:  data/analysis/ndcp_metro_2015_2022.csv
Outputs: output/tables/ps4_q4_robustness.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
VOUCHER = {2022: 706.0, 2015: 473.0}
df = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype={"fips": str, "oews_area": str})

rows = []
for year, mu0 in VOUCHER.items():
    d = df[(df["year"] == year) & df["MCPRESCHOOL"].notna()].copy()
    d["monthly"] = d["MCPRESCHOOL"] * 4.33

    # Baseline: county, iid
    t = stats.ttest_1samp(d["monthly"], mu0)
    se = d["monthly"].std(ddof=1) / np.sqrt(len(d))
    rows.append({"year": year, "spec": "County, iid SE (baseline)", "n_obs": len(d), "n_clusters": np.nan,
                 "mean": d["monthly"].mean(), "se": se, "t_stat": t.statistic, "df": len(d) - 1,
                 "p_value": t.pvalue})

    # (1) County, state-clustered SE
    fit = sm.OLS(d["monthly"] - mu0, np.ones(len(d))).fit(cov_type="cluster",
                                                          cov_kwds={"groups": d["state_abbr"]})
    g = d["state_abbr"].nunique()
    tc = fit.params.iloc[0] / fit.bse.iloc[0]
    rows.append({"year": year, "spec": "County, state-clustered SE", "n_obs": len(d), "n_clusters": g,
                 "mean": d["monthly"].mean(), "se": fit.bse.iloc[0], "t_stat": tc, "df": g - 1,
                 "p_value": 2 * stats.t.sf(abs(tc), g - 1)})

    # (2) Metro-area level
    m = d.groupby("oews_area")["monthly"].mean()
    tm = stats.ttest_1samp(m, mu0)
    rows.append({"year": year, "spec": "Metro area (county avg.), iid SE", "n_obs": len(m), "n_clusters": np.nan,
                 "mean": m.mean(), "se": m.std(ddof=1) / np.sqrt(len(m)), "t_stat": tm.statistic,
                 "df": len(m) - 1, "p_value": tm.pvalue})

res = pd.DataFrame(rows)
res["gap_vs_voucher"] = res["mean"] - res["year"].map(VOUCHER)
res["gap_pct"] = res["gap_vs_voucher"] / res["year"].map(VOUCHER) * 100
res["reject_5pct"] = res["p_value"] < 0.05
res.to_csv(ROOT / "output/tables/ps4_q4_robustness.csv", index=False)
pd.set_option("display.width", 220, "display.float_format", lambda v: f"{v:.4g}")
print(res.to_string(index=False))
