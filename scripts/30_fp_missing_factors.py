"""Final project (e): factors the prediction does not include, quantified where public data allow.

1. Competition / supply: Census County Business Patterns (CBP), NAICS 624410 "Child Day Care Services":
   establishments and employees per county, 2016, 2019, 2022 (employer establishments; home-based providers
   without employees are not covered). Density = establishments per 1,000 children under 6 needing care.
2. Demand trend: change in children under 6, 2015 -> 2022 (ACS 5-year).
3. Cost dynamics: real (2022 $) childcare-worker wage change 2019 -> 2022 (metro OEWS) and real median gross rent
   change 2015 -> 2022 (ACS).
Each indicator for the top 10 is compared with the 2022 analysis sample (median and county percentile).

Inputs:  Census API (key in census_api_key.txt), data/analysis/fp_premiums_2015_2022.csv,
         output/tables/fp_top10_final.csv
Outputs: data/raw/cbp/cbp_624410_YYYY.csv, output/tables/fp_e_missing_factors_top10.csv,
         output/tables/fp_e_sample_benchmarks.csv
"""
import os
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/cbp"
RAW.mkdir(parents=True, exist_ok=True)
def census_key():
    """Only needed if a CBP file has to be downloaded (the files used are included in data/raw/cbp/)."""
    keyfile = ROOT / "census_api_key.txt"
    key = os.environ.get("CENSUS_API_KEY") or (keyfile.read_text().strip() if keyfile.exists() else None)
    if not key:
        raise SystemExit("CBP file missing: set CENSUS_API_KEY or create census_api_key.txt to download it")
    return key


def cbp(year):
    path = RAW / f"cbp_624410_{year}.csv"
    if not path.exists():
        key = census_key()
        naics = "NAICS2017" if year >= 2017 else "NAICS2012"
        r = requests.get(f"https://api.census.gov/data/{year}/cbp",
                         params={"get": f"ESTAB,EMP,{naics}", "for": "county:*", "in": "state:*", naics: "624410",
                                 "key": key}, timeout=120)
        r.raise_for_status()
        js = r.json()
        pd.DataFrame(js[1:], columns=js[0]).to_csv(path, index=False)
    df = pd.read_csv(path, dtype=str)
    df["fips"] = df.state.str.zfill(2) + df.county.str.zfill(3)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.assign(estab=pd.to_numeric(df.ESTAB), emp=pd.to_numeric(df.EMP))[["fips", "estab", "emp"]]


c16, c19, c22 = cbp(2016), cbp(2019), cbp(2022)
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str})
top10 = pd.read_csv(ROOT / "output/tables/fp_top10_final.csv", dtype={"fips": str})
d = p[p.year == 2022].copy()
d = d.merge(c22.rename(columns={"estab": "estab_2022", "emp": "emp_2022"}), on="fips", how="left")
d = d.merge(c19.rename(columns={"estab": "estab_2019", "emp": "emp_2019"}), on="fips", how="left")
d = d.merge(c16.rename(columns={"estab": "estab_2016", "emp": "emp_2016"}), on="fips", how="left")
d["centers_per_1000_kids"] = d.estab_2022 / d.kids_under6_allpar_lf * 1000
d["center_jobs_per_100_kids"] = d.emp_2022 / d.kids_under6_allpar_lf * 100
d["centers_change_2019_2022_pct"] = (d.estab_2022 / d.estab_2019 - 1) * 100
w = lambda col, y: p[p.year == y].set_index("fips")[col]
d["kids_change_2015_2022_pct"] = (d.kids_under6 / d.fips.map(w("kids_under6", 2015)) - 1) * 100
d["wage_change_2019_2022_pct"] = (d.childcare_wage_real2022 / d.fips.map(w("childcare_wage_real2022", 2019)) - 1) * 100
d["rent_change_2015_2022_pct"] = (d.median_gross_rent_real2022 / d.fips.map(w("median_gross_rent_real2022", 2015)) - 1) * 100

IND = ["centers_per_1000_kids", "center_jobs_per_100_kids", "centers_change_2019_2022_pct", "kids_change_2015_2022_pct",
       "wage_change_2019_2022_pct", "rent_change_2015_2022_pct"]
for c in IND:
    d[f"pct_{c}"] = d[c].rank(pct=True)
bench = d[IND].describe(percentiles=[.25, .5, .75]).T[["count", "25%", "50%", "75%"]]
bench.to_csv(ROOT / "output/tables/fp_e_sample_benchmarks.csv")
t = d[d.fips.isin(top10.fips)].set_index("fips").loc[top10.fips].reset_index()
cols = ["fips", "county_name", "state_abbr", "estab_2022", "emp_2022", "kids_under6_allpar_lf"] + IND + [f"pct_{c}" for c in IND]
t[cols].to_csv(ROOT / "output/tables/fp_e_missing_factors_top10.csv", index=False)

pd.set_option("display.width", 260, "display.float_format", lambda v: f"{v:,.2f}")
print("CBP coverage of 2022 analysis sample:", d.estab_2022.notna().sum(), "of", len(d))
print("\nSample benchmarks (2022 analysis dataset):\n", bench.to_string())
print("\nTop 10:\n", t[["county_name", "state_abbr", "estab_2022", "kids_under6_allpar_lf"] + IND].to_string(index=False))
print("\nTop 10 percentiles:\n", t[["county_name"] + [f"pct_{c}" for c in IND]].to_string(index=False))
print("\ncorr(premium avg, centers per 1000 kids):",
      round(d.prem_LLS_pct.corr(d.centers_per_1000_kids, method="spearman"), 3))
