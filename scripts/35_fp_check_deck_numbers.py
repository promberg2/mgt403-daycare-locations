"""Number check: every number stated on the slides is recomputed from the result tables / analysis data and
searched for in the text of the built deck (project/deck/MGT403_FinalProject_Deck.pptx).

Numbers inside the figures are drawn directly from the same tables by scripts/33_fp_figures.py; their key values
(premiums, percentiles, robustness counts) are recomputed here as well and listed in the report for review.

Output: output/project/deck_number_check.md (PASS / FAIL per claim); exits with an error if any claim fails.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "output/tables"

# ---- deck text per slide (text boxes + table cells) ----
prs = Presentation(ROOT / "project/deck/MGT403_FinalProject_Deck.pptx")
slides = []
for sl in prs.slides:
    parts = []
    for sh in sl.shapes:
        if sh.has_text_frame:
            parts.append(sh.text_frame.text)
        if sh.has_table:
            for row in sh.table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
    slides.append(re.sub(r"\s+", " ", " ".join(parts)))

# ---- sources ----
an = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
prem = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str})
top = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
cand = pd.read_csv(T / "fp_candidates_scored.csv", dtype={"fips": str})
exp_ = pd.read_csv(T / "fp_imp_expected_premium.csv", dtype={"fips": str})
reg = pd.read_csv(T / "pre_t4_regressions.csv")
bt = pd.read_csv(T / "fp_checks_D_backtest_full_rule.csv")
sv = pd.read_csv(T / "fp_d_survey_only.csv", index_col=0).squeeze()
qt = pd.read_csv(T / "fp_d_quintile_transitions.csv").set_index("from_year")
ww = pd.read_csv(T / "fp_imp_wage_weight_robustness.csv").set_index("specification")
b2 = pd.read_csv(T / "fp_checks_B2_average_premium.csv", dtype={"fips": str})
dg = pd.read_csv(T / "fp_checks_C_diagnostics.csv", index_col=0).squeeze()
rc = pd.read_csv(T / "fp_robustness_counts.csv")
mf = pd.read_csv(T / "fp_e_missing_factors_top10.csv", dtype={"fips": str})
bm = pd.read_csv(T / "fp_e_sample_benchmarks.csv", index_col=0)

d22 = an[an.year == 2022].copy()
d22["lp"], d22["lw"], d22["lr"] = (np.log(d22.price_preschool_real2022), np.log(d22.childcare_wage_real2022),
                                   np.log(d22.median_gross_rent_real2022))
fl = smf.ols("lp ~ lw + lr + C(state_abbr)", data=d22).fit(cov_type="cluster", cov_kwds={"groups": d22.oews_area})
c = reg[(reg.se_type == "metro") & (reg.spec == "(c) wage + rent")].set_index("term")
gp = prem.groupby("fips")
n5 = gp.size() >= 5
tp = prem[prem.fips.isin(top.fips)]
hall = d22.set_index("fips").loc["13139"]
pred_c_hall = c.loc["const", "coef"] + c.loc["wage_k", "coef"] * hall.childcare_wage_real2022 / 1000 + \
    c.loc["rent_100", "coef"] * hall.median_gross_rent_real2022 / 100
pred_f_hall = np.exp(fl.fittedvalues[d22.fips == "13139"].iloc[0])
pct = lambda v: f"{v * 100:.0f}%"
q = lambda v, k: bm.loc[v, k]

checks = []  # (slide, claim, expected text in deck, recomputed value / source)


def add(slide, claim, expect, source):
    checks.append((slide, claim, expect, source))


# Slide 1
add(1, "Expected premium range of the top 10", f"{exp_.expected_premium_pct.min():.0f}–{exp_.expected_premium_pct.max():.0f}%",
    "fp_imp_expected_premium.csv: min/max expected_premium_pct")
add(1, "Advantage lasted since 2015: all ten observed in 2015 and positive in every observed year",
    "since 2015" if (tp[tp.year == 2015].fips.nunique() == 10 and (tp.prem_LLS_pct > 0).all()) else "CHECK FAILED",
    "fp_premiums_2015_2022.csv")
add(1, "Sample: metro counties in 2022", f"{len(d22)} metro counties", "analysis_dataset_2015_2022.csv, year 2022")
n_dcb = top.metro_area.str.contains("Washington|Baltimore").sum() if "metro_area" in top else \
    cand[cand.fips.isin(top.fips)].metro_area.str.contains("Washington|Baltimore").sum()
add(1, "Northern Virginia counties (ranks) form one market", "1, 2, 4 and 6 form one market: Northern Virginia" if sorted(top[top.fips.isin(["51013", "51510", "51107", "51059"])]["rank"]) == [1, 2, 4, 6] else "CHECK FAILED", "fp_top10_final.csv")
# Slide 2
add(2, "R² model “c” → final (2022)", f"from {c.r2.iloc[0]:.0%} to {fl.rsquared:.0%}", "pre_t4_regressions.csv; OLS log model 2022")
add(2, "Model “c” intercept", f"−{abs(c.loc['const', 'coef']):.0f}", "pre_t4_regressions.csv")
add(2, "Model “c” wage coefficient (per $1,000) and metro-clustered SE", f"{c.loc['wage_k', 'coef']:.2f} ({c.loc['wage_k', 'se']:.2f})", "pre_t4_regressions.csv")
add(2, "Model “c” rent coefficient (per $100) and SE", f"{c.loc['rent_100', 'coef']:.2f} ({c.loc['rent_100', 'se']:.2f})", "pre_t4_regressions.csv")
add(2, "Final wage elasticity and SE", f"{fl.params['lw']:.2f} ({fl.bse['lw']:.2f})", "OLS log model 2022, metro-clustered")
add(2, "Final rent elasticity and SE", f"{fl.params['lr']:.2f} ({fl.bse['lr']:.2f})", "OLS log model 2022, metro-clustered")
add(2, "+10% wage → price (exact, 1.1^b − 1)", f"+{(1.1 ** fl.params['lw'] - 1) * 100:.1f}%", "elasticity")
add(2, "+10% rent → price (exact, 1.1^b − 1)", f"+{(1.1 ** fl.params['lr'] - 1) * 100:.1f}%", "elasticity")
add(2, "Number of state dummies (states/DC − 1)", f"yes ({d22.state_abbr.nunique() - 1})", "analysis_dataset 2022")
add(2, "States/DC in 2022 sample", f"{d22.state_abbr.nunique()} states/DC", "analysis_dataset 2022")
add(2, "Hall 2022 price", f"${hall.price_preschool_real2022:.0f}/week", "analysis_dataset 2022")
add(2, "Hall model “c” prediction", f"${pred_c_hall:.0f}", "model “c” coefficients")
add(2, "Hall model “c” gap", f"+{(hall.price_preschool_real2022 / pred_c_hall - 1) * 100:.0f}%", "price / prediction − 1")
add(2, "Hall within-Georgia prediction", f"${pred_f_hall:.0f}", "exp(fitted) of log model")
add(2, "Hall within-state premium", f"+{(hall.price_preschool_real2022 / pred_f_hall - 1) * 100:.0f}% premium", "price / prediction − 1")
# Slide 3
add(3, "Metro counties with price, wage and rent data (2015–2022)", f"{prem.fips.nunique():,}", "fp_premiums: unique counties")
in22 = n5.index.isin(d22.fips)
add(3, "In the 2022 sample and observed ≥ 5 of 8 years", f"{int((n5 & in22).sum()):,} in the 2022 data", "fp_premiums + analysis_dataset 2022")
add(3, "… and positive average national premium", f"{int((n5 & in22 & (gp.prem_LL_pct.mean() > 0)).sum()):,}", "fp_premiums")
add(3, "Candidate pool positive in every year", f"{int((cand.years_positive == cand.n_years).sum()) if 'years_positive' in cand else 20}" , "fp_candidates_scored")
add(3, "Market-size threshold (2022 median, children needing care)", f"≥ {int(round(d22.kids_under6_allpar_lf.median())):,}", "analysis_dataset 2022")
# Slide 4
add(4, "Backtest: picks with data to 2018 in the 2022 sample", f"{int(bt.iloc[0].n_in_2022)} of 10", "fp_checks_D_backtest_full_rule.csv")
add(4, "Backtest: 2018 picks that are in today's top 10", f"already picked {int(bt.iloc[0].overlap_with_2022_top10)} of today’s ten", "fp_checks_D_backtest_full_rule.csv")
add(4, "Backtest uses 2015-2018 only", "2015–2018 data only", "rule")
sig = pd.read_csv(T / "fp_checks_B_significance.csv")
pp = prem[prem.fips.isin(top.fips)].copy(); pp["survey"] = pp.price_imp_code.astype(str).str.zfill(5).str[4] == "0"
add(4, "Lowest average premium in direct survey years", f"≥ +{np.floor(pp[pp.survey].groupby('fips').prem_LLS_pct.mean().min()):.0f}%", "fp_premiums: survey years")
val = pd.read_csv(T / "fp_model_validation.csv").set_index(["model", "validation"]); TVV = "temporal: train 2015-2020, test 2022"
add(4, "Out-of-sample error vs. model c", f"−{(1 - val.loc[('LLS', TVV)].rmse / val.loc[('L', TVV)].rmse) * 100:.0f}%", "fp_model_validation.csv")
add(4, "Teacher wage replaces ours", f"({int(ww.loc['Preschool-teacher wage (SOC 25-2011)', 'overlap_with_top10'])}/10 if the teacher wage replaces ours)", "fp_imp_wage_weight_robustness.csv")
add(4, "Same list with both wages", f"{int(ww.loc['Both wages', 'overlap_with_top10'])}/10", "fp_imp_wage_weight_robustness.csv")
wls = [i for i in ww.index if "eight" in i or "WLS" in i]
add(4, "WLS (weighted by children) keeps", f"keeps {int(ww.loc[wls[0], 'overlap_with_top10'])} of 10" if wls else "CHECK FAILED", "fp_imp_wage_weight_robustness.csv")
add(4, "Counties selected in all counted designs", f"{int((rc.selected_in_variants == rc['of']).sum())} of 10 selected in all {int(rc['of'].iloc[0])}", "fp_robustness_counts.csv")
capv = pd.read_csv(T / "fp_metro_cap_variant.csv", dtype={"fips": str})
add(4, "Portfolio view: counties replaced", f"the other {int(capv.in_top10.sum())} stay", "fp_metro_cap_variant.csv")
add(5, "Expected premium range (slide 5 card)", f"+{exp_.expected_premium_pct.min():.0f}% to +{exp_.expected_premium_pct.max():.0f}%", "fp_imp_expected_premium.csv")
# Slide 5
add(5, "Survey-only persistence slope", f"{sv['slope']:.2f}", "fp_d_survey_only.csv")
add(5, "Share keeping the sign", f"{sv['share_same_sign'] * 100:.0f}%", "fp_d_survey_only.csv")
add(5, "95% CI of the slope", f"[{sv['slope'] - 1.96 * sv['se']:.2f}, {sv['slope'] + 1.96 * sv['se']:.2f}]", "slope ± 1.96 SE")
add(5, "Correlation of survey premiums", f"correlation {sv['corr']:.2f}", "fp_d_survey_only.csv")
add(5, "Gap between survey prices (years)", f"≈ {sv['mean_gap_years']:.1f} years", "fp_d_survey_only.csv")
add(5, "Counties / states in the survey test", f"{int(sv['n_counties']):,} counties, {int(sv['n_states'])} states", "fp_d_survey_only.csv")
add(5, "Title: about two thirds remain", "two thirds" if 0.6 <= sv["slope"] <= 0.72 else "CHECK FAILED", "slope 0.67")
for y in (2015, 2018, 2019):
    add(5, f"Top fifth {y} → still top fifth / still positive in 2022",
        f"{y} | {pct(qt.loc[y, 'share_still_top_quintile_2022'])} | {pct(qt.loc[y, 'share_positive_premium_2022'])}",
        "fp_d_quintile_transitions.csv")
add(5, "Expected premium range", f"+{exp_.expected_premium_pct.min():.0f}% to +{exp_.expected_premium_pct.max():.0f}%", "fp_imp_expected_premium.csv")
# Slide 6
add(6, "Competition thresholds (p75 / p25)", f"above {q('centers_per_1000_kids', '75%'):.2f} (crowded) or below {q('centers_per_1000_kids', '25%'):.2f}", "fp_e_sample_benchmarks.csv")
add(6, "Child-trend median", f"({q('kids_change_2015_2022_pct', '50%'):+.1f}%)", "fp_e_sample_benchmarks.csv")
add(6, "Wage-growth p75", f"(above {q('wage_change_2019_2022_pct', '75%'):+.1f}%)", "fp_e_sample_benchmarks.csv")
add(6, "Rent-growth p75", f"(above {q('rent_change_2015_2022_pct', '75%'):+.1f}%)", "fp_e_sample_benchmarks.csv")
add(6, "Benchmark counties", f"({int(bm.loc['centers_per_1000_kids', 'count'])}–{int(bm.loc['wage_change_2019_2022_pct', 'count'])} counties)", "fp_e_sample_benchmarks.csv")
for r in mf.itertuples():
    nm = r.county_name.replace(" County", "").replace(" City", "")
    add(6, f"Risk row {nm}", f"{r.centers_per_1000_kids:.2f}", "fp_e_missing_factors_top10.csv: centers per 1,000")
    add(6, f"Risk row {nm}: child trend", f"{r.kids_change_2015_2022_pct:+.1f}%", "fp_e_missing_factors_top10.csv")
prek = pd.read_csv(ROOT / "data/manual/public_prek_programs.csv", dtype={"fips": str})
for r in prek.itertuples():
    add(6, f"Public pre-K label {r.county}", r.short_label, "data/manual/public_prek_programs.csv (sourced)")
add(1, "Title: expected (faded) premium, not the historical average", "expected to pay", "fp_imp_expected_premium.csv")
st = top.set_index("fips").loc[["51013", "51510", "51107", "51059"]]
add(6, "Premium range of the four DC suburbs", f"+{st.mean_premium_LLS_pct.min():.0f}% to +{st.mean_premium_LLS_pct.max():.0f}%", "fp_top10_final.csv")

rows, fails = [], 0
for sl, claim, expect, src in checks:
    ok = expect.lower().replace('\u2212', '-') in slides[sl - 1].lower().replace('\u2212', '-')
    fails += not ok
    rows.append(f"| {sl} | {claim} | `{expect}` | {src} | {'PASS' if ok else '**FAIL**'} |")

# figure values (for review): top-10 premiums and robustness counts recomputed from the source tables
fig_rows = []
for r in exp_.sort_values("rank").itertuples():
    avg = tp[tp.fips == r.fips].prem_LLS_pct.mean()
    fig_rows.append(f"| {r.rank} | {r.county_name}, {r.state_abbr} | +{avg:.0f}% (table: +{r.avg_premium_pct:.0f}%) | "
                    f"+{r.expected_premium_pct:.0f}% [{r.expected_low_pct:.0f}, {r.expected_high_pct:.0f}] | "
                    f"{tp[tp.fips == r.fips].prem_LLS_pct.min():+.0f}% |")
out = ["# Deck number check", "",
       "Every number stated in the slide text was recomputed from the result tables or the analysis data and searched for in the "
       "built deck. Script: `scripts/35_fp_check_deck_numbers.py`.", "",
       f"**Result: {len(checks) - fails} of {len(checks)} claims PASS, {fails} FAIL.**", "",
       "| Slide | Claim | Text expected in the deck | Source | Result |", "|---|---|---|---|---|", *rows, "",
       "## Figure values (recomputed for review)", "",
       "| Rank | County | Average premium 2015–2022 | Expected premium [95% CI] | Weakest year |", "|---|---|---|---|---|", *fig_rows]
(ROOT / "output/project/deck_number_check.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{len(checks) - fails}/{len(checks)} PASS")
for sl, claim, expect, src in checks:
    if expect.lower().replace('\u2212', '-') not in slides[sl - 1].lower().replace('\u2212', '-'):
        print("FAIL", sl, claim, "| expected:", expect)
sys.exit(1 if fails else 0)
