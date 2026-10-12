"""Download BLS OEWS metro/nonmetro area files (2015-2022) and extract SOC 39-9011 Childcare Workers.

Each oesmYYma.zip contains these workbooks:
  MSA_M20YY_dl.xlsx  - metropolitan areas. In 2015-2017 the eleven large MSAs that have
                       metropolitan divisions appear here ONLY as their divisions.
  aMSA_M20YY_dl.xlsx - 2015-2017 only: whole-MSA estimates for those eleven MSAs (per BLS
                       file_descriptions.xlsx). Needed because the crosswalk uses whole-MSA codes.
  BOS_M20YY_dl.xlsx  - nonmetropolitan ("balance of state") areas
We keep all of them so the full metro/nonmetro geography is available; the metro filter is applied
later. Division rows are kept but marked with is_division so they can be excluded.

Download: bls.gov blocks anonymous scripted requests (HTTP 403). BLS asks automated clients to put
contact info in the User-Agent. Either
  (a) set the environment variable BLS_CONTACT_EMAIL to YOUR OWN e-mail and run this script, or
  (b) download the zips manually in a browser into data/raw/oews/ and run this script (it skips
      the download for any zip already present).

Outputs:
  data/raw/oews/oesmYYma.zip                     (raw, untouched)
  data/interim/oews_childcare_workers_2015_2022.csv
      year, oews_area (7-char, zero-padded), area_title, area_type, tot_emp, a_mean, h_mean,
      plus the raw a_mean string so suppression codes stay visible.
"""
import io
import os
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/oews"
YEARS = range(2015, 2023)
SOC = "39-9011"


def download(year: int) -> Path:
    yy = f"{year % 100:02d}"
    path = RAW / f"oesm{yy}ma.zip"
    if path.exists():
        return path
    email = os.environ.get("BLS_CONTACT_EMAIL")
    if not email:
        raise SystemExit(
            f"{path.name} missing. Set BLS_CONTACT_EMAIL or download "
            f"https://www.bls.gov/oes/special-requests/{path.name} into {RAW}"
        )
    r = requests.get(
        f"https://www.bls.gov/oes/special-requests/{path.name}",
        headers={"User-Agent": f"MGT403 course project ({email})"},
        timeout=300,
    )
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def extract(year: int, zpath: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            base = Path(name).name.upper()
            if not base.endswith((".XLSX", ".XLS")):
                continue
            if base.startswith(("MSA", "AMSA")):
                area_type = "metro"
            elif base.startswith("BOS"):
                area_type = "nonmetro"
            else:
                continue  # skip field descriptions / other files
            df = pd.read_excel(io.BytesIO(z.read(name)), dtype=str)
            df.columns = df.columns.str.strip().str.lower()
            df = df.rename(columns={"area_name": "area_title"})  # 2015-2018 files use area_name
            df = df[df["occ_code"].str.strip() == SOC].copy()
            df["area_type"] = area_type
            df["source_file"] = Path(name).name
            frames.append(df)
    if not frames:
        raise RuntimeError(f"No MSA/BOS workbook found in {zpath.name}")
    out = pd.concat(frames, ignore_index=True)
    out["year"] = year
    return out


rows = []
for year in YEARS:
    zpath = download(year)
    df = extract(year, zpath)
    print(f"{year}: {len(df)} area rows for SOC {SOC} ({df.area_type.value_counts().to_dict()})")
    rows.append(df)

oews = pd.concat(rows, ignore_index=True)
oews = oews.rename(columns={"area": "oews_area"})
oews["oews_area"] = oews["oews_area"].str.strip().str.zfill(7)
oews["a_mean_raw"] = oews["a_mean"]
for col in ["tot_emp", "a_mean", "h_mean"]:
    # BLS codes: '*' / '**' = not released, '#' = above top-coding threshold
    oews[col] = pd.to_numeric(oews[col].str.replace(",", ""), errors="coerce")

oews["is_division"] = oews["area_title"].str.contains("Metropolitan Division", na=False)
assert not oews.duplicated(["year", "oews_area"]).any(), "duplicate area-year rows"

keep = ["year", "oews_area", "area_title", "area_type", "is_division", "occ_code", "occ_title",
        "tot_emp", "a_mean", "h_mean", "a_mean_raw", "source_file"]
oews = oews[keep].sort_values(["year", "oews_area"])
out = ROOT / "data/interim/oews_childcare_workers_2015_2022.csv"
oews.to_csv(out, index=False)
print(f"\nSaved {len(oews)} rows -> {out.relative_to(ROOT)}")
print("Missing a_mean by year:\n", oews.groupby("year")["a_mean"].apply(lambda s: s.isna().sum()))
