# PS4 Q2: Fact sheet for the written discussion

All figures: 2022, metro analysis sample (counties with OEWS area code `00…`), NDCP median weekly full-time price
for **center-based** care, **nominal dollars**. Unit of observation: county (unweighted). This sheet lists
numbers only; the interpretation is written separately.

Figure: [`output/figures/ps4_q2_histograms_2022.png`](../figures/ps4_q2_histograms_2022.png)

## 1. Required statistics (mean / SD / N / 95% CI)

95% CI = mean ± t(0.975, N−1) × SD/√N, with t = 1.962.

| Age group | N | Mean | SD | SE | 95% CI for the mean |
|---|---:|---:|---:|---:|---|
| Infant (0–23 months) | 1,012 | $214.95 | $82.96 | $2.61 | [$209.84, $220.07] |
| Toddler (24–35 months) | 1,011 | $186.46 | $66.37 | $2.09 | [$182.36, $190.55] |
| Preschool (36–54 months) | 1,013 | $175.09 | $59.98 | $1.88 | [$171.39, $178.79] |

- None of the three CIs overlap.
- Monthly equivalent (mean × 4.33 weeks): infant $930.76, toddler $807.36, preschool $758.13.

## 2. Shape of the distributions

| Age group | Min | p10 | p25 | Median | p75 | p90 | Max | IQR | p90/p10 | CV (SD/mean) | Skewness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Infant | $95.60 | $130.99 | $151.30 | $198.93 | $254.45 | $325.00 | $606.61 | $103.15 | 2.48 | 0.39 | 1.26 |
| Toddler | $97.00 | $117.21 | $138.75 | $170.00 | $216.67 | $279.20 | $520.00 | $77.92 | 2.38 | 0.36 | 1.31 |
| Preschool | $86.19 | $114.00 | $130.08 | $162.50 | $200.00 | $258.75 | $496.30 | $69.92 | 2.27 | 0.34 | 1.43 |

- In every group the median is below the mean (a positive skew means a long right tail).
- A county at the 90th percentile pays 2.3–2.5 times as much as one at the 10th.
- Histogram features: the infant histogram has a second peak at $280–300 (79 counties). It comes from shared
  state prices: 22 Ohio counties are at exactly $295.00, and the rest are mostly in NY, WI, NJ and IL.

## 3. Differences between age groups within the same county (paired)

| Comparison | N | Mean difference | 95% CI | % of the older group's price | Younger group costs more | Equal | Younger group costs less |
|---|---:|---:|---|---:|---:|---:|---:|
| Infant − Toddler | 1,011 | $28.53 | [$26.63, $30.43] | +15.3% | 92.4% | 4.9% | 2.7% (27) |
| Toddler − Preschool | 1,011 | $11.31 | [$10.14, $12.47] | +6.5% | 64.5% | 28.6% | 6.9% (70) |
| Infant − Preschool | 1,012 | $39.81 | [$37.53, $42.08] | +22.7% | 96.4% | 0.0% | 3.6% (36) |

- Infant care costs less than preschool in 36 counties (3.6%). These gaps are small (median $3.07, maximum
  $14.63) and concentrated in a few states: SC 10, MI 8, KS 7, LA 5, WV 3, IL/ME/NJ 1 each. Example: seven
  Kansas counties have infant $95.60 and preschool $97.60.
- Toddler and preschool prices are identical in 28.6% of counties.

## 4. Geography: most and least expensive counties

| Age group | 5 most expensive | 5 least expensive |
|---|---|---|
| Infant | San Francisco CA $606.61; Suffolk MA (Boston) $590.00; Arlington VA $559.34; Norfolk MA $555.00; San Mateo CA $554.56 | Five Kansas counties (Wabaunsee, Sumner, Kingman, Doniphan, Osage) at $95.60 |
| Toddler | Norfolk MA $520.00; Arlington VA $496.30; Suffolk MA $493.05; District of Columbia $450.60; San Francisco CA $433.45 | Chatham GA $97.00; Doniphan, Osage, Kingman, Sumner KS $97.60 |
| Preschool | Arlington VA $496.30; San Francisco CA $477.04; San Mateo CA $437.17; Marin CA $433.34; Alexandria VA $424.29 | Pamlico NC $86.19; Yadkin NC $91.22; Gates NC $92.54; Rockingham NC $92.54; Osage KS $97.60 |

- The top of the distribution is dominated by the San Francisco, Boston and Washington DC metro areas.
- Lowest state averages (preschool): AL $125.32, ID $126.03, KS $126.65.
- Highest state averages (preschool): MA $294.55, NJ $295.72, DC $392.50 (DC is one county).

## 5. Robustness: counties are not independent observations

- NDCP prices come from state market-rate surveys and are often reported by state rate zone, so many counties
  in a state share one price. For preschool there are **500 distinct prices across 1,013 counties** in 45 states.
  Examples: Georgia has 74 counties and 4 prices; Tennessee 42 counties and 2 prices; Ohio 38 counties and
  3 prices; New York 38 counties and 5 prices. Full list: `output/tables/ps4_q2_state_clustering_2022.csv`.
- **60.3%** of the variance in preschool prices is between states, not within them.
- 95% CIs with standard errors clustered by state (CR1, t with 44 df):

| Age group | Clustered SE | 95% CI (clustered) | vs. standard SE |
|---|---:|---|---:|
| Infant | $12.43 | [$189.91, $240.00] | 4.8× |
| Toddler | $9.29 | [$167.73, $205.19] | 4.4× |
| Preschool | $8.16 | [$158.64, $191.54] | 4.3× |

| Paired difference | Clustered SE | 95% CI (clustered) |
|---|---:|---|
| Infant − Toddler | $5.10 | [$18.25, $38.81] |
| Toddler − Preschool | $2.21 | [$6.86, $15.75] |
| Infant − Preschool | $5.70 | [$28.32, $51.30] |

- With clustering, the level CIs of neighboring age groups overlap. The paired-difference CIs still exclude zero.

## 6. Data caveats you may want to mention

- **Sample:** 1,235 metro counties in 2022, of which about 1,013 have prices. The 222 without prices are
  concentrated in PR (69), IN (44), PA (37), MO (34) and AR (20).
- **Imputation:** 89.2% of 2022 preschool prices involve at least one NDCP imputation (mostly interpolation
  between survey years, 68.4%). We keep them; see Q1.
- **Unweighted county means:** a county with 5,000 people counts as much as Los Angeles County. This is
  the "average county", not the price faced by the average family.

## Source files

- `output/tables/ps4_q2_summary_2022.csv`
- `output/tables/ps4_q2_percentiles_2022.csv`
- `output/tables/ps4_q2_paired_differences_2022.csv`
- `output/tables/ps4_q2_extremes_2022.csv`
- `output/tables/ps4_q2_state_clustering_2022.csv`
- Scripts: `scripts/06_ps4_q2_distribution_2022.py`, `scripts/07_ps4_q2_factsheet.py`
