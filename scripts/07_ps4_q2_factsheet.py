"""PS4 Q2 supplementary descriptives for the written discussion (2022, metro sample).

Outputs: output/tables/ps4_q2_percentiles_2022.csv
         output/tables/ps4_q2_extremes_2022.csv      5 most / least expensive counties per age group
         output/tables/ps4_q2_state_clustering_2022.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AGES = {"MCINFANT": "infant", "MCTODDLER": "toddler", "MCPRESCHOOL": "preschool"}
df = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d = df[df["year"] == 2022]

q = [0.10, 0.25, 0.50, 0.75, 0.90]
pct = pd.DataFrame({lab: d[c].quantile(q) for c, lab in AGES.items()}).T
pct.columns = [f"p{int(x * 100)}" for x in q]
pct["p90_p10_ratio"] = pct["p90"] / pct["p10"]
pct["iqr"] = pct["p75"] - pct["p25"]
pct["cv"] = [d[c].std() / d[c].mean() for c in AGES]
pct["skew"] = [d[c].skew() for c in AGES]
pct.round(3).to_csv(ROOT / "output/tables/ps4_q2_percentiles_2022.csv")

ext = []
for c, lab in AGES.items():
    s = d.dropna(subset=[c]).sort_values(c)
    for tag, part in [("lowest", s.head(5)), ("highest", s.tail(5).iloc[::-1])]:
        for _, r in part.iterrows():
            ext.append({"age_group": lab, "rank": tag, "county": r["county_name"], "state": r["state_abbr"],
                        "metro_area": r["area_title"], "price": r[c]})
pd.DataFrame(ext).to_csv(ROOT / "output/tables/ps4_q2_extremes_2022.csv", index=False)

x = d.dropna(subset=["MCPRESCHOOL"])
st = x.groupby("state_abbr")["MCPRESCHOOL"].agg(counties="size", distinct_prices="nunique",
                                                 mean="mean", min="min", max="max")
st = st.sort_values("counties", ascending=False)
st.round(2).to_csv(ROOT / "output/tables/ps4_q2_state_clustering_2022.csv")
between = x.groupby("state_abbr")["MCPRESCHOOL"].transform("mean")
share_between = between.var() / x["MCPRESCHOOL"].var()

pd.set_option("display.width", 200)
print(pct.round(2).to_string())
print(pd.DataFrame(ext).to_string(index=False))
print(f"\nPreschool: {len(x)} counties, {x['MCPRESCHOOL'].nunique()} distinct prices, {x.state_abbr.nunique()} states")
print(f"Share of preschool price variance that is between states: {share_between:.1%}")
print("Highest / lowest state means:\n", st.sort_values("mean").iloc[[0, 1, 2, -3, -2, -1]].round(2).to_string())

# Sign of within-county differences (younger minus older age group)
print("\nWithin-county comparisons (counts):")
for a, b in [("MCINFANT", "MCTODDLER"), ("MCTODDLER", "MCPRESCHOOL"), ("MCINFANT", "MCPRESCHOOL")]:
    p = d[[a, b, "state_abbr"]].dropna()
    lower = p[p[a] < p[b]]
    print(f"  {a} vs {b}: higher {(p[a] > p[b]).sum()}, equal {(p[a] == p[b]).sum()}, lower {len(lower)}"
          + (f"; lower by state {lower.state_abbr.value_counts().to_dict()}, "
             f"median gap ${(lower[b] - lower[a]).median():.2f}, max ${(lower[b] - lower[a]).max():.2f}"
             if a == "MCINFANT" and b == "MCPRESCHOOL" else ""))
print("\nMonthly equivalents (mean x 4.33):", {lab: round(d[c].mean() * 4.33, 2) for c, lab in AGES.items()})
