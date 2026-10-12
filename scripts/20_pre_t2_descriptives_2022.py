"""Pre-analysis task 2: mean / SD / N for all variables in the analysis dataset, 2022.

Analysis dataset = complete cases (price and all predictors non-missing), 2022: one row per metro county,
unweighted. Dollar values in 2022 dollars (= nominal 2022). Min / max added for context.
Infant and toddler prices are included for context; they are not part of the complete-case definition, so their
N can differ slightly.

Input:  data/analysis/analysis_dataset_2015_2022.csv
Output: output/tables/pre_t2_descriptives_2022.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d = a[a["year"] == 2022]

VARS = [
    ("Outcome: childcare price", "price_preschool_real2022", "Preschool price, center-based median ($/week)", "NDCP MCPRESCHOOL"),
    ("Outcome: childcare price", "price_infant_real2022", "Infant price, center-based median ($/week)", "NDCP MCINFANT"),
    ("Outcome: childcare price", "price_toddler_real2022", "Toddler price, center-based median ($/week)", "NDCP MCTODDLER"),
    ("Costs", "childcare_wage_real2022", "Childcare-worker mean annual wage ($)", "OEWS SOC 39-9011"),
    ("Costs", "median_gross_rent_real2022", "Median gross rent ($/month)", "ACS B25064_001E"),
    ("Demand", "per_capita_income_real2022", "Per-capita income ($/year)", "ACS B19301_001E"),
    ("Demand", "pop_total", "Total population", "ACS B01001_001E"),
    ("Demand", "kids_under6", "Own children under 6", "ACS B23008_002E"),
    ("Demand", "kids_under6_allpar_lf", "Under 6, all resident parents in labor force", "ACS B23008_004E+010E+013E"),
    ("Demand", "female_college_share", "Share of women 25+ with bachelor's or higher", "ACS B15002"),
    ("Demand", "female_ftyr_share", "Share of women 16-64 full-time year-round", "ACS B23022"),
    ("Demand", "under6_share", "Share of population under 6", "kids_under6 / pop_total"),
    ("Demand", "under6_careneed_share", "Share of population under 6 needing care", "kids_under6_allpar_lf / pop_total"),
]
rows = []
for grp, col, lab, src in VARS:
    x = d[col].dropna()
    rows.append({"group": grp, "variable": col, "label": lab, "source": src, "mean": x.mean(),
                 "sd": x.std(ddof=1), "n": len(x), "min": x.min(), "max": x.max()})
tab = pd.DataFrame(rows)
tab.to_csv(ROOT / "output/tables/pre_t2_descriptives_2022.csv", index=False)

print(f"2022 analysis dataset: {len(d)} counties, {d.oews_area.nunique()} metro areas, {d.state_abbr.nunique()} states/DC")
pd.set_option("display.width", 220, "display.float_format", lambda v: f"{v:,.4f}")
print(tab[["group", "label", "mean", "sd", "n", "min", "max"]].to_string(index=False))
print("\nMonthly preschool price (x 4.33): mean", round(d.price_preschool_real2022.mean() * 4.33, 2))
print("Imputed-price share (NDCP):", round(d.price_imputed.astype(str).eq("True").mean(), 3))
