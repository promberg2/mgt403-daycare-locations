"""Extract the NDCP childcare price series we need (2015-2022) into a tidy county x year file.

Input:  data/raw/ndcp/NDCP2022.xlsx  (manual download from DOL; 2008-2022, ~370 columns)
Output: data/interim/ndcp_prices_2015_2022.csv

Columns kept (weekly prices, nominal dollars):
  MC*    median price, center-based care      (MCINFANT, MCTODDLER, MCPRESCHOOL)
  _75C*  75th percentile, center-based care
  MFCC*  median price, family childcare (home-based)
  _75FCC* 75th percentile, family childcare
  *_flag the NDCP flag for each aggregate price (meaning: see Technical Report, Appendix C)
  *_flag the NDCP aggregation flag for each aggregate price: how the age-group price was built from
         the fine age bands (1 = all bands equal, 2 = mode, 3 = highest of several modes).
         NOT an imputation flag (Technical Report, Appendix C).
  MC*_imp  imputation code for the center-based median price of each age group, built from the
         five-digit imputation flags of its fine age bands (a digit is 1 if ANY band had that
         imputation). Digits (Technical Report pp. 9-26):
           1 imputed from a different age group   2 converted to weekly price
           3 county modeled from statewide data   4 median derived from 75th pctile (lognormal)
           5 interpolated between survey years
  MC*_imputed  True if any digit of MC*_imp is 1.
County FIPS is stored as a number in the workbook, so it is zero-padded back to 5 characters.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START, END = 2015, 2022

ages = ["INFANT", "TODDLER", "PRESCHOOL"]
prices, flags = [], []
for prefix in ["MC", "_75C", "MFCC", "_75FCC"]:
    for age in ages:
        prices.append(f"{prefix}{age}")
        flags.append(f"{prefix}{age.capitalize()}_flag")
ids = ["STATE_NAME", "STATE_ABBREVIATION", "COUNTY_NAME", "COUNTY_FIPS_CODE", "STUDYYEAR"]
# fine age bands (months) that make up each aggregate center-based age group
bands = {"INFANT": ["Bto5", "6to11", "12to17", "18to23"],
         "TODDLER": ["24to29", "30to35"],
         "PRESCHOOL": ["36to41", "42to47", "48to53"]}
icols = [f"iMC{b}" for bl in bands.values() for b in bl]

nd = pd.read_excel(ROOT / "data/raw/ndcp/NDCP2022.xlsx", usecols=ids + prices + flags + icols,
                   dtype={c: str for c in flags + icols + ["COUNTY_FIPS_CODE"]})
nd = nd[nd["STUDYYEAR"].between(START, END)].copy()


def combine_codes(frame: pd.DataFrame) -> pd.Series:
    """Digit-wise OR of five-digit imputation codes across the fine age bands."""
    def one(row):
        codes = [c for c in row if isinstance(c, str) and len(c) == 5]
        if not codes:
            return pd.NA
        return "".join("1" if any(c[k] == "1" for c in codes) else "0" for k in range(5))
    return frame.apply(one, axis=1)


imp = []
for age, bl in bands.items():
    col = f"MC{age}_imp"
    nd[col] = combine_codes(nd[[f"iMC{b}" for b in bl]])
    nd[f"MC{age}_imputed"] = nd[col].str.contains("1").astype("boolean")
    imp += [col, f"MC{age}_imputed"]
nd["fips"] = nd["COUNTY_FIPS_CODE"].str.strip().str.split(".").str[0].str.zfill(5)
nd = nd.rename(columns={"STUDYYEAR": "year", "STATE_ABBREVIATION": "state_abbr",
                        "STATE_NAME": "state_name", "COUNTY_NAME": "county_name"})
nd = nd[["year", "fips", "state_abbr", "state_name", "county_name"] + prices + flags + imp]
assert not nd.duplicated(["year", "fips"]).any(), "duplicate county-year rows"
assert (nd["fips"].str.len() == 5).all()

out = ROOT / "data/interim/ndcp_prices_2015_2022.csv"
nd.sort_values(["year", "fips"]).to_csv(out, index=False)
print(f"Saved {len(nd)} county-year rows -> {out.relative_to(ROOT)}")
print(nd.groupby("year")[["MCINFANT", "MCTODDLER", "MCPRESCHOOL"]].count())
