"""PS4 Q1: restrict NDCP county prices to the metro analysis sample.

Definition (assignment, "Geography & crosswalks"): a county-year is in the metro sample if, in the
year-specific crosswalk, its OEWS area code begins with "00" (metropolitan area). Counties in
nonmetropolitan areas (any other prefix) are dropped. This sample is reused in PS4, PS5 and the
final project.

Inputs:
  data/interim/ndcp_prices_2015_2022.csv         (04_prepare_ndcp.py)
  data/crosswalks/county_oews_crosswalk.csv      (course-provided, unchanged)
Outputs:
  data/analysis/ndcp_metro_2015_2022.csv         metro county-years, all NDCP price columns +
                                                 oews_area / area_title (metro label)
  output/tables/ps4_q1_sample_construction.csv   counts at each step, by year
  output/tables/ps4_q1_imputation_2022.csv       imputation shares, metro sample, 2022
When reading the output, keep fips, oews_area and *_imp as text (dtype=str): they carry leading zeros.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "data/analysis").mkdir(exist_ok=True)
(ROOT / "output/tables").mkdir(parents=True, exist_ok=True)

# Codes are text: FIPS (5 chars) and five-digit imputation codes must keep their leading zeros.
TEXT = {"fips": str, "MCINFANT_imp": str, "MCTODDLER_imp": str, "MCPRESCHOOL_imp": str,
        **{f"{p}{a}_flag": str for p in ["MC", "_75C", "MFCC", "_75FCC"]
           for a in ["Infant", "Toddler", "Preschool"]}}
nd = pd.read_csv(ROOT / "data/interim/ndcp_prices_2015_2022.csv", dtype=TEXT)
assert nd["MCPRESCHOOL_imp"].dropna().str.len().eq(5).all()
cw = pd.read_csv(ROOT / "data/crosswalks/county_oews_crosswalk.csv", dtype=str)
cw["year"] = cw["year"].astype(int)
cw = cw.rename(columns={"county_fips": "fips", "state_abbr": "cw_state_abbr"})
assert not cw.duplicated(["year", "fips"]).any(), "crosswalk not unique on year x county"

# Year-specific join: each county-year gets that year's OEWS area.
m = nd.merge(cw, on=["year", "fips"], how="outer", indicator=True, validate="one_to_one")
m["is_metro"] = m["oews_area"].str.startswith("00")

# --- Diagnostics -------------------------------------------------------------------------
only_ndcp = m[m["_merge"] == "left_only"]
only_cw = m[m["_merge"] == "right_only"]
assert only_ndcp.empty, f"NDCP county-years without crosswalk entry:\n{only_ndcp[['year', 'fips']]}"
state_mismatch = m[(m["_merge"] == "both") & (m["state_abbr"] != m["cw_state_abbr"])]
assert state_mismatch.empty, "state abbreviation differs between NDCP and crosswalk"

metro_cw_no_ndcp = only_cw[only_cw["is_metro"]]
# Expected: two legacy FIPS codes the crosswalk still carries - 12025 (Dade County, renamed
# Miami-Dade 12086 in 1997) and 51515 (Bedford city, merged into Bedford County 51019 in 2013).
# NDCP uses the current codes, which are matched, so nothing is lost.
print("Metro counties in crosswalk but not in NDCP:")
print(metro_cw_no_ndcp[["year", "fips", "cw_state_abbr", "area_title"]].to_string(index=False)
      if len(metro_cw_no_ndcp) else "  none")

# --- Metro analysis sample -----------------------------------------------------------------
metro = m[(m["_merge"] == "both") & m["is_metro"]].drop(columns=["_merge", "is_metro", "cw_state_abbr"])
lead = ["year", "fips", "state_abbr", "state_name", "county_name", "oews_area", "area_title"]
metro = metro[lead + [c for c in metro.columns if c not in lead]].sort_values(["year", "fips"])
metro.to_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", index=False)

# --- Sample construction table -------------------------------------------------------------
both = m[m["_merge"] == "both"]
steps = pd.DataFrame({
    "ndcp_counties": nd.groupby("year").size(),
    "matched_to_crosswalk": both.groupby("year").size(),
    "nonmetro_dropped": both[~both["is_metro"]].groupby("year").size(),
    "metro_counties": metro.groupby("year").size(),
    "metro_areas": metro.groupby("year")["oews_area"].nunique(),
    "with_infant_price": metro.groupby("year")["MCINFANT"].count(),
    "with_toddler_price": metro.groupby("year")["MCTODDLER"].count(),
    "with_preschool_price": metro.groupby("year")["MCPRESCHOOL"].count(),
})
steps.index.name = "year"
steps.to_csv(ROOT / "output/tables/ps4_q1_sample_construction.csv")
print("\nSample construction by year:")
print(steps.to_string())

# Stability of the metro county set across years
yrs = metro.groupby("fips")["year"].nunique()
print(f"\nDistinct metro counties 2015-2022: {len(yrs)}; metro in all 8 years: {(yrs == 8).sum()}")
changers = metro[metro["fips"].isin(yrs[yrs < 8].index)]
print("Counties metro in only some years:",
      changers.groupby("fips").agg(state=("state_abbr", "first"), county=("county_name", "first"),
                                   years=("year", lambda s: f"{s.min()}-{s.max()} ({s.size})")).to_string())

# Where are 2022 prices missing?
miss22 = metro[(metro["year"] == 2022) & metro["MCPRESCHOOL"].isna()]
print("\n2022 metro counties without a preschool price, by state:",
      miss22["state_abbr"].value_counts().to_dict())

# --- Imputation shares, 2022 (documents the decision to keep imputed NDCP prices) ---------
names = ["from_other_age_group", "weekly_conversion", "state_to_county_model",
         "pctile_model", "between_survey_years"]
rows = []
for age in ["INFANT", "TODDLER", "PRESCHOOL"]:
    s = metro[(metro["year"] == 2022) & metro[f"MC{age}"].notna()]
    codes = s[f"MC{age}_imp"].dropna()
    row = {"age_group": age.lower(), "n_with_price": len(s),
           "any_imputation": s[f"MC{age}_imputed"].astype(float).mean()}
    for k, nm in enumerate(names):
        row[nm] = (codes.str[k] == "1").sum() / len(s)
    rows.append(row)
imp = pd.DataFrame(rows).round(3)
imp.to_csv(ROOT / "output/tables/ps4_q1_imputation_2022.csv", index=False)
print("\nShare of 2022 metro prices with each NDCP imputation:")
print(imp.to_string(index=False))
