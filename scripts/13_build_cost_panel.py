"""PS5 task 3: merge OEWS area wages down to counties, attach ACS county data, keep metro counties.

Steps
  1. Crosswalk (course file, county x year -> OEWS area + area title) is the backbone.
  2. Keep metro counties: oews_area begins with "00".
     Drop two legacy FIPS codes the crosswalk still carries (12025 Dade County -> now 12086 Miami-Dade;
     51515 Bedford city -> merged into 51019 Bedford County). They are not counties any more, have no
     ACS or NDCP data, and their current counties are already in the crosswalk. The resulting county set
     is identical to the PS4 metro analysis sample (checked below).
  3. Join OEWS SOC 39-9011 wages on [year, oews_area]. The BLS area code was zero-padded to 7 characters
     in 02_get_oews.py (e.g. 31080 -> 0031080). Metropolitan-division rows (2015-2017) have their own
     codes and are not used; the whole-MSA rows from BLS's aMSA file are.
  4. Join ACS derived variables on [year, county FIPS] (5-character strings).
  5. Metro label = area_title from the crosswalk.

Connecticut 2022: the 2022 ACS reports CT's 9 planning regions (09110-09190), while the crosswalk uses
the 8 old counties (09001-09015). Those 8 county-years get no ACS values (left missing, documented).

Inputs:  data/crosswalks/county_oews_crosswalk.csv, data/interim/oews_childcare_workers_2015_2022.csv,
         data/interim/acs5_county_derived_2015_2022.csv, data/analysis/ndcp_metro_2015_2022.csv (check only)
Output:  data/analysis/county_costs_metro_2015_2022.csv   (identified by year x fips)
         output/tables/ps5_q3_merge_diagnostics.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FIPS = {"12025", "51515"}

cw = pd.read_csv(ROOT / "data/crosswalks/county_oews_crosswalk.csv", dtype=str)
cw["year"] = cw["year"].astype(int)
cw = cw.rename(columns={"county_fips": "fips"})
oews = pd.read_csv(ROOT / "data/interim/oews_childcare_workers_2015_2022.csv",
                   dtype={"oews_area": str, "a_mean_raw": str})
acs = pd.read_csv(ROOT / "data/interim/acs5_county_derived_2015_2022.csv", dtype={"fips": str})

assert cw["oews_area"].str.len().eq(7).all() and oews["oews_area"].str.len().eq(7).all()
assert not cw.duplicated(["year", "fips"]).any()

# 1-2. metro counties from the crosswalk
metro = cw[cw["oews_area"].str.startswith("00") & ~cw["fips"].isin(LEGACY_FIPS)].copy()

# 3. OEWS wages on [year, oews_area]
w = oews.loc[~oews["is_division"], ["year", "oews_area", "a_mean", "h_mean", "tot_emp", "a_mean_raw"]]
w = w.rename(columns={"a_mean": "childcare_wage", "h_mean": "childcare_wage_hourly",
                      "tot_emp": "childcare_emp", "a_mean_raw": "childcare_wage_raw"})
m = metro.merge(w, on=["year", "oews_area"], how="left", validate="many_to_one", indicator="_oews")

# 4. ACS on [year, fips]
m = m.merge(acs.drop(columns=["county_name"]), on=["year", "fips"], how="left", validate="one_to_one",
            indicator="_acs")

# 5. order columns; metro label = crosswalk area_title
m = m.rename(columns={"area_title": "metro_area"})
lead = ["year", "fips", "state_abbr", "oews_area", "metro_area"]
out = m[lead + [c for c in m.columns if c not in lead and not c.startswith("_")]].sort_values(["year", "fips"])
assert not out.duplicated(["year", "fips"]).any()
out.to_csv(ROOT / "data/analysis/county_costs_metro_2015_2022.csv", index=False)

# --- Diagnostics ------------------------------------------------------------------------------
ndcp = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype={"fips": str}, usecols=["year", "fips"])
same_set = set(map(tuple, out[["year", "fips"]].values)) == set(map(tuple, ndcp[["year", "fips"]].values))
print("County set identical to PS4 metro sample:", same_set)

diag = pd.DataFrame({
    "crosswalk_counties": cw.groupby("year").size(),
    "metro_counties": out.groupby("year").size(),
    "metro_areas": out.groupby("year")["oews_area"].nunique(),
    "wage_missing": out.groupby("year")["childcare_wage"].apply(lambda s: s.isna().sum()),
})
diag["wage_missing_pct"] = (diag["wage_missing"] / diag["metro_counties"] * 100).round(2)
diag["wage_area_not_in_bls"] = m[m["_oews"] == "left_only"].groupby("year").size()
diag["wage_suppressed_by_bls"] = m[(m["_oews"] == "both") & m["childcare_wage"].isna()].groupby("year").size()
diag["acs_missing_rows"] = m[m["_acs"] == "left_only"].groupby("year").size()
diag = diag.fillna(0).astype({c: int for c in diag.columns if c != "wage_missing_pct"})
diag.index.name = "year"
(ROOT / "output/tables").mkdir(parents=True, exist_ok=True)
diag.to_csv(ROOT / "output/tables/ps5_q3_merge_diagnostics.csv")

pd.set_option("display.width", 220)
print("\nMerge diagnostics by year:\n", diag.to_string())
print(f"\nOverall: {out['childcare_wage'].isna().sum()} of {len(out)} metro county-years without a wage "
      f"({out['childcare_wage'].isna().mean() * 100:.2f}%)")
mw = out[out["childcare_wage"].isna()]
print("\nMetro areas without a wage (year: areas):")
for y, g in mw.groupby("year"):
    print(f"  {y}: " + "; ".join(f"{t} ({n})" for t, n in g.groupby("metro_area").size().items()))
acs_miss = m[m["_acs"] == "left_only"]
print("\nCounty-years without ACS row:", acs_miss[["year", "fips", "state_abbr"]].to_string(index=False))
print("\nOther ACS missing values in the panel:",
      out[["per_capita_income", "median_gross_rent", "female_college_share"]].isna().sum().to_dict())
