"""PS4 Q4: test whether the CCDF monthly voucher equals the mean price of median-priced center-based
preschool care across metro counties.

H0: mu = voucher   vs.   H1: mu != voucher   (two-sided, alpha = 0.05)
mu = mean monthly price = weekly NDCP median preschool price x 4.33, nominal dollars.
Vouchers (nominal): 2022 $706, 2015 $473.

Test statistic: t = (xbar - mu0) / (s / sqrt(n)), df = n - 1.
p-value (two-sided):
  normal approximation  p = 2 * (1 - Phi(|t|))            (Phi = standard normal CDF)
  exact t               p = 2 * (1 - F_{n-1}(|t|))        (F = CDF of Student's t, n-1 df)
With n ~ 1,000 the two are practically identical in interpretation.

Implementation note: on this machine a Windows Application Control policy blocks a compiled scipy
DLL, so the CDFs are computed without scipy: Phi via math.erfc, the t CDF via the regularized
incomplete beta function in mpmath (pure Python). Formula for t >= 0:
  1 - F_nu(t) = 0.5 * I_{nu/(nu+t^2)}(nu/2, 1/2)

Inputs:  data/analysis/ndcp_metro_2015_2022.csv
Outputs: output/tables/ps4_q4_voucher_test.csv
"""
import math
from pathlib import Path

import mpmath
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WEEKS_PER_MONTH = 4.33
VOUCHER = {2022: 706.0, 2015: 473.0}


def normal_two_sided_p(t: float) -> float:
    return math.erfc(abs(t) / math.sqrt(2))              # = 2 * (1 - Phi(|t|))


def t_two_sided_p(t: float, nu: int) -> float:
    return float(mpmath.betainc(nu / 2, 0.5, 0, nu / (nu + t * t), regularized=True))  # = 2*(1-F(|t|))


def t_critical(nu: int, alpha: float = 0.05) -> float:
    return float(mpmath.findroot(lambda q: t_two_sided_p(q, nu) - alpha, 1.96))


df = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype={"fips": str})

rows = []
for year, mu0 in VOUCHER.items():
    x = df.loc[df["year"] == year, "MCPRESCHOOL"].dropna() * WEEKS_PER_MONTH
    n, xbar, s = len(x), x.mean(), x.std(ddof=1)
    se = s / math.sqrt(n)
    t = (xbar - mu0) / se
    tcrit = t_critical(n - 1)
    rows.append({"year": year, "voucher_monthly": mu0, "n": n, "mean_monthly": xbar, "sd_monthly": s,
                 "se": se, "t_stat": t, "df": n - 1,
                 "p_value_t": t_two_sided_p(t, n - 1), "p_value_normal": normal_two_sided_p(t),
                 "t_crit_5pct": tcrit, "ci_low": xbar - tcrit * se, "ci_high": xbar + tcrit * se,
                 "reject_H0_5pct": t_two_sided_p(t, n - 1) < 0.05})

# sanity checks of the CDF implementations against known values
assert abs(normal_two_sided_p(1.959964) - 0.05) < 1e-6
assert abs(t_critical(10) - 2.228139) < 1e-5

res = pd.DataFrame(rows)
res.to_csv(ROOT / "output/tables/ps4_q4_voucher_test.csv", index=False)
pd.set_option("display.float_format", lambda v: f"{v:.6g}")
print(res.T.to_string())
