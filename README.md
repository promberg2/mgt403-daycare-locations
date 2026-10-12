# MGT 403 Data Project: Where Should We Open Our Next Daycare?

Yale SOM, MGT 403 Probability Modeling and Statistics, Fall 2026.
Team: Carson Tavares, Lee Itzhaki, Vusala Suleymanova, Philipp Romberg.

This repository contains all code and data used to produce our submission: the slide deck, the combined Pre-analysis and
Appendix document, and the AI prompt log. Every number in the deck and the document is computed by the scripts below from public
data; nothing is typed in by hand.

## Deliverables

| File | Content |
|---|---|
| `project/deck/MGT403_FinalProject_Deck.pdf` (+ `.pptx`) | Slide deck, 6 slides (assignment items a–e) |
| `project/submission/MGT403_PreAnalysis_and_Appendix.pdf` | Part I: pre-analysis tasks 1–4; Part II: appendix (data handling, methods, decisions, checks) |
| `project/submission/MGT403_Prompt_Log.pdf` (+ `.md`) | Every prompt given to the AI tool (Claude Code, https://claude.ai/code), dated, verbatim |

## Quick start (reproduce all results)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # macOS/Linux: .venv/bin/python
.venv/Scripts/python run_pipeline.py
```

`run_pipeline.py` runs the scripts in `scripts/` in order and rebuilds all tables (`output/tables`), figures (`output/figures`),
the deck (`.pptx`) and the document. It starts from the data included in `data/` and needs no internet access or keys.
`output/project/deck_number_check.md` then shows that every number stated on the slides matches the result tables.

Options:

- `--full` also re-downloads the raw data first (CPI-U, BLS OEWS, Census ACS). This needs
  - `BLS_CONTACT_EMAIL`: **your own** e-mail address (BLS requires a contact in the User-Agent of scripted downloads), and
  - a free Census API key (https://api.census.gov/data/key_signup.html) in `CENSUS_API_KEY` or a file `census_api_key.txt`
    in the project root (git-ignored; our key is not included).
- `--homework` also reruns the Problem Set 4/5 scripts that only answer homework questions.

Two steps need Windows software and are optional: the deck PDF export (`scripts/export_deck.ps1`, Microsoft PowerPoint) and the
HTML-to-PDF printing of the document (Microsoft Edge, headless). All analysis results are produced by Python alone.

## Data

| Source | What we use | Location |
|---|---|---|
| U.S. DOL, National Database of Childcare Prices (NDCP) | Median weekly price, center-based preschool, by county, 2015–2022 | `data/raw/ndcp/NDCP2022.xlsx` (manual download; dol.gov blocks scripts) |
| BLS Occupational Employment and Wage Statistics (OEWS) | Mean annual wage, childcare workers (SOC 39-9011); preschool teachers (25-2011) for robustness | raw zips **not included** (275 MB): `scripts/02_get_oews.py` downloads them; the extracted wages are in `data/interim/` |
| Census ACS 5-year (API) | Rent, children under 6, working parents, population, income | `data/raw/acs/` |
| BLS CPI-U (CUUR0000SA0) | Conversion to 2022 dollars | `data/raw/cpi/` |
| Course county–OEWS crosswalk | Links counties to OEWS areas; metro = area code starting with 00 | `data/crosswalks/` |
| Census County Business Patterns (NAICS 624410) | Childcare establishments (competition check) | `data/raw/cbp/` |
| Census Gazetteer, cartographic boundaries | Map on slide 1 | `data/raw/geo/` |
| State and county public pre-K program rules | Public pre-K check (sources and access dates in the file) | `data/manual/public_prek_programs.csv` |

Raw files are never edited. `data/raw_checksums.sha256` fixes the SHA-256 of every downloaded file (including the OEWS zips, so a
re-download can be verified). `data/interim/` holds cleaned extracts, `data/analysis/` the analysis samples.

## Scripts (run in this order)

| Scripts | Purpose |
|---|---|
| `01`–`05`, `08`, `12`, `13`, `15` | Data construction from Problem Sets 4–5 (downloads, NDCP prices, OEWS wages, ACS, CPI, crosswalk merge, metro sample, 2022 dollars) |
| `06`, `07`, `09`–`11`, `14`, `16`, `17` | Homework-only answers for Problem Sets 4–5 (not needed for the project) |
| `18`–`23` | Pre-analysis tasks 1–4 (merge, analysis dataset, descriptives, scatter plots, regressions) |
| `25`–`32` | Final project: cost models and premiums, selection rule, checks, stability, missing factors, robustness, analysis register |
| `33`–`37` | Deck figures, deck, number check, appendix analysis, combined document |
| `38` | Builds the prompt log from the team's working logs (kept outside this repository); its output is included |
| `export_deck.ps1` | Exports the deck to PDF via PowerPoint (Windows) |

Each script starts with a docstring stating its inputs, method and outputs. The appendix (Part II, G2) lists every script.

## Folder layout

```
data/        raw/ (source files), crosswalks/, manual/, interim/, analysis/, raw_checksums.sha256
scripts/     numbered analysis scripts (see above)
output/      tables/ (all results as CSV), figures/, project/ (decisions, analysis register, number check), ps4/, ps5/
project/     deck/, submission/ (document, prompt log), assets/ (Yale SOM logo files)
run_pipeline.py, requirements.txt
```

## AI use

AI assistance is allowed for this project. The analysis code, figures and drafts of the documents were produced with Claude Code
(https://claude.ai/code) at the team's direction. Every prompt, verbatim and dated, is in `project/submission/MGT403_Prompt_Log.pdf`.
Interpretations marked as the team's own text and all methodological decisions were made by the team.
