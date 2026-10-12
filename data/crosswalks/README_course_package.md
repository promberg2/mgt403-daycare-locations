# MGT-403 Data Project — Student Package

This folder is the complete student-facing package for the MGT-403 childcare data
project (Version 3, 2026-09-20). Everything you are given is here.

## Contents

- **`ASSIGNMENT.pdf`** — the full assignment: two graded homework problems (on
  Problem Sets 4 and 5), the pre-analysis project data work, and the open-ended
  final project. It lists the data sources, the required years (2015–2022), the
  required ACS variables (with Census codes), geography/FIPS guidance, and the
  CPI-U inflation instructions.
- **`data/crosswalks/county_oews_crosswalk.csv`** — the single provided dataset:
  the **county × year → OEWS area** crosswalk. Use it to (a) merge BLS OEWS
  area-level wages down to counties, (b) define the metro analysis sample
  (`oews_area` begins `00`), and (c) label each county's metropolitan area (the
  `area_title` field).

## The data you pull yourself

Apart from the crosswalk above, you download the source data directly from the
public providers (instructions and exact series/variables are in `ASSIGNMENT.pdf`):

- **DOL National Database of Childcare Prices (NDCP)** — childcare prices.
- **BLS Occupational Employment and Wage Statistics (OEWS)** — childcare-worker
  wages, occupation **SOC 39-9011**.
- **U.S. Census American Community Survey (ACS) 5-year** — demand/demographics,
  pulled at the county level via the Census API.

## The OEWS crosswalk (`county_oews_crosswalk.csv`)

**Why it exists:** OEWS publishes wages at the *area* level (metropolitan and
nonmetropolitan areas), not the county level. BLS publishes which counties make up
each area, but the definitions change over time and, in New England, OEWS areas
are town-based rather than county-based. This crosswalk maps each county directly
to its OEWS `area` code for each year so the wage merge works everywhere. One row
per **county × year** (2015–2022); merge OEWS wage rows on `[year, oews_area]`
(zero-pad the OEWS `area` field to 7 characters first).

| Column | Meaning |
|---|---|
| `county_fips` | 5-char `state(2)+county(3)` FIPS |
| `state_abbr` | 2-letter state abbreviation |
| `year` | Data year (2015–2022) |
| `oews_area` | 7-character OEWS area code (merge key) |
| `area_title` | OEWS area name |
