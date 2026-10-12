"""Pull ACS 5-year county estimates (2015-2022) from the Census API for the project variables.

API key: put your free key (https://api.census.gov/data/key_signup.html) in the environment
variable CENSUS_API_KEY or in a file named `census_api_key.txt` in the project root
(that file is git-ignored so the key is not submitted).

Variables pulled (raw ACS codes; derived variables are constructed later in the analysis):
  B19301_001E  per-capita income
  B01001_001E  total population
  B23008_002E  own children under 6
  B23008_004E, _010E, _013E  under-6 living with parent(s), all resident parents in labor force
  B25064_001E  median gross rent
  B15002_019E  women 25+ (total);  B15002_032E.._035E  women 25+ with bachelor's or higher
  B23022_026E  women 16-64 (total); B23022_029E  women 16-64 who worked full-time year-round

Outputs:
  data/raw/acs/acs5_county_YYYY.csv          one file per vintage, as returned by the API
  data/raw/acs/acs5_variable_labels.csv      Census label of every variable in every year, so we
                                             can verify codes mean the same thing across vintages
  data/interim/acs5_county_2015_2022.csv     stacked, fips as 5-char string, sentinels -> NaN
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
YEARS = range(2015, 2023)
VARS = [
    "B19301_001E", "B01001_001E",
    "B23008_002E", "B23008_004E", "B23008_010E", "B23008_013E",
    "B25064_001E",
    "B15002_019E", "B15002_032E", "B15002_033E", "B15002_034E", "B15002_035E",
    "B23022_026E", "B23022_029E",
]


def api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY")
    keyfile = ROOT / "census_api_key.txt"
    if not key and keyfile.exists():
        key = keyfile.read_text().strip()
    if not key:
        raise SystemExit("No Census API key: set CENSUS_API_KEY or create census_api_key.txt")
    return key


key = api_key()
frames, labels = [], []
for year in YEARS:
    base = f"https://api.census.gov/data/{year}/acs/acs5"
    r = requests.get(base, params={"get": ",".join(["NAME"] + VARS), "for": "county:*",
                                   "in": "state:*", "key": key}, timeout=120)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df.to_csv(ROOT / f"data/raw/acs/acs5_county_{year}.csv", index=False)
    df["year"] = year
    frames.append(df)

    for v in VARS:
        meta = requests.get(f"{base}/variables/{v}.json", timeout=60).json()
        labels.append({"year": year, "variable": v, "concept": meta.get("concept"),
                       "label": meta.get("label")})
    print(f"{year}: {len(df)} counties")

acs = pd.concat(frames, ignore_index=True)
acs["fips"] = acs["state"].str.zfill(2) + acs["county"].str.zfill(3)
for v in VARS:
    acs[v] = pd.to_numeric(acs[v], errors="coerce")
    acs.loc[acs[v] < 0, v] = np.nan  # Census sentinels such as -666666666 = not available
acs = acs[["year", "fips", "NAME"] + VARS].rename(columns={"NAME": "county_name"})
acs.to_csv(ROOT / "data/interim/acs5_county_2015_2022.csv", index=False)

lab = pd.DataFrame(labels)
lab.to_csv(ROOT / "data/raw/acs/acs5_variable_labels.csv", index=False)
drift = lab.groupby("variable")["label"].nunique()
print("\nVariables whose label text changes across vintages (check these):")
print(drift[drift > 1] if (drift > 1).any() else "none")
