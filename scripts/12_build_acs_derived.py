"""PS5 task 1: construct the derived ACS variables defined in the assignment (county x year, 2015-2022).

Assignment definitions (ACS 5-year; vintage YYYY = survey years YYYY-4 .. YYYY):
  per_capita_income      = B19301_001E          (dollars of the vintage year, nominal)
  pop_total              = B01001_001E
  kids_under6            = B23008_002E
  kids_under6_allpar_lf  = B23008_004E + B23008_010E + B23008_013E
                           (under 6, all resident parents in the labor force: both of two parents,
                            or the single resident father / mother)
  median_gross_rent      = B25064_001E          (rent + utilities, dollars of the vintage year)
  female_college_share   = (B15002_032E + _033E + _034E + _035E) / B15002_019E
                           (women 25+ with bachelor's, master's, professional or doctorate degree)
  female_ftyr_share      = B23022_029E / B23022_026E
                           (women 16-64 who worked full-time, 50-52 weeks)
  under6_share           = kids_under6 / pop_total
  under6_careneed_share  = kids_under6_allpar_lf / pop_total     (denominator as in the assignment)

Input:  data/interim/acs5_county_2015_2022.csv   (03_get_acs.py)
Output: data/interim/acs5_county_derived_2015_2022.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
acs = pd.read_csv(ROOT / "data/interim/acs5_county_2015_2022.csv", dtype={"fips": str})
assert acs["fips"].str.len().eq(5).all() and not acs.duplicated(["year", "fips"]).any()

d = acs[["year", "fips", "county_name"]].copy()
d["per_capita_income"] = acs["B19301_001E"]
d["pop_total"] = acs["B01001_001E"]
d["kids_under6"] = acs["B23008_002E"]
d["kids_under6_allpar_lf"] = acs[["B23008_004E", "B23008_010E", "B23008_013E"]].sum(axis=1, min_count=3)
d["median_gross_rent"] = acs["B25064_001E"]
d["female_college_share"] = acs[["B15002_032E", "B15002_033E", "B15002_034E", "B15002_035E"]].sum(
    axis=1, min_count=4) / acs["B15002_019E"]
d["female_ftyr_share"] = acs["B23022_029E"] / acs["B23022_026E"]
d["under6_share"] = d["kids_under6"] / d["pop_total"]
d["under6_careneed_share"] = d["kids_under6_allpar_lf"] / d["pop_total"]

shares = ["female_college_share", "female_ftyr_share", "under6_share", "under6_careneed_share"]
for s in shares:
    ok = d[s].dropna().between(0, 1).all()
    assert ok, f"{s} outside [0, 1]"
both = d[["kids_under6_allpar_lf", "kids_under6"]].dropna()
assert (both["kids_under6_allpar_lf"] <= both["kids_under6"]).all()

d.to_csv(ROOT / "data/interim/acs5_county_derived_2015_2022.csv", index=False)

pd.set_option("display.width", 220)
print("Counties per year:", d.groupby("year").size().to_dict())
print("\nMissing values by variable (all years):")
print(d.drop(columns=["year", "fips", "county_name"]).isna().sum().to_string())
miss = d[d.drop(columns=["year", "fips", "county_name"]).isna().any(axis=1)]
print("\nCounty-years with any missing value:", miss[["year", "fips", "county_name"]].to_string(index=False)
      if len(miss) <= 15 else f"{len(miss)} rows")
print("\n2022 summary (all ACS counties incl. PR):")
print(d[d.year == 2022].drop(columns=["year", "fips", "county_name"]).describe().T[["count", "mean", "std", "min", "max"]].round(4).to_string())
ct22 = d[(d.year == 2022) & d.fips.str.startswith("09")]
print("\nConnecticut in 2022:", ct22[["fips", "county_name"]].to_string(index=False))
