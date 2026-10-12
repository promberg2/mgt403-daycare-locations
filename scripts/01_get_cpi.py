"""Download CPI-U (BLS series CUUR0000SA0) and build annual averages + 2022-dollar deflators.

Source: BLS Public Data API v1 (no key needed), monthly not-seasonally-adjusted values.
Annual average = mean of the 12 monthly values (this is how BLS defines the annual average).

Outputs:
  data/raw/cpi/cpi_u_monthly_2015_2022.csv
  data/interim/cpi_u_annual.csv   (year, cpi_u, to_2022_dollars)
Multiply a nominal dollar value from year t by `to_2022_dollars` to express it in 2022 dollars.
"""
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SERIES = "CUUR0000SA0"
START, END = 2015, 2022

resp = requests.post(
    "https://api.bls.gov/publicAPI/v1/timeseries/data/",
    json={"seriesid": [SERIES], "startyear": str(START), "endyear": str(END)},
    timeout=60,
)
resp.raise_for_status()
payload = resp.json()
if payload["status"] != "REQUEST_SUCCEEDED":
    raise RuntimeError(payload["message"])

monthly = pd.DataFrame(payload["Results"]["series"][0]["data"])
monthly = monthly[monthly["period"].str.match(r"M(0[1-9]|1[0-2])")]  # drop M13 if present
monthly = monthly.assign(year=monthly["year"].astype(int), value=monthly["value"].astype(float))
monthly = monthly[["year", "period", "value"]].sort_values(["year", "period"])
monthly.to_csv(ROOT / "data/raw/cpi/cpi_u_monthly_2015_2022.csv", index=False)

counts = monthly.groupby("year").size()
assert (counts == 12).all(), f"Incomplete months: {counts.to_dict()}"

annual = monthly.groupby("year", as_index=False)["value"].mean().rename(columns={"value": "cpi_u"})
annual["cpi_u"] = annual["cpi_u"].round(3)
annual["to_2022_dollars"] = annual.loc[annual.year == 2022, "cpi_u"].item() / annual["cpi_u"]
annual.to_csv(ROOT / "data/interim/cpi_u_annual.csv", index=False)
print(annual.to_string(index=False))
