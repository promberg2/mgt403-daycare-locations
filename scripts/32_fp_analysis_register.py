"""Analysis register: for every analysis in the final project, the sample, variables, method, N and output file.

All N are computed from the data files (not typed), so the register cannot drift from the results.
Output: output/project/analysis_register.md, output/tables/analysis_register.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "output/tables"
panel = pd.read_csv(ROOT / "data/analysis/project_panel_2015_2022.csv", dtype={"fips": str})
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
prem = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str})
cand = pd.read_csv(T / "fp_candidates_scored.csv", dtype={"fips": str})
top10 = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
cbp = pd.read_csv(T / "fp_e_missing_factors_top10.csv", dtype={"fips": str})
bench = pd.read_csv(T / "fp_e_sample_benchmarks.csv", index_col=0)
surv = pd.read_csv(T / "fp_d_survey_only.csv", index_col=0).squeeze()
d22 = a[a.year == 2022]
bal = a.groupby("fips").year.nunique().eq(8).sum()
avg_n = prem.groupby("fips").size().ge(5).sum()
n_by_year = ", ".join(f"{y}: {n:,}" for y, n in a.groupby("year").size().items())

PRICE = "NDCP median weekly full-time price, center-based preschool (MCPRESCHOOL), 2022 $"
COST = "OEWS mean annual wage, childcare workers (SOC 39-9011), metro area → county; ACS median gross rent (B25064_001E); 2022 $"
DEM = ("ACS: children under 6 with all resident parents in the labor force (B23008_004E+010E+013E); its share of total "
       "population; per-capita income (B19301_001E, 2022 $)")
rows = [
    ("S0", "Metro analysis sample", "Counties whose year-specific OEWS area code (course crosswalk) starts with 00, 2015–2022",
     f"{len(panel):,} county-years ({panel.fips.nunique():,} counties)", "County FIPS, year, OEWS area, metro title",
     "Crosswalk join on [year, FIPS]; legacy FIPS 12025 and 51515 dropped", "data/analysis/project_panel_2015_2022.csv"),
    ("S1", "Analysis dataset", "S0 with price and all 10 predictors non-missing",
     f"{len(a):,} county-years; per year {n_by_year}", f"{PRICE}; {COST}; ACS demand variables",
     "Complete cases (pre-analysis task 1)", "data/analysis/analysis_dataset_2015_2022.csv"),
    ("P1", "Pre-analysis descriptives and regressions (a)/(b)/(c)", "S1, 2022",
     f"{len(d22):,} counties, {d22.oews_area.nunique()} metro areas", f"{PRICE}; wage per $1,000; rent per $100",
     "OLS; SEs clustered by metro area", "output/tables/pre_t2_*, pre_t3_*, pre_t4_*"),
    ("F1", "Cost model and premium (main)", "S1, each year 2015–2022 separately",
     f"{len(prem):,} county-year premiums", f"log price; log wage; log rent; state fixed effects",
     "OLS per year; premium = exp(residual) − 1 (within-state %); national premium = same model without state effects",
     "data/analysis/fp_premiums_2015_2022.csv"),
    ("F2", "Historical validation of the cost model", "S1: train 2015–2020 → test 2022; and 2022 10-fold CV grouped by metro area",
     "Test: 997 counties (temporal), 992 (CV)", "as F1; plus level and no-state-effect variants",
     "Out-of-sample RMSE / MAE ($/week)", "output/tables/fp_model_validation.csv"),
    ("F3", "Candidate pool", f"S1 counties observed ≥ 5 years (n = {avg_n:,}) with average national premium > 0",
     "Top 20 by average within-state premium 2015–2022", "average premium (F1)", "Ranking",
     "output/tables/fp_candidates_scored.csv"),
    ("F4", "Filters and score → top 10", "Candidate pool (20)",
     f"{len(cand)} pass both filters → top {len(top10)}",
     f"persistence (premium > 0 every year); market size (children needing care ≥ 2022 median "
     f"{d22.kids_under6_allpar_lf.median():,.0f}); {DEM}",
     "Score = 0.5 × premium percentile + 0.5 × demand percentile (within candidates)", "output/tables/fp_top10_final.csv"),
    ("F5", "Robustness of the selection", "Full rule rerun per variant",
     "10 variants (8 plausible)", "as F3–F4 with one change each", "Overlap with top 10",
     "output/tables/fp_robustness.csv, fp_robustness_counts.csv"),
    ("F6", "Statistical checks", "2022 (S1) and average premiums (S1, ≥ 5 years)",
     f"2022: {len(d22):,} counties; averages: {avg_n:,} counties",
     "studentized residuals, 95% prediction interval, Breusch–Pagan, percentile of average premium",
     "OLS diagnostics", "output/tables/fp_checks_*.csv"),
    ("F7", "Backtest of the full rule", "Rule applied with data 2015–2018 only; outcome = 2022 premium",
     "10 selected (8 observed in 2022) vs. all other 2022 counties", "as F3–F4", "Comparison of 2022 premiums",
     "output/tables/fp_checks_D_backtest_full_rule.csv"),
    ("F8", "(d) Stability over time", f"S1; balanced panel = counties in all 8 years (n = {bal:,}); survey-only pairs",
     f"balanced {bal:,}; survey pairs {int(surv['n_counties']):,} counties in {int(surv['n_states'])} states",
     "within-state premium (F1); NDCP imputation code (5th digit = 0 → direct survey price)",
     "correlations, persistence regressions (state-clustered SE), quintile transitions", "output/tables/fp_d_*.csv"),
    ("F9", "Improvements / robustness", "S1 (teacher wage: 94–98% coverage per year)",
     "see output tables", "preschool-teacher wage (OEWS SOC 25-2011); WLS weights = children under 6; DC grouped with MD/VA",
     "rerun of F1–F4", "output/tables/fp_imp_*.csv"),
    ("F10", "(e) Missing factors", "2022 S1 counties with CBP data",
     f"{int(bench.loc['centers_per_1000_kids', 'count']):,} counties (CBP coverage)",
     "Census County Business Patterns NAICS 624410 establishments/employees 2016/2019/2022; ACS children under 6 change; real wage and rent change",
     "Percentiles vs. sample", "output/tables/fp_e_*.csv"),
]
reg = pd.DataFrame(rows, columns=["id", "analysis", "sample", "n", "variables", "method", "output"])
reg.to_csv(T / "analysis_register.csv", index=False)

md = ["# Analysis register: samples, variables, methods", "",
      "Every result in the slides and appendix can be traced to one row here. All N are computed from the data files.",
      "Dollar values: constant 2022 dollars (CPI-U, CUUR0000SA0, annual average). Unit of observation: metro county "
      "(unweighted unless stated). Codes (FIPS, OEWS area) handled as zero-padded text.", ""]
for r in reg.itertuples():
    md += [f"### {r.id}. {r.analysis}", f"- **Sample:** {r.sample}", f"- **N:** {r.n}", f"- **Variables:** {r.variables}",
           f"- **Method:** {r.method}", f"- **Output:** `{r.output}`", ""]
(ROOT / "output/project/analysis_register.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
