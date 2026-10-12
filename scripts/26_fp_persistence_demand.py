"""Final project step 2: persistence and demand facts for the top-20 candidates, and a historical test of
whether premiums persist.

Premium measure (team decision): LLS = within-state % premium from log(price) ~ log(wage) + log(rent) + state FE,
estimated year by year; robustness: national % premium (LL) > 0.

Persistence (per county, 2015-2022):
  years observed, years with LLS premium > 0, mean LLS premium 2015-2021, LLS premium in 2019 (pre-COVID),
  percentile rank of the premium within each year.
Historical test (all counties):
  - correlation of county premiums between years (2015->2022, 2019->2022, ...)
  - backtest: select the top 20 by mean premium 2015-2018 -> where are they in 2022 (mean premium, share with
    positive premium, share in top quintile) vs. all other counties.
Demand facts (2022): children under 6 needing care (all resident parents working) = market size; per-capita income;
  under-6 care-need share; female full-time year-round share; change in children under 6, 2015-2022.

Inputs:  data/analysis/fp_premiums_2015_2022.csv
Outputs: output/tables/fp_persistence_backtest.csv, output/tables/fp_top20_facts.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
p["pct_rank"] = p.groupby("year")["prem_LLS_pct"].rank(pct=True)
w = p.pivot_table(index="fips", columns="year", values="prem_LLS_pct")

# --- historical persistence test ---------------------------------------------------------------------
cor = {f"{a}->{b}": w[[a, b]].dropna().corr().iloc[0, 1] for a, b in
       [(2015, 2022), (2017, 2022), (2019, 2022), (2020, 2022), (2015, 2019), (2021, 2022)]}
early = p[p.year.between(2015, 2018)].groupby("fips").prem_LLS_pct.agg(["mean", "size"])
early = early[early["size"] >= 3]
sel = early.nlargest(20, "mean").index
y22 = p[p.year == 2022].set_index("fips")
y22["top_quintile"] = y22.pct_rank >= 0.8
inn, out = y22[y22.index.isin(sel)], y22[~y22.index.isin(sel)]
bt = pd.DataFrame([
    {"group": "Top 20 selected on 2015-2018 premium", "n_in_2022": len(inn),
     "mean_premium_2022_pct": inn.prem_LLS_pct.mean(), "share_positive_2022": (inn.prem_LLS_pct > 0).mean(),
     "share_top_quintile_2022": inn.top_quintile.mean()},
    {"group": "All other counties", "n_in_2022": len(out),
     "mean_premium_2022_pct": out.prem_LLS_pct.mean(), "share_positive_2022": (out.prem_LLS_pct > 0).mean(),
     "share_top_quintile_2022": out.top_quintile.mean()}])
bt.to_csv(ROOT / "output/tables/fp_persistence_backtest.csv", index=False)

# --- facts for the 2022 top 20 -----------------------------------------------------------------------------
d22 = p[p.year == 2022].copy()
top = d22[d22.prem_LL_pct > 0].nlargest(20, "prem_LLS_pct")
hist = p[p.fips.isin(top.fips)]
k15 = p[p.year == 2015].set_index("fips").kids_under6
facts = []
for _, r in top.iterrows():
    h = hist[hist.fips == r.fips]
    pre = h[h.year <= 2021]
    facts.append({
        "fips": r.fips, "county": f"{r.county_name}, {r.state_abbr}", "metro": r.metro_area,
        "premium_2022_pct": r.prem_LLS_pct, "premium_national_2022_pct": r.prem_LL_pct,
        "years_observed": len(h), "years_positive": int((h.prem_LLS_pct > 0).sum()),
        "mean_premium_2015_2021_pct": pre.prem_LLS_pct.mean() if len(pre) else np.nan,
        "premium_2019_pct": h.loc[h.year == 2019, "prem_LLS_pct"].squeeze() if (h.year == 2019).any() else np.nan,
        "min_pct_rank": h.pct_rank.min(),
        "kids_careneed_2022": r.kids_under6_allpar_lf, "kids_under6_2022": r.kids_under6, "pop_2022": r.pop_total,
        "income_2022": r.per_capita_income_real2022, "careneed_share": r.under6_careneed_share,
        "female_ftyr_share": r.female_ftyr_share,
        "kids_change_2015_2022_pct": (r.kids_under6 / k15.get(r.fips, np.nan) - 1) * 100,
        "price_2022": r.price, "price_imputed_code": r.price_imp_code})
f = pd.DataFrame(facts)
f.to_csv(ROOT / "output/tables/fp_top20_facts.csv", index=False)

pd.set_option("display.width", 260, "display.float_format", lambda v: f"{v:,.2f}")
print("Year-to-year correlation of county LLS premiums:", {k: round(v, 3) for k, v in cor.items()})
print("\nBacktest:\n", bt.to_string(index=False))
print("\nSample medians 2022: kids_careneed", d22.kids_under6_allpar_lf.median(), "| income",
      round(d22.per_capita_income_real2022.median()), "| careneed share", round(d22.under6_careneed_share.median(), 4),
      "| ftyr", round(d22.female_ftyr_share.median(), 3))
print(f.drop(columns=["fips", "metro"]).to_string(index=False))
