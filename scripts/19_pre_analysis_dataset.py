"""Pre-analysis task 1: define the analysis dataset = year x county observations where the price and all
predictor variables are non-missing (complete cases).

Price: NDCP median weekly center-based preschool price, 2022 dollars.
Predictors: childcare-worker wage, median gross rent, per-capita income (2022 dollars), population, kids under 6,
kids under 6 with all parents in the labor force, female college share, female full-time year-round share,
under-6 share, under-6 care-need share.
Requiring only price + wage + rent gives the identical sample in every year (checked below), so the definition
does not depend on which predictors are counted. The same sample is used for all pre-analysis regressions.

Input:  data/analysis/project_panel_2015_2022.csv
Output: data/analysis/analysis_dataset_2015_2022.csv
        output/tables/pre_t1_sample_flow.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data/analysis/project_panel_2015_2022.csv", dtype={"fips": str, "oews_area": str,
                                                                          "price_imp_code": str})
PRICE = "price_preschool_real2022"
PRED = ["childcare_wage_real2022", "median_gross_rent_real2022", "per_capita_income_real2022", "pop_total",
        "kids_under6", "kids_under6_allpar_lf", "female_college_share", "female_ftyr_share", "under6_share",
        "under6_careneed_share"]

complete = d[[PRICE] + PRED].notna().all(axis=1)
core = d[[PRICE, "childcare_wage_real2022", "median_gross_rent_real2022"]].notna().all(axis=1)
assert (complete == core).all(), "definition depends on which predictors are required"
a = d[complete].copy()
a.to_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", index=False)

g = d.groupby("year")
flow = pd.DataFrame({
    "metro_county_years": g.size(),
    "no_price": g[PRICE].apply(lambda s: s.isna().sum()),
    "price_but_no_wage": d[d[PRICE].notna() & d["childcare_wage_real2022"].isna()].groupby("year").size(),
    "price_wage_but_missing_acs": d[d[PRICE].notna() & d["childcare_wage_real2022"].notna() & ~complete].groupby("year").size(),
    "analysis_dataset": a.groupby("year").size(),
}).fillna(0).astype(int)
flow["share_kept_pct"] = (flow["analysis_dataset"] / flow["metro_county_years"] * 100).round(1)
flow.index.name = "year"
flow.to_csv(ROOT / "output/tables/pre_t1_sample_flow.csv")

pd.set_option("display.width", 200)
print(flow.to_string())
print(f"\nAnalysis dataset: {len(a):,} county-years, {a.fips.nunique():,} distinct counties, "
      f"{a.groupby('year').oews_area.nunique().to_dict()} metro areas by year")
bal = a.groupby("fips").year.nunique()
print(f"Counties in all 8 years: {(bal == 8).sum():,}")
print("2022 counties lost because of missing prices, by state:",
      d[(d.year == 2022) & d[PRICE].isna()].state_abbr.value_counts().head(8).to_dict())
