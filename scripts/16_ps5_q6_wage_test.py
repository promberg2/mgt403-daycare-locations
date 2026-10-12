"""PS5 task 6: were average inflation-adjusted childcare-worker wages the same in 2022 as in 2019?

H0: mu_2022 - mu_2019 = 0   vs   H1: mu_2022 - mu_2019 != 0   (two-sided, alpha = 0.05)
Wages: OEWS SOC 39-9011 mean annual wage in constant 2022 dollars (CPI-U).

Four versions, to show the choice of test does / does not matter:
  A. County level, two independent samples (Welch t-test)     - textbook difference-in-means test
  B. County level, paired t-test on each county's change      - same counties in both years
  C. Metro-area level, paired t-test (recommended)            - wages are measured per metro area, so
     counties in the same metro repeat one value; pairing each area with itself removes the
     between-area variation in wage levels
  D. Metro-area level, two independent samples (Welch)
Only areas / counties with a wage in BOTH years are used in the paired tests.

Inputs:  data/analysis/county_costs_metro_2015_2022_real.csv
Outputs: output/tables/ps5_q6_wage_test.csv, output/tables/ps5_q6_inputs.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data/analysis/county_costs_metro_2015_2022_real.csv", dtype={"fips": str, "oews_area": str})
W = "childcare_wage_real2022"

cty = d[d.year.isin([2019, 2022])].pivot_table(index="fips", columns="year", values=W)
area = (d[d.year.isin([2019, 2022])].dropna(subset=[W])
        .groupby(["year", "oews_area"])[W].first().unstack("year"))


def welch(x19, x22, label):
    x19, x22 = x19.dropna(), x22.dropna()
    n1, n2 = len(x19), len(x22)
    m1, m2, s1, s2 = x19.mean(), x22.mean(), x19.std(ddof=1), x22.std(ddof=1)
    se = np.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
    t = (m2 - m1) / se
    dfw = (s1 ** 2 / n1 + s2 ** 2 / n2) ** 2 / ((s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1))
    chk = stats.ttest_ind(x22, x19, equal_var=False)
    assert np.isclose(chk.statistic, t)
    return {"test": label, "n_2019": n1, "n_2022": n2, "mean_2019": m1, "mean_2022": m2, "sd_2019": s1,
            "sd_2022": s2, "diff": m2 - m1, "se": se, "t": t, "df": dfw, "p": chk.pvalue,
            "ci_low": (m2 - m1) - stats.t.ppf(0.975, dfw) * se, "ci_high": (m2 - m1) + stats.t.ppf(0.975, dfw) * se}


def paired(df, label):
    p = df[[2019, 2022]].dropna()
    dd = p[2022] - p[2019]
    n, mean, sd = len(dd), dd.mean(), dd.std(ddof=1)
    se = sd / np.sqrt(n)
    t = mean / se
    chk = stats.ttest_rel(p[2022], p[2019])
    assert np.isclose(chk.statistic, t)
    return {"test": label, "n_2019": n, "n_2022": n, "mean_2019": p[2019].mean(), "mean_2022": p[2022].mean(),
            "sd_2019": p[2019].std(ddof=1), "sd_2022": p[2022].std(ddof=1), "diff": mean, "sd_diff": sd,
            "se": se, "t": t, "df": n - 1, "p": chk.pvalue, "share_increase": (dd > 0).mean(),
            "ci_low": mean - stats.t.ppf(0.975, n - 1) * se, "ci_high": mean + stats.t.ppf(0.975, n - 1) * se}


res = pd.DataFrame([
    welch(cty[2019], cty[2022], "A. County, two-sample (Welch)"),
    paired(cty, "B. County, paired"),
    paired(area, "C. Metro area, paired (recommended)"),
    welch(area[2019], area[2022], "D. Metro area, two-sample (Welch)"),
])
res["reject_5pct"] = res["p"] < 0.05
res.to_csv(ROOT / "output/tables/ps5_q6_wage_test.csv", index=False)

pd.set_option("display.width", 250, "display.float_format", lambda v: f"{v:,.4f}")
print(res[["test", "n_2019", "n_2022", "mean_2019", "mean_2022", "diff", "se", "t", "df", "p", "ci_low",
           "ci_high", "reject_5pct"]].to_string(index=False))
print("\nShare of metro areas with a real wage increase 2019->2022:", round(res.loc[2, "share_increase"], 3))
print("Metro areas with a wage in 2019 / 2022 / both:", area[2019].notna().sum(), area[2022].notna().sum(),
      area[[2019, 2022]].dropna().shape[0])
