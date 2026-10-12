"""PS5 task 4: descriptive table (mean / SD / N) of each predictor, metro counties, 2022.

Unit of observation: metro county (unweighted), 2022. 2022 dollar values are nominal 2022 = constant
2022 dollars. N differs by variable because of missing values (BLS wage suppression; 7 Connecticut
counties without 2022 ACS data; rent missing for one small county). Min and max are added for context.

Input:  data/analysis/county_costs_metro_2015_2022.csv
Output: output/tables/ps5_q4_descriptives_2022.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data/analysis/county_costs_metro_2015_2022.csv", dtype={"fips": str})
d22 = d[d["year"] == 2022]

VARS = [  # (column, label, source)
    ("childcare_wage", "Childcare-worker mean annual wage ($)", "OEWS, SOC 39-9011 (metro area)"),
    ("median_gross_rent", "Median gross rent ($/month)", "ACS B25064_001E"),
    ("per_capita_income", "Per-capita income ($/year)", "ACS B19301_001E"),
    ("pop_total", "Total population", "ACS B01001_001E"),
    ("kids_under6", "Own children under 6", "ACS B23008_002E"),
    ("kids_under6_allpar_lf", "Under 6, all resident parents in labor force", "ACS B23008_004E+010E+013E"),
    ("female_college_share", "Share of women 25+ with bachelor's or higher", "ACS B15002"),
    ("female_ftyr_share", "Share of women 16-64 full-time year-round", "ACS B23022"),
    ("under6_share", "Share of population under 6", "kids_under6 / pop_total"),
    ("under6_careneed_share", "Share of population under 6 needing care", "kids_under6_allpar_lf / pop_total"),
]
rows = []
for col, lab, src in VARS:
    x = d22[col].dropna()
    rows.append({"variable": col, "label": lab, "source": src, "mean": x.mean(), "sd": x.std(ddof=1),
                 "n": len(x), "min": x.min(), "max": x.max()})
tab = pd.DataFrame(rows)
tab.to_csv(ROOT / "output/tables/ps5_q4_descriptives_2022.csv", index=False)

print(f"Metro counties in 2022: {len(d22)}; metro areas: {d22['oews_area'].nunique()}")
print(f"Distinct wage values across counties: {d22['childcare_wage'].nunique()} "
      f"(wages are measured per metro area, so counties in the same metro share one value)")
pd.set_option("display.width", 220, "display.float_format", lambda v: f"{v:,.4f}")
print(tab[["label", "mean", "sd", "n", "min", "max"]].to_string(index=False))
