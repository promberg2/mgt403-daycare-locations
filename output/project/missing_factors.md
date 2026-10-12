# (e) Factors the prediction is missing: draft

The selection uses price, childcare-worker wage, rent, demand (children needing care, care-need share, income) and persistence. Below are the factors a final market selection should add. Where public data allow, they are quantified for the top 10 (script `30_fp_missing_factors.py`; table `output/tables/fp_e_missing_factors_top10.csv`). Percentiles refer to the 2022 analysis sample of metro counties.

## A. Quantified with public data (not yet part of the selection)

**1. Competition / supply (Census County Business Patterns, NAICS 624410, 2022)**
- Sample median: 4.9 childcare establishments per 1,000 children needing care.
- Top 10:
  - most are average to dense, e.g. San Francisco 14.2 (99th pct), Multnomah 12.2 (98th pct);
  - Hall GA 2.6 (5th pct) and Sullivan TN 3.0 (10th pct) are thinly supplied.
- High prices despite dense competition (SF, Portland) point to strong willingness to pay. Thin supply (Hall, Sullivan) can mean unmet demand, an entry opportunity, or a market too small to sustain centers.
- Across all counties, premium and center density are only weakly related (Spearman 0.14), so the premium is *not* simply a sign of missing supply.
- Limitation: CBP counts employer establishments only, not their capacity or quality, and not home-based providers without employees.

**2. Demand trend (ACS, children under 6, 2015 → 2022)**
- Sample median: −4.4%.
- Shrinking child populations in Multnomah OR (−15.8%, 11th pct) and Fairfax VA (−9.5%).
- Only Loudoun (+0.8%) and Howard (+0.5%) are growing.
- A falling child population erodes future demand even where today's premium is high.

**3. Cost dynamics (2022 dollars)**
- Real childcare-worker wage growth 2019 → 2022 (sample median +1.8%):
  - Hall GA +13.3% (97th pct), Howard +8.6%, Multnomah +7.6%;
  - Washington DC-area counties +5.1%.
- Real rent growth 2015 → 2022 (sample median +5.5%):
  - Multnomah +27.3% (98th pct), San Francisco +20.4%, Olmsted +16.8%.
- Fast-rising costs can erode the premium in future.

## B. Not in our data (would need additional research)

4. **Public / subsidized preschool.** Free public pre-K competes directly with paid center-based preschool. *(Background knowledge, to verify before final use:)* Georgia has a statewide lottery-funded pre-K program for 4-year-olds (Hall County); Multnomah County voters approved "Preschool for All" (2020), which started offering free seats in 2022; Virginia's pre-K initiative is targeted rather than universal.
5. **Commercial real-estate costs and site availability.** We use residential median gross rent (ACS) as the rent proxy. A center pays commercial rent and needs suitable licensed space, outdoor area and zoning approval.
6. **Labor availability and turnover.** OEWS gives average wages, not vacancies or turnover. Staffing a center can be the binding constraint, especially where wages rise fastest (Hall).
7. **Local regulation.** State fixed effects absorb state-level rules (staff ratios, licensing). Local requirements and county-level differences in enforcement are not captured.
8. **Price data quality.**
   - NDCP prices are medians of state market-rate surveys: only 2–5 direct survey years per top-10 county; other years are interpolated.
   - The 2022 CA/VA prices are model extrapolations.
   - A county median may not be the price a new premium provider can charge (quality mix).
   - Mitigated, but not removed, by using the average premium over 2015–2022.
9. **Willingness to pay of the target segment and post-COVID shifts.** Income and dual-earner shares are included, but not commuting patterns or remote work after 2020 (relevant for San Francisco and the Washington DC area) or employer-sponsored childcare.
10. **Model fit.** Wage, rent and state effects explain 81% of 2022 price variation; about 19% (≈ 14% of the price, one residual SD) reflects factors we do not observe. That is exactly why the premium can be large, and why it should be verified locally.

## C. Implications for the top 10 (risk flags)
- **Lowest risk on these factors:** Loudoun VA and Howard MD (growing child population, moderate rent growth), Arlington and Alexandria VA (stable demand, flat rents).
- **Watch:**
  - Multnomah OR: shrinking child population, sharply rising rents, free public preschool;
  - Hall GA: low supply, fast wage growth, statewide pre-K;
  - Sullivan TN: smallest market, thin supply;
  - San Francisco: very dense competition, rising rents.
