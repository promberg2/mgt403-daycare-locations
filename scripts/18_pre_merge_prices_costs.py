"""Pre-analysis: merge NDCP county prices onto the year x county cost/demand file from Problem Set 5.

Both inputs are built on the same metro analysis sample (crosswalk oews_area begins "00"), so the join on
[year, fips] should be one-to-one with every row matched. No rows are dropped here; the analysis dataset
(complete cases) is defined in the next step.

Price variables kept (NDCP, center-based, median weekly full-time price):
  MCPRESCHOOL / MCPRESCHOOL_real2022     preschool (36-54 months) - the project's focus
  MCINFANT_real2022, MCTODDLER_real2022  other age groups, for context
  MCPRESCHOOL_imp, MCPRESCHOOL_imputed   NDCP imputation code / flag (see PS4)

Inputs:  data/analysis/county_costs_metro_2015_2022_real.csv   (PS5, task 5)
         data/analysis/ndcp_metro_2015_2022_real.csv           (PS4, Q3)
Output:  data/analysis/project_panel_2015_2022.csv             (identified by year x fips)
         output/tables/pre_merge_coverage.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TXT = {"fips": str, "oews_area": str, "MCPRESCHOOL_imp": str}

costs = pd.read_csv(ROOT / "data/analysis/county_costs_metro_2015_2022_real.csv", dtype=TXT)
prices = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022_real.csv", dtype=TXT,
                     usecols=["year", "fips", "county_name", "state_name", "MCPRESCHOOL", "MCPRESCHOOL_real2022",
                              "MCINFANT_real2022", "MCTODDLER_real2022", "MCPRESCHOOL_imp", "MCPRESCHOOL_imputed"])
prices = prices.rename(columns={"MCPRESCHOOL": "price_preschool", "MCPRESCHOOL_real2022": "price_preschool_real2022",
                                "MCINFANT_real2022": "price_infant_real2022", "MCTODDLER_real2022": "price_toddler_real2022",
                                "MCPRESCHOOL_imp": "price_imp_code", "MCPRESCHOOL_imputed": "price_imputed"})

m = costs.merge(prices, on=["year", "fips"], how="outer", validate="one_to_one", indicator=True)
print("Merge result:", m["_merge"].value_counts().to_dict())
assert (m["_merge"] == "both").all(), "county-years present in only one file"
m = m.drop(columns="_merge")

lead = ["year", "fips", "county_name", "state_abbr", "state_name", "oews_area", "metro_area",
        "price_preschool", "price_preschool_real2022"]
m = m[lead + [c for c in m.columns if c not in lead]].sort_values(["year", "fips"])
assert not m.duplicated(["year", "fips"]).any()
m.to_csv(ROOT / "data/analysis/project_panel_2015_2022.csv", index=False)

cov = pd.DataFrame({
    "county_years": m.groupby("year").size(),
    "with_price": m.groupby("year")["price_preschool"].count(),
    "with_wage": m.groupby("year")["childcare_wage"].count(),
    "with_rent": m.groupby("year")["median_gross_rent"].count(),
    "price_wage_rent": m.dropna(subset=["price_preschool", "childcare_wage", "median_gross_rent"]).groupby("year").size(),
})
cov.index.name = "year"
cov.to_csv(ROOT / "output/tables/pre_merge_coverage.csv")
print(f"\nPanel: {len(m):,} county-years x {m.shape[1]} columns")
print(cov.to_string())
