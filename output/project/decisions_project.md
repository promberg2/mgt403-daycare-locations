# Methodological decisions: final project

Each decision was taken by the team after the AI laid out the options and evidence (see prompt log). For the appendix document.

## D1. Premium measure: within-state premium (main), national premium (robustness)
- **Decision:** the premium is the percentage by which a county's price exceeds the price predicted from its childcare-worker wage and rent, estimated with log(price) on log(wage) and log(rent) plus state fixed effects, year by year. The county's average national premium (same model without state effects) must also be positive.
- **Why:**
  - The state-effects model predicts prices best on historical data. Out-of-sample error is $33.67/week when fitted on 2015–2020 and used to predict 2022, vs. $39 without state effects. In 2022 cross-validation grouped by metro area it is $30.38 vs. $37.
  - NDCP prices are largely set by state rate zones. For example, 24 Wisconsin counties have only 4 distinct prices. States also differ in unobserved cost drivers such as staff-to-child ratio rules.
  - A national premium would mostly select states rather than markets.

## D2. Selection based on the premium averaged over 2015–2022 (not 2022 alone)
- **Decision:** the candidate pool is the 20 counties with the highest *average* within-state premium over all observed years 2015–2022 (at least 5 years observed), not the highest premium in 2022 alone.
- **Why:**
  1. **Our goal is a lasting advantage.** A multi-year average measures exactly that; a single year can be a spike.
  2. **The 2022 prices for California and Virginia are not survey data.** NDCP has no 2022 market-rate survey for these states and extrapolates prices with a matching model. This produces implausible one-year jumps. From 2020 to 2022, nominal prices rose 25% in San Francisco, 28% in San Mateo and 37% in Marin, but fell 15% in Los Angeles; Arlington VA rose 21% while neighbouring Fairfax County fell 7%. Ranking on 2022 alone selected counties (San Mateo, Marin) whose premium was about 10% in every year before 2022.
  3. **The result is robust.** The average-based top 10 is nearly identical to a selection that ignores the 2022 values entirely (average 2015–2020: 9 of 10 the same) and to a pre-COVID selection (average 2015–2019: 9 of 10). Seven of the ten counties are selected in all 8 plausible robustness variants.
- **Effect:** six counties are selected under both designs (Arlington, Alexandria, San Francisco, Loudoun, Olmsted, Howard). Fairfax County VA, Multnomah OR, Hall GA and Sullivan TN replace Alameda, San Mateo, Marin and McLean.

## D3. Persistence filter
- **Decision:** the within-state premium must be positive in every observed year.
- **Why:** the advantage must have lasted. Persistence is real but partial: in survey-only data, the correlation of premiums about 4.7 years apart is 0.67.

## D4. Market-size filter
- **Decision:** at least the median number of children under 6 with all resident parents in the labor force (4,286 in 2022).
- **Why:** a high premium in a very small market cannot support a center. This excludes, for example, Manassas Park City VA (816) and Falls Church City VA (578).

## D5. Ranking score
- **Decision:** 50% premium strength (average premium) + 50% demand index (children needing care, their share of the population, per-capita income). Both are percentile ranks among the remaining candidates, so the weights are effective weights.
- **Why:** this prioritizes markets with strong childcare demand among the counties with a lasting premium. The ranking is insensitive to the weights: 70/30 and 30/70 give the same top 10.

## D6. No cap per metro area
- **Decision:** several counties of the same metro area may be selected, e.g. Washington DC area: Arlington, Alexandria, Loudoun, Fairfax.
- **Why:** they are separate local markets, and we want the best counties.

## D7. Earlier design corrected (scaling)
- In an earlier version, premium strength was ranked among the candidates while demand was ranked against all counties. On those different scales, the 50/50 weighting was not effectively 50/50. Both components now use the same scale.

## D8. Robustness checks added after the analysis review
- **Wage measure:** center-based preschools employ preschool teachers (SOC 25-2011) as well as childcare workers (SOC 39-9011, the assignment's measure).
  - Re-estimating the premium with preschool-teacher wages keeps 8 of the top 10 (Hall GA and Sullivan TN are replaced by Ramsey MN and Clayton GA). Using both wages keeps all 10.
  - The childcare-worker wage is the stronger predictor: with both wages in the 2022 model, its elasticity is 0.33 vs. 0.06 for the teacher wage.
  - Fit is practically identical (R² 0.811 vs. 0.808).
- **Weighting by number of children (WLS):** keeps 6 of the top 10.
  - Weighting lets large counties dominate the cost line; it drops Loudoun, Fairfax, Multnomah and Olmsted and adds Erie NY, Onondaga NY, McLean IL and St. Johns FL.
  - We keep the unweighted model: every county is one market observation, and market size enters separately through the demand filter and score.
- **Expected premium:** premiums only partly persist. With direct survey prices, about 67% of a county's premium remains ~4.7 years later (slope 0.674, 95% CI 0.57–0.78).
  - Expected future premiums for the top 10 are therefore smaller than today's averages, e.g. Arlington +37% instead of +60%, Sullivan +18% instead of +28%.
  - All remain clearly positive. The ranking is unchanged, because the shrinkage is proportional.
- **Washington DC:** DC is not in the selection because NDCP reports a DC price only for 2022 (2015–2021 missing). It cannot meet the persistence requirement.
  - With state fixed effects DC would also have a premium of 0 by construction (single-county "state").
  - Grouping DC with MD and VA gives DC a 2022 premium of +71%: a promising market, but without price history. Mentioned as an additional candidate to investigate, not as a recommendation.
