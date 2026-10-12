# PS4 Q3: Fact sheet for the written discussion

Metro analysis sample, NDCP median weekly full-time price for **center-based** care. The statistic is the mean
across counties (unweighted), converted to **constant 2022 dollars** with CPI-U. This sheet lists numbers only;
the interpretation is written separately.

Figures:
- Main: [`ps4_q3_real_price_trends.png`](../figures/ps4_q3_real_price_trends.png)
- Nominal vs. real: [`ps4_q3_nominal_vs_real.png`](../figures/ps4_q3_nominal_vs_real.png)
- Robustness: [`ps4_q3_balanced_panel.png`](../figures/ps4_q3_balanced_panel.png)

## 1. Inflation adjustment (CPI-U, CUUR0000SA0, annual average of 12 months)

Real 2022 $ = nominal $ × CPI₂₀₂₂ / CPI_year

| Year | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CPI-U | 237.017 | 240.007 | 245.120 | 251.107 | 255.657 | 258.811 | 270.970 | 292.655 |
| Multiplier to 2022 $ | 1.2347 | 1.2194 | 1.1939 | 1.1655 | 1.1447 | 1.1308 | 1.0800 | 1.0000 |

- The general price level rose 23.5% from 2015 to 2022: 7.9% in 2015–2019 but 14.5% in 2019–2022, including
  8.0% in 2022 alone.

## 2. Mean price by year, real 2022 dollars (all counties with a price)

| Year | N | Infant | Toddler | Preschool |
|---:|---:|---:|---:|---:|
| 2015 | 1,003 | $214.16 | $188.64 | $175.96 |
| 2016 | 1,025 | $212.40 | $187.69 | $174.58 |
| 2017 | 1,063 | $218.29 | $193.15 | $179.54 |
| 2018 | 1,062–1,063 | $217.89 | $192.14 | $179.12 |
| 2019 | 1,062–1,063 | $219.80 | $193.01 | $180.47 |
| 2020 | 1,062–1,063 | $223.38 | $195.56 | $183.25 |
| 2021 | 916–918 | $204.14 | $183.64 | $172.81 |
| 2022 | 1,011–1,013 | $214.95 | $186.46 | $175.09 |

95% CIs, medians and nominal values for every year: `output/tables/ps4_q3_trends_real.csv`.

## 3. Percent changes: nominal vs. real

| Age group | Period | Nominal | **Real** | Real (median across counties) | Real (balanced panel) |
|---|---|---:|---:|---:|---:|
| Infant | 2015–2022 | +23.9% | **+0.4%** | +2.0% | −0.9% |
| Toddler | 2015–2022 | +22.1% | **−1.2%** | −1.7% | −2.1% |
| Preschool | 2015–2022 | +22.9% | **−0.5%** | +1.8% | +0.4% |
| Infant | 2015–2019 | +10.7% | +2.6% | +5.1% | +2.7% |
| Toddler | 2015–2019 | +10.4% | +2.3% | +4.1% | +2.2% |
| Preschool | 2015–2019 | +10.6% | +2.6% | +5.6% | +3.3% |
| Infant | 2019–2022 | +12.0% | −2.2% | −3.0% | −3.6% |
| Toddler | 2019–2022 | +10.6% | −3.4% | −5.5% | −4.1% |
| Preschool | 2019–2022 | +11.1% | −3.0% | −3.6% | −2.9% |
| CPI-U | 2015–2022 | +23.5% | | | |
| CPI-U | 2015–2019 | +7.9% | | | |
| CPI-U | 2019–2022 | +14.5% | | | |

- 2015→2022 in 2022 dollars: infant +$0.80, toddler −$2.18, preschool −$0.87 per week.
- Over the full period, nominal childcare prices rose at almost exactly the rate of general inflation.
- Before 2019, nominal prices grew faster than CPI (about +10.5% vs. +7.9%). After 2019, slower
  (about +11% vs. +14.5%).
- Across all measures the ordering is unchanged: infant > toddler > preschool in every year.

## 4. Sample composition: the 2021 dip

- NDCP has **no 2021 prices at all** for California (37 metro counties), North Carolina (46), Virginia (80) and
  Pennsylvania (37); IL and MO lose 7 each. That is 214 counties priced in 2020 but not in 2021.
- These counties are more expensive than average: their 2020 real preschool mean is $191.28 vs. $183.25 overall.
- Dropping them mechanically lowers the 2021 mean. CA, NC and VA return in 2022 (PA does not), so the mean
  rises again.
- **Balanced panel** (counties with a price in all 8 years): 741–743 counties in 34 states; excludes e.g.
  CA, NC, VA, PA. Real preschool mean: 2015 $168.41 → 2020 $177.71 (peak) → 2021 $176.85 → 2022 $168.99.
  No 2021 dip; instead a drop in 2022 (−4.4% real), when nominal prices in these counties rose +3.2% while
  CPI rose +8.0%.

## 5. Caveats

- Most prices in recent years are NDCP imputations, e.g. linear interpolation between state survey years
  (68% of 2022 metro preschool prices; 100% of 2020 prices carry some imputation). Interpolated prices move
  smoothly by construction and cannot react to sudden events such as COVID or the 2021–22 inflation spike.
- CPI-U measures all consumer prices, not childcare providers' costs. "Real" means relative to the general
  price level.
- These are unweighted county means (see Q2).

## Source files

- `output/tables/ps4_q3_trends_real.csv`
- `output/tables/ps4_q3_changes.csv`
- `data/analysis/ndcp_metro_2015_2022_real.csv` (all 12 NDCP price columns in 2022 $, for PS5 and the final project)
- Script: `scripts/08_ps4_q3_real_trends.py`
