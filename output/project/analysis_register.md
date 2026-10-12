# Analysis register: samples, variables, methods

Every result in the slides and appendix can be traced to one row here. All N are computed from the data files.
Dollar values: constant 2022 dollars (CPI-U, CUUR0000SA0, annual average). Unit of observation: metro county (unweighted unless stated). Codes (FIPS, OEWS area) handled as zero-padded text.

### S0. Metro analysis sample
- **Sample:** Counties whose year-specific OEWS area code (course crosswalk) starts with 00, 2015–2022
- **N:** 9,873 county-years (1,236 counties)
- **Variables:** County FIPS, year, OEWS area, metro title
- **Method:** Crosswalk join on [year, FIPS]; legacy FIPS 12025 and 51515 dropped
- **Output:** `data/analysis/project_panel_2015_2022.csv`

### S1. Analysis dataset
- **Sample:** S0 with price and all 10 predictors non-missing
- **N:** 8,146 county-years; per year 2015: 994, 2016: 1,019, 2017: 1,057, 2018: 1,062, 2019: 1,061, 2020: 1,050, 2021: 905, 2022: 998
- **Variables:** NDCP median weekly full-time price, center-based preschool (MCPRESCHOOL), 2022 $; OEWS mean annual wage, childcare workers (SOC 39-9011), metro area → county; ACS median gross rent (B25064_001E); 2022 $; ACS demand variables
- **Method:** Complete cases (pre-analysis task 1)
- **Output:** `data/analysis/analysis_dataset_2015_2022.csv`

### P1. Pre-analysis descriptives and regressions (a)/(b)/(c)
- **Sample:** S1, 2022
- **N:** 998 counties, 330 metro areas
- **Variables:** NDCP median weekly full-time price, center-based preschool (MCPRESCHOOL), 2022 $; wage per $1,000; rent per $100
- **Method:** OLS; SEs clustered by metro area
- **Output:** `output/tables/pre_t2_*, pre_t3_*, pre_t4_*`

### F1. Cost model and premium (main)
- **Sample:** S1, each year 2015–2022 separately
- **N:** 8,146 county-year premiums
- **Variables:** log price; log wage; log rent; state fixed effects
- **Method:** OLS per year; premium = exp(residual) − 1 (within-state %); national premium = same model without state effects
- **Output:** `data/analysis/fp_premiums_2015_2022.csv`

### F2. Historical validation of the cost model
- **Sample:** S1: train 2015–2020 → test 2022; and 2022 10-fold CV grouped by metro area
- **N:** Test: 997 counties (temporal), 992 (CV)
- **Variables:** as F1; plus level and no-state-effect variants
- **Method:** Out-of-sample RMSE / MAE ($/week)
- **Output:** `output/tables/fp_model_validation.csv`

### F3. Candidate pool
- **Sample:** S1 counties observed ≥ 5 years (n = 1,059) with average national premium > 0
- **N:** Top 20 by average within-state premium 2015–2022
- **Variables:** average premium (F1)
- **Method:** Ranking
- **Output:** `output/tables/fp_candidates_scored.csv`

### F4. Filters and score → top 10
- **Sample:** Candidate pool (20)
- **N:** 10 pass both filters → top 10
- **Variables:** persistence (premium > 0 every year); market size (children needing care ≥ 2022 median 4,286); ACS: children under 6 with all resident parents in the labor force (B23008_004E+010E+013E); its share of total population; per-capita income (B19301_001E, 2022 $)
- **Method:** Score = 0.5 × premium percentile + 0.5 × demand percentile (within candidates)
- **Output:** `output/tables/fp_top10_final.csv`

### F5. Robustness of the selection
- **Sample:** Full rule rerun per variant
- **N:** 10 variants (8 plausible)
- **Variables:** as F3–F4 with one change each
- **Method:** Overlap with top 10
- **Output:** `output/tables/fp_robustness.csv, fp_robustness_counts.csv`

### F6. Statistical checks
- **Sample:** 2022 (S1) and average premiums (S1, ≥ 5 years)
- **N:** 2022: 998 counties; averages: 1,059 counties
- **Variables:** studentized residuals, 95% prediction interval, Breusch–Pagan, percentile of average premium
- **Method:** OLS diagnostics
- **Output:** `output/tables/fp_checks_*.csv`

### F7. Backtest of the full rule
- **Sample:** Rule applied with data 2015–2018 only; outcome = 2022 premium
- **N:** 10 selected (8 observed in 2022) vs. all other 2022 counties
- **Variables:** as F3–F4
- **Method:** Comparison of 2022 premiums
- **Output:** `output/tables/fp_checks_D_backtest_full_rule.csv`

### F8. (d) Stability over time
- **Sample:** S1; balanced panel = counties in all 8 years (n = 712); survey-only pairs
- **N:** balanced 712; survey pairs 1,038 counties in 46 states
- **Variables:** within-state premium (F1); NDCP imputation code (5th digit = 0 → direct survey price)
- **Method:** correlations, persistence regressions (state-clustered SE), quintile transitions
- **Output:** `output/tables/fp_d_*.csv`

### F9. Improvements / robustness
- **Sample:** S1 (teacher wage: 94–98% coverage per year)
- **N:** see output tables
- **Variables:** preschool-teacher wage (OEWS SOC 25-2011); WLS weights = children under 6; DC grouped with MD/VA
- **Method:** rerun of F1–F4
- **Output:** `output/tables/fp_imp_*.csv`

### F10. (e) Missing factors
- **Sample:** 2022 S1 counties with CBP data
- **N:** 882 counties (CBP coverage)
- **Variables:** Census County Business Patterns NAICS 624410 establishments/employees 2016/2019/2022; ACS children under 6 change; real wage and rent change
- **Method:** Percentiles vs. sample
- **Output:** `output/tables/fp_e_*.csv`
