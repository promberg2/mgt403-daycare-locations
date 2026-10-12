# Deck number check

Every number stated in the slide text was recomputed from the result tables or the analysis data and searched for in the built deck. Script: `scripts/35_fp_check_deck_numbers.py`.

**Result: 83 of 83 claims PASS, 0 FAIL.**

| Slide | Claim | Text expected in the deck | Source | Result |
|---|---|---|---|---|
| 1 | Expected premium range of the top 10 | `18–37%` | fp_imp_expected_premium.csv: min/max expected_premium_pct | PASS |
| 1 | Advantage lasted since 2015: all ten observed in 2015 and positive in every observed year | `since 2015` | fp_premiums_2015_2022.csv | PASS |
| 1 | Sample: metro counties in 2022 | `998 metro counties` | analysis_dataset_2015_2022.csv, year 2022 | PASS |
| 1 | Northern Virginia counties (ranks) form one market | `1, 2, 4 and 6 form one market: Northern Virginia` | fp_top10_final.csv | PASS |
| 2 | R² model “c” → final (2022) | `from 61% to 81%` | pre_t4_regressions.csv; OLS log model 2022 | PASS |
| 2 | Model “c” intercept | `−88` | pre_t4_regressions.csv | PASS |
| 2 | Model “c” wage coefficient (per $1,000) and metro-clustered SE | `7.09 (0.58)` | pre_t4_regressions.csv | PASS |
| 2 | Model “c” rent coefficient (per $100) and SE | `5.91 (0.92)` | pre_t4_regressions.csv | PASS |
| 2 | Final wage elasticity and SE | `0.37 (0.09)` | OLS log model 2022, metro-clustered | PASS |
| 2 | Final rent elasticity and SE | `0.53 (0.04)` | OLS log model 2022, metro-clustered | PASS |
| 2 | +10% wage → price (exact, 1.1^b − 1) | `+3.6%` | elasticity | PASS |
| 2 | +10% rent → price (exact, 1.1^b − 1) | `+5.2%` | elasticity | PASS |
| 2 | Number of state dummies (states/DC − 1) | `yes (43)` | analysis_dataset 2022 | PASS |
| 2 | States/DC in 2022 sample | `44 states/DC` | analysis_dataset 2022 | PASS |
| 2 | Hall 2022 price | `$179/week` | analysis_dataset 2022 | PASS |
| 2 | Hall model “c” prediction | `$167` | model “c” coefficients | PASS |
| 2 | Hall model “c” gap | `+7%` | price / prediction − 1 | PASS |
| 2 | Hall within-Georgia prediction | `$138` | exp(fitted) of log model | PASS |
| 2 | Hall within-state premium | `+30% premium` | price / prediction − 1 | PASS |
| 3 | Metro counties with price, wage and rent data (2015–2022) | `1,159` | fp_premiums: unique counties | PASS |
| 3 | In the 2022 sample and observed ≥ 5 of 8 years | `972 in the 2022 data` | fp_premiums + analysis_dataset 2022 | PASS |
| 3 | … and positive average national premium | `460` | fp_premiums | PASS |
| 3 | Candidate pool positive in every year | `10` | fp_candidates_scored | PASS |
| 3 | Market-size threshold (2022 median, children needing care) | `≥ 4,286` | analysis_dataset 2022 | PASS |
| 4 | Backtest: picks with data to 2018 in the 2022 sample | `8 of 10` | fp_checks_D_backtest_full_rule.csv | PASS |
| 4 | Backtest: 2018 picks that are in today's top 10 | `already picked 7 of today’s ten` | fp_checks_D_backtest_full_rule.csv | PASS |
| 4 | Backtest uses 2015-2018 only | `2015–2018 data only` | rule | PASS |
| 4 | Lowest average premium in direct survey years | `≥ +27%` | fp_premiums: survey years | PASS |
| 4 | Out-of-sample error vs. model c | `−14%` | fp_model_validation.csv | PASS |
| 4 | Teacher wage replaces ours | `(8/10 if the teacher wage replaces ours)` | fp_imp_wage_weight_robustness.csv | PASS |
| 4 | Same list with both wages | `10/10` | fp_imp_wage_weight_robustness.csv | PASS |
| 4 | WLS (weighted by children) keeps | `keeps 6 of 10` | fp_imp_wage_weight_robustness.csv | PASS |
| 4 | Counties selected in all counted designs | `7 of 10 selected in all 5` | fp_robustness_counts.csv | PASS |
| 4 | Portfolio view: counties replaced | `the other 8 stay` | fp_metro_cap_variant.csv | PASS |
| 5 | Expected premium range (slide 5 card) | `+18% to +37%` | fp_imp_expected_premium.csv | PASS |
| 5 | Survey-only persistence slope | `0.67` | fp_d_survey_only.csv | PASS |
| 5 | Share keeping the sign | `74%` | fp_d_survey_only.csv | PASS |
| 5 | 95% CI of the slope | `[0.57, 0.78]` | slope ± 1.96 SE | PASS |
| 5 | Correlation of survey premiums | `correlation 0.67` | fp_d_survey_only.csv | PASS |
| 5 | Gap between survey prices (years) | `≈ 4.7 years` | fp_d_survey_only.csv | PASS |
| 5 | Counties / states in the survey test | `1,038 counties, 46 states` | fp_d_survey_only.csv | PASS |
| 5 | Title: about two thirds remain | `two thirds` | slope 0.67 | PASS |
| 5 | Top fifth 2015 → still top fifth / still positive in 2022 | `2015 | 56% | 82%` | fp_d_quintile_transitions.csv | PASS |
| 5 | Top fifth 2018 → still top fifth / still positive in 2022 | `2018 | 63% | 89%` | fp_d_quintile_transitions.csv | PASS |
| 5 | Top fifth 2019 → still top fifth / still positive in 2022 | `2019 | 73% | 97%` | fp_d_quintile_transitions.csv | PASS |
| 5 | Expected premium range | `+18% to +37%` | fp_imp_expected_premium.csv | PASS |
| 6 | Competition thresholds (p75 / p25) | `above 6.24 (crowded) or below 3.86` | fp_e_sample_benchmarks.csv | PASS |
| 6 | Child-trend median | `(-4.4%)` | fp_e_sample_benchmarks.csv | PASS |
| 6 | Wage-growth p75 | `(above +6.1%)` | fp_e_sample_benchmarks.csv | PASS |
| 6 | Rent-growth p75 | `(above +12.0%)` | fp_e_sample_benchmarks.csv | PASS |
| 6 | Benchmark counties | `(882–974 counties)` | fp_e_sample_benchmarks.csv | PASS |
| 6 | Risk row Arlington | `5.44` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Arlington: child trend | `-3.3%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Alexandria | `5.67` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Alexandria: child trend | `-5.9%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row San Francisco | `14.22` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row San Francisco: child trend | `-5.5%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Loudoun | `6.54` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Loudoun: child trend | `+0.8%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Olmsted | `5.24` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Olmsted: child trend | `-5.7%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Fairfax | `6.22` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Fairfax: child trend | `-9.5%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Multnomah | `12.16` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Multnomah: child trend | `-15.8%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Howard | `7.00` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Howard: child trend | `+0.5%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Hall | `2.60` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Hall: child trend | `-5.1%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Risk row Sullivan | `3.03` | fp_e_missing_factors_top10.csv: centers per 1,000 | PASS |
| 6 | Risk row Sullivan: child trend | `-6.4%` | fp_e_missing_factors_top10.csv | PASS |
| 6 | Public pre-K label Arlington County | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Alexandria City | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Loudoun County | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Fairfax County | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label San Francisco County | `universal (TK + city)` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Olmsted County | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Multnomah County | `Preschool for All` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Howard County | `income-tiered only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Hall County | `universal (state)` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 6 | Public pre-K label Sullivan County | `targeted only` | data/manual/public_prek_programs.csv (sourced) | PASS |
| 1 | Title: expected (faded) premium, not the historical average | `expected to pay` | fp_imp_expected_premium.csv | PASS |
| 6 | Premium range of the four DC suburbs | `+30% to +61%` | fp_top10_final.csv | PASS |

## Figure values (recomputed for review)

| Rank | County | Average premium 2015–2022 | Expected premium [95% CI] | Weakest year |
|---|---|---|---|---|
| 1 | Arlington County, VA | +61% (table: +60%) | +37% [31, 44] | +47% |
| 2 | Alexandria City, VA | +50% (table: +49%) | +31% [26, 37] | +35% |
| 3 | San Francisco County, CA | +36% (table: +35%) | +23% [19, 27] | +21% |
| 4 | Loudoun County, VA | +35% (table: +35%) | +22% [19, 26] | +31% |
| 5 | Olmsted County, MN | +33% (table: +33%) | +21% [18, 25] | +32% |
| 6 | Fairfax County, VA | +30% (table: +30%) | +19% [16, 23] | +26% |
| 7 | Multnomah County, OR | +32% (table: +32%) | +20% [17, 24] | +22% |
| 8 | Howard County, MD | +32% (table: +31%) | +20% [17, 24] | +25% |
| 9 | Hall County, GA | +33% (table: +33%) | +21% [18, 25] | +28% |
| 10 | Sullivan County, TN | +28% (table: +28%) | +18% [15, 21] | +24% |
