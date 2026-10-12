"""Build the combined Pre-Analysis and Appendix document (HTML -> PDF with headless Microsoft Edge), in the design language of the deck.

Every number is read from output/tables/*.csv or recomputed from data/analysis/*.csv in this script; nothing is typed
in by hand. Section letters match the references on the slides (B-C model, D selection and stability, E reliability,
F local factors).

Output: project/submission/MGT403_PreAnalysis_and_Appendix.html / .pdf
"""
import ast
import re
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "project/submission"
SUB.mkdir(parents=True, exist_ok=True)
T, FIGDIR = ROOT / "output/tables", "../../output/figures"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
TEAM = "Carson Tavares · Lee Itzhaki · Vusala Suleymanova · Philipp Romberg"
rd = lambda name, **kw: pd.read_csv(T / name, **kw)

# ------------------------------------------------------------------ data ------------------------------------------------
a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str, "price_imp_code": str})
panel = pd.read_csv(ROOT / "data/analysis/project_panel_2015_2022.csv", dtype={"fips": str}, usecols=["year", "fips"])
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
top = rd("fp_top10_final.csv", dtype={"fips": str})
cand = rd("app_candidates.csv", dtype={"fips": str})
exp_ = rd("fp_imp_expected_premium.csv", dtype={"fips": str})
flow = rd("pre_t1_sample_flow.csv")
models = rd("app_models_2022.csv").set_index("model")
yearly = rd("app_yearly_models.csv")
val = rd("fp_model_validation.csv")
reg = rd("pre_t4_regressions.csv")
persist = rd("fp_d_persistence_regressions.csv")
quint = rd("fp_d_quintile_transitions.csv").set_index("from_year")
sv = rd("fp_d_survey_only.csv", index_col=0).squeeze()
bt = rd("fp_checks_D_backtest_full_rule.csv")
bt18 = rd("app_backtest_2018.csv")
rob = rd("fp_robustness.csv")
robc = rd("fp_robustness_counts.csv")
ww = rd("fp_imp_wage_weight_robustness.csv")
wfit = rd("fp_imp_wage_model_fit.csv")
sig = rd("fp_checks_B_significance.csv")
b2 = rd("fp_checks_B2_average_premium.csv", dtype={"fips": str})
diag = rd("fp_checks_C_diagnostics.csv", index_col=0).squeeze()
qual = rd("app_ndcp_quality_top10.csv", dtype={"fips": str})
mf = rd("fp_e_missing_factors_top10.csv", dtype={"fips": str})
bm = rd("fp_e_sample_benchmarks.csv", index_col=0)
dcg = rd("fp_imp_dc_grouping.csv", index_col=0).squeeze()
excl = rd("app_excluded_no2022.csv", dtype={"fips": str})
prek = pd.read_csv(ROOT / "data/manual/public_prek_programs.csv", dtype={"fips": str}).set_index("fips")
check_md = (ROOT / "output/project/deck_number_check.md").read_text(encoding="utf-8")
check_line = [l for l in check_md.splitlines() if l.startswith("**Result")][0].strip("*")

d22 = a[a.year == 2022].copy()
SHORT = {r.fips: f"{r.county_name.replace(' County', '').replace(' City', '')}, {r.state_abbr}" for r in top.itertuples()}
gp = p.groupby("fips")
n_all = p.fips.nunique()
n5_all = int((gp.size() >= 5).sum())
in22 = gp.size().index.isin(d22.fips)
n22_5 = int(((gp.size() >= 5) & in22).sum())
n22_5nat = int(((gp.size() >= 5) & in22 & (gp.prem_LL_pct.mean() > 0)).sum())
thr = d22.kids_under6_allpar_lf.median()
avg_arith = gp.prem_LLS_pct.mean()
c_ = reg[(reg.se_type == "metro") & (reg.spec == "(c) wage + rent")].set_index("term")
ra = reg[(reg.se_type == "metro") & (reg.spec == "(a) wage")].set_index("term")
rb = reg[(reg.se_type == "metro") & (reg.spec == "(b) rent")].set_index("term")
# Hall example (as on slide 2)
d22["lp"], d22["lw"], d22["lr"] = np.log(d22.price_preschool_real2022), np.log(d22.childcare_wage_real2022), np.log(d22.median_gross_rent_real2022)
fl = smf.ols("lp ~ lw + lr + C(state_abbr)", data=d22).fit(cov_type="cluster", cov_kwds={"groups": d22.oews_area})
hall = d22.set_index("fips").loc["13139"]
hall_c = c_.loc["const", "coef"] + c_.loc["wage_k", "coef"] * hall.childcare_wage_real2022 / 1000 + c_.loc["rent_100", "coef"] * hall.median_gross_rent_real2022 / 100
hall_f = float(np.exp(fl.fittedvalues[d22.fips == "13139"].iloc[0]))
# CA / VA 2022 extrapolation evidence (nominal NDCP prices, 2020 -> 2022)
nom = a.pivot_table(index="fips", columns="year", values="price_preschool")
chg = lambda f: (nom.loc[f, 2022] / nom.loc[f, 2020] - 1) * 100
wi = d22[d22.state_abbr == "WI"]


# ------------------------------------------------------------------ helpers ---------------------------------------------
def pc(v, d=0, sign=True):
    out = f"{v:+.{d}f}%" if sign else f"{v:.{d}f}%"
    out = "0%" if d == 0 and out in ("+0%", "-0%") else out
    return out.replace("-", "\u2212")  # typographic minus


def tbl(head, rows, align=None, cls="", widths=None, hl=()):
    align = align or ["l"] + ["r"] * (len(head) - 1)
    cg = "".join(f"<col style='width:{w}'>" for w in widths) if widths else ""
    th = "".join(f"<th class='{al}'>{h}</th>" for h, al in zip(head, align))
    body = "".join("<tr" + (" class='hl'" if i in hl else "") + ">" + "".join(f"<td class='{al}'>{c}</td>" for c, al in zip(r, align)) + "</tr>"
                   for i, r in enumerate(rows))
    return f"<table class='{cls}'><colgroup>{cg}</colgroup><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def box(kind, label, html):
    return f"<div class='box {kind}'><div class='boxlabel'>{label}</div>{html}</div>"


def fig(name, cap, width="100%"):
    return f"<figure><img src='{FIGDIR}/{name}' style='width:{width}'><figcaption>{cap}</figcaption></figure>"


def stats_row(items):
    return "<div class='stats'>" + "".join(f"<div class='stat'><div class='num'>{n}</div><div class='lab'>{l}</div></div>" for n, l in items) + "</div>"


def section(letter, title, slides):
    ref = f"<span class='slideref'>{slides}</span>" if slides else ""
    return f"<div class='section'><div class='eyebrow'>Appendix {letter}{ref}</div><h2>{title}</h2>"


BEYOND = "<span class='beyond'>Beyond course scope</span>"

# ================================================================== COVER =================================================
top_rows = []
for r in top.itertuples():
    e = exp_.set_index("fips").loc[r.fips]
    top_rows.append([f"<b>{r.rank}</b>", SHORT[r.fips], "Northern Virginia" if r.fips in ("51013", "51510", "51107", "51059") else r.metro_area.split(",")[0].split("-")[0], pc(avg_arith[r.fips]),
                     f"<b>{pc(e.expected_premium_pct)}</b>", f"{r.kids_under6_allpar_lf:,.0f}", f"{r.score:.2f}"])
cover = f"""
<div class='cover-page'><div class='cover'>
  <div class='kicker'>MGT 403 · Probability Modeling &amp; Statistics · Yale SOM · Data Project</div>
  <h1>Where should we open our next preschool?</h1>
  <div class='subtitle'>Pre-analysis and appendix: the data, methods and checks behind our answer</div>
  <div class='team'>{TEAM} · October 2026</div>
</div>
<div class='lead'>We look for counties where parents pay much more for center-based preschool than local costs justify, where this
advantage has lasted for years, and where enough families need care. This document answers the pre-analysis tasks and shows how each of our ideas became a
measurable step, which data and samples each step uses, and how we tested whether the result can be trusted.</div>
<h3>Our answer: ten counties</h3>
{tbl(["Rank", "County", "Metro area", "Average premium 2015–22", "Expected premium", "Children needing care", "Score"],
     top_rows, align=["c", "l", "l", "r", "r", "r", "r"], widths=["7%", "21%", "20%", "15%", "13%", "13%", "11%"], cls="small")}
<p class='note'>Premium = how much the county's preschool price exceeds the price predicted from its childcare-worker wage and rent,
compared with counties in the same state (Appendix B). Expected premium = the average premium after the typical fading of premiums
over about five years (Appendix D). Score = 50% premium rank + 50% demand rank among the ten (Appendix D).</p>
<h3>How to read this document</h3>
{tbl(["Part", "Content", "Slide"], [
    ["Pre", "Pre-analysis tasks 1–4: analysis dataset, descriptives, scatter plots, regressions (model “c”)", "2"],
    ["0", "From our ideas to measurable steps; which years enter which analysis", "–"],
    ["A", "Data sources, variables, samples and every data-handling decision", "all"],
    ["B", "Cost model: from model “c” to the final model; fit and residuals", "2"],
    ["C", "Out-of-sample validation of the cost model", "2"],
    ["D", "Team decisions, selection rule, candidates, score, market characteristics; stability", "3, 5"],
    ["E", "Reliability: backtest, robustness, portfolio view, statistical checks, data quality", "4"],
    ["F", "What the model does not see: risk flags, public pre-K, the Northern Virginia cluster, other candidates", "6"],
    ["G", "Limitations and reproducibility (scripts, data, checks, AI use)", "–"]],
    align=["c", "l", "c"], widths=["8%", "80%", "12%"], cls="small")}
<p class='note'><span class='tagteam'>Team</span> boxes contain the team's own interpretations and decisions (decisions were taken after the options and evidence were laid out; Appendix D). Data work, statistics and drafts of the text were produced with an AI tool (Claude Code, Python) at our direction;
all prompts are documented in the prompt log submitted with the code. {BEYOND} marks methods that go beyond the course.</p></div>
"""

flow_rows = [[str(r.year), f"{r.metro_county_years:,}", f"{r.no_price:,}", f"{r.price_but_no_wage:,}", f"{r.price_wage_but_missing_acs:,}",
              f"<b>{r.analysis_dataset:,}</b>", f"{r.share_kept_pct:.1f}%"] for r in flow.itertuples()]
flow_rows.append(["<b>Total</b>", f"<b>{flow.metro_county_years.sum():,}</b>", f"{flow.no_price.sum():,}", f"{flow.price_but_no_wage.sum():,}",
                  f"{flow.price_wage_but_missing_acs.sum():,}", f"<b>{flow.analysis_dataset.sum():,}</b>",
                  f"{flow.analysis_dataset.sum() / flow.metro_county_years.sum() * 100:.1f}%"])
# ================================================================== PART I: PRE-ANALYSIS (tasks 1-4) ==========================
import re  # noqa: E402

import statsmodels.api as sm  # noqa: E402

desc = rd("pre_t2_descriptives_2022.csv")
fits = rd("pre_t3_fits.csv").set_index("x")
st = (ROOT / "output/project/student_texts_project.md").read_text(encoding="utf-8")
sec = dict(re.findall(r"## (Pre-analysis task \d: [^\n]+)\n\n(.+?)(?=\n\n## |\Z)", st, flags=re.S))


def team_text(text):
    """Team's own words, unchanged except typographic R² (the AI corrected spelling and grammar only, on request)."""
    text = text.strip().replace("R2", "R²")
    out = []
    for para in text.split("\n\n"):
        lines = para.split("\n")
        if len(lines) > 1 and len(lines[0]) < 40:  # short first line = sub-heading in the team's text
            out.append(f"<p><b>{lines[0]}</b><br>{' '.join(lines[1:])}</p>")
        else:
            out.append("<p>" + "<br>".join(lines) + "</p>")
    return "".join(out)


def team_box(label, text):
    return f"<div class='box team'><div class='boxlabel'>{label}</div>{team_text(text)}</div>"


mreg = reg[reg.se_type == "metro"].set_index(["spec", "term"])
oreg = reg[reg.se_type == "OLS"].set_index(["spec", "term"])
sreg = reg[reg.se_type == "state"].set_index(["spec", "term"])
SPECS = ["(a) wage", "(b) rent", "(c) wage + rent"]
cell = lambda sp, t: (f"{mreg.loc[(sp, t)].coef:.3f}".replace("-", "−") + f" <span class='se'>({mreg.loc[(sp, t)].se:.3f})</span>" if (sp, t) in mreg.index else "–")
p4rows = [[lab] + [cell(sp, t) for sp in SPECS] for lab, t in
          [("Wage (per $1,000/year)", "wage_k"), ("Rent (per $100/month)", "rent_100"), ("Intercept", "const")]]
p4rows += [["R²"] + [f"{mreg.xs(sp).r2.iloc[0]:.3f}" for sp in SPECS],
           ["Residual SD ($/week)"] + [f"{mreg.xs(sp).resid_sd.iloc[0]:.2f}" for sp in SPECS],
           ["N (metro clusters)"] + [f"{int(mreg.xs(sp).n.iloc[0]):,} ({d22.oews_area.nunique()})" for sp in SPECS]]
serows = [[lab, f"{oreg.loc[(sp, t)].se:.3f}", f"<b>{mreg.loc[(sp, t)].se:.3f}</b>", f"{sreg.loc[(sp, t)].se:.3f}", f"{sreg.loc[(sp, t)].p:.1e}"]
          for lab, sp, t in [("(a) wage alone", "(a) wage", "wage_k"), ("(b) rent alone", "(b) rent", "rent_100"),
                             ("(c) wage, rent held constant", "(c) wage + rent", "wage_k"), ("(c) rent, wage held constant", "(c) wage + rent", "rent_100")]]
bw, br = mreg.loc[("(c) wage + rent", "wage_k")].coef, mreg.loc[("(c) wage + rent", "rent_100")].coef
ba, bb = mreg.loc[("(a) wage", "wage_k")].coef, mreg.loc[("(b) rent", "rent_100")].coef
w_k, r_h = d22.childcare_wage_real2022 / 1000, d22.median_gross_rent_real2022 / 100
dl_rw = sm.OLS(r_h, sm.add_constant(w_k)).fit().params.iloc[1]
dl_wr = sm.OLS(w_k, sm.add_constant(r_h)).fit().params.iloc[1]
corr_wr = d22.childcare_wage_real2022.corr(d22.median_gross_rent_real2022)
iqr_w = bw * (w_k.quantile(.75) - w_k.quantile(.25))
iqr_r = br * (r_h.quantile(.75) - r_h.quantile(.25))


def dfmt(r):
    if r.variable.endswith("share"):
        return f"{r['mean']:.4f}", f"{r.sd:.4f}"
    return f"{r['mean']:,.2f}", f"{r.sd:,.2f}"


drows, dhl, grp = [], [], None
for _, r in desc.iterrows():
    if r.group != grp:
        dhl.append(len(drows))
        drows.append([r.group, "", "", "", ""])
        grp = r.group
    mn, sd = dfmt(r)
    drows.append([r.label, mn, sd, f"{int(r.n):,}", f"<span class='se'>{r.source}</span>"])
fw, fr = fits.loc["childcare_wage_real2022"], fits.loc["median_gross_rent_real2022"]
n_all8 = int((a.groupby("fips").year.nunique() == 8).sum())

partP = section("P", "Pre-analysis: prices and costs (tasks 1–4)", "slide 2 · model “c”").replace("Appendix P", "Pre-analysis") + f"""
{box("idea", "Our idea", "<p>Before searching for markets, establish how strongly childcare prices move with the two main costs of a center, "
     "staff wages and rent. The resulting model “c” is the starting point of our selection (Appendix B).</p>")}
<h3>Task 1. The analysis dataset</h3>
<p class='task'><b>Task.</b> Merge NDCP county prices to the year × county cost/demand file from Problem Set 5, then define the analysis dataset as
year × county observations where prices and predictor variables are non-missing.</p>
<ul>
<li><b>Merge:</b> NDCP prices joined to the Problem Set 5 cost/demand panel on [year, 5-digit county FIPS], one-to-one. Both files use the same metro
sample (OEWS area code starting with 00), so all {flow.metro_county_years.sum():,} metro county-years matched.</li>
<li><b>Definition:</b> county-years with the center-based preschool price and all 10 predictors non-missing (wage, rent, per-capita income, population,
children under 6, children under 6 whose resident parents all work, female college share, female full-time year-round share, under-6 share,
care-need share). Requiring only price, wage and rent gives the identical sample in every year, so the definition does not depend on which predictors
are counted. All regressions use this one sample.</li>
<li><b>Result:</b> <b>{len(a):,} county-years</b> of {a.fips.nunique():,} counties ({n_all8} of them in all eight years); <b>2022: {len(d22)} counties</b> in
{d22.oews_area.nunique()} metro areas and {d22.state_abbr.nunique()} states including DC.</li>
</ul>
{tbl(["Year", "Metro county-years", "No NDCP price", "Price, no wage", "Missing ACS", "Analysis dataset", "Kept"], flow_rows,
     widths=["10%", "16%", "15%", "14%", "14%", "17%", "14%"], cls="small")}
<p class='note'>Missing NDCP prices are the main reason for exclusion and are concentrated in a few states (2022: Puerto Rico, Indiana, Pennsylvania,
Missouri, Arkansas). In 2021 NDCP has no prices for CA, NC, PA and VA. Missing ACS in 2022: the Connecticut counties (planning-region change).</p>
</div>
<div class='section'>
<h3 style='margin-top:0'>Task 2. Descriptive statistics, 2022</h3>
<p class='task'><b>Task.</b> Make a table of mean / SD / number of observations for all variables in the analysis dataset for 2022.</p>
{tbl(["Variable (2022, metro counties, 2022 $)", "Mean", "SD", "N", "Source"], drows, align=["l", "r", "r", "r", "l"],
     widths=["43%", "13%", "13%", "8%", "23%"], cls="small", hl=tuple(dhl))}
<p class='note'>Unweighted county statistics. Infant and toddler prices are shown for context (not part of the complete-case definition). The sample
excludes counties without NDCP prices, mainly lower-cost areas (no Puerto Rico counties remain), so cost and income means are above those for all
metro counties (Problem Set 5: wage $27,373, rent $1,052).</p>
</div>
<div class='section'>
<h3 style='margin-top:0'>Task 3. Prices vs. wages and rents</h3>
<p class='task'><b>Task.</b> Make scatter plots of childcare prices against (a) childcare-worker wages and (b) rents, with the fitted line from a linear
regression. How do you interpret these?</p>
{fig("app_P3_scatter.png", f"Figure P1. Center-based preschool price vs. costs, 2022, N = {len(d22)} metro counties; line = OLS fit. Vertical clusters in (a): "
     "all counties of a metro area share one OEWS wage but have different NDCP prices.")}
{tbl(["Bivariate OLS, 2022", "Fitted line", "Slope (readable units)", "R²", "Correlation"], [
    ["(a) Wage", f"−{abs(fw.intercept):.2f} + {fw.slope:.5f} × wage", f"+${fw.slope_scaled:.2f}/week per $1,000", f"{fw.r2:.3f}", f"{fw['corr']:.3f}"],
    ["(b) Rent", f"{fr.intercept:.2f} + {fr.slope:.4f} × rent", f"+${fr.slope_scaled:.2f}/week per $100", f"{fr.r2:.3f}", f"{fr['corr']:.3f}"]],
    widths=["18%", "30%", "26%", "12%", "14%"], cls="small")}
{team_box("Team interpretation · task 3", sec["Pre-analysis task 3: Interpretation of the scatter plots"])}
</div>
<div class='section'>
<h3 style='margin-top:0'>Task 4. Multivariate regression</h3>
<p class='task'><b>Task.</b> Using 2022 data, regress median preschool price on (a) wages alone, (b) rent alone, and (c) wages and rent together.
Interpret the coefficients in each, and explain any changes in the wage/rent coefficients between the univariate and multivariate specifications.</p>
{box("decision", "Team decisions · task 4 (paraphrased from team notes)", "<ul><li><b>Readable units:</b> price in $/week, wage per $1,000 of annual wage, rent per $100 of monthly rent (2022 $).</li>"
     "<li><b>Standard errors clustered by metro area,</b> for the same reason as in Problem Set 5 (task 7): counties in one metro area share one OEWS wage, "
     "so they are not independent observations.</li></ul>")}
<p><b>Model “c”:</b> Price<sub>i</sub> = a + b<sub>1</sub>·Wage<sub>i</sub> + b<sub>2</sub>·Rent<sub>i</sub> + e<sub>i</sub></p>
{tbl(["Dependent variable: preschool price ($/week)", "(a) Wage", "(b) Rent", "(c) Wage + rent"], p4rows,
     widths=["37%", "21%", "21%", "21%"], cls="small", hl=(0, 1))}
<p class='note'>Standard errors in parentheses, clustered by metro area. All slope coefficients p &lt; 0.0001. The same {len(d22)} counties in all three models.</p>
{fig("app_P4_coefficients.png", "Figure P2. Cost coefficients alone (open) and together (filled), 2022, with 95% confidence intervals.")}
<p><b>Omitted-variable decomposition (exact).</b> Rent rises on average by {dl_rw:.3f} × $100 per $1,000 of wage, and wage by {dl_wr:.3f} × $1,000 per
$100 of rent (r = {corr_wr:.2f}). Hence b<sub>wage</sub>(a) = {bw:.3f} + {br:.3f} × {dl_rw:.3f} = <b>{bw + br * dl_rw:.3f}</b> and
b<sub>rent</sub>(b) = {br:.3f} + {bw:.3f} × {dl_wr:.3f} = <b>{br + bw * dl_wr:.3f}</b>, exactly the single-regression coefficients. Holding rent constant, moving
a county from the 25th to the 75th percentile of wages raises the predicted price by ${iqr_w:.2f}/week; the same move in rent adds ${iqr_r:.2f}/week.
The intercepts are not interpretable on their own (a wage or rent of $0 is far outside the data).</p>
{tbl(["Robustness: SE of the slope", "OLS", "Metro-clustered (used)", "State-clustered", "p, state-clustered"], serows,
     widths=["34%", "14%", "20%", "16%", "16%"], cls="small")}
{team_box("Team interpretation · task 4", sec["Pre-analysis task 4: Interpretation of the regressions"])}
</div>"""

# ================================================================== PART 0: ideas =========================================
IDEAS = [
    ("Find counties where prices are unusually high relative to costs (wages and rent).",
     "Cost model: predict each county's price from its childcare-worker wage and rent, within its state; premium = actual vs. predicted price.",
     "NDCP prices, BLS OEWS wages, ACS rents, 2015–2022", "B, C"),
    ("The advantage must have lasted over time.",
     "Rank on the average premium over all observed years (≥ 5); require a positive premium in every year; measure how much of a premium survives.",
     "Yearly premiums 2015–2022; direct NDCP survey years", "D"),
    ("Prioritize places with strong childcare demand.",
     f"Market-size filter (≥ {thr:,.0f} children under 6 whose parents all work) and a demand score (children needing care, their share of the population, income).",
     "ACS 5-year 2022", "D"),
    ("Start with a top 20, then add factors to get to the top 10.",
     "Candidate pool = 20 largest average premiums; then persistence, market size and the score.",
     "Selection rule, Appendix D", "D"),
    ("Test the approach with historical data to build the best predictive model.",
     "Out-of-sample validation of the cost model; backtest of the complete rule as if decided in 2018; robustness to each design choice.",
     "2015–2018 → 2022; 2015–2020 → 2022", "C, E"),
    ("Look beyond the model before investing.",
     "Five local risk checks: competition, child-population trend, wage and rent growth, free public pre-K.",
     "Census CBP 2022; ACS; OEWS; state/county pre-K rules", "F"),
]
part0 = section("0", "From our ideas to measurable steps", "") + f"""
<p>Our selection follows six guiding ideas the team set at the start of the project. The table shows how each idea was turned
into a measurable step, which data it uses, and where the evidence is.</p>
{tbl(["Our idea", "How we measured it", "Data", "App."], [[f"<b>{i}</b>", m, d, s] for i, m, d, s in IDEAS],
     align=["l", "l", "l", "c"], widths=["27%", "43%", "22%", "8%"])}
<h3>Which years enter which analysis</h3>
<p>The rule never uses information from after the year it is tested on: the backtest decides with 2015–2018 data only and is judged
on 2022; the validation of the cost model fits 2015–2020 and predicts 2022.</p>
{fig("app_A_timeline.png", "Figure 0.1. Years used by each analysis. Market size and demand use the 2022 ACS 5-year estimates (survey years 2018–2022).")}
</div>"""

# ================================================================== A: data ===============================================
src_rows = [
    ["<b>National Database of Childcare Prices (NDCP)</b>, U.S. Department of Labor", "Median weekly full-time price of center-based preschool care (MCPRESCHOOL), imputation codes", "County", "2015–2022"],
    ["<b>Occupational Employment and Wage Statistics (OEWS)</b>, BLS", "Mean annual wage of childcare workers (SOC 39-9011); preschool teachers (25-2011) for robustness", "Metro area → its counties", "2015–2022"],
    ["<b>American Community Survey 5-year (ACS)</b>, Census API", "Median gross rent, children under 6, children whose resident parents all work, population, per-capita income", "County", "2015–2022"],
    ["<b>CPI-U</b> (CUUR0000SA0), BLS", "Annual average; converts all dollar values to 2022 dollars", "U.S.", "2015–2022"],
    ["<b>County–OEWS crosswalk</b>, course package", "Year-specific link of counties to OEWS areas; metro = area code starting with 00", "County", "2015–2022"],
    ["<b>County Business Patterns (CBP)</b>, Census API", "Child day care establishments and employees (NAICS 624410)", "County", "2016, 2019, 2022"],
    ["<b>Gazetteer and cartographic boundaries</b>, Census", "County internal points, state and county outlines (maps only)", "County", "2022"],
    ["<b>Public pre-K program rules</b>, state and county agencies", "Eligibility and scope of free public pre-K (sources in Appendix F)", "County / state", "accessed Oct 2026"],
]
var_rows = [
    ["Price", "NDCP MCPRESCHOOL × CPI factor", "$/week, 2022 $", "Cost model (dependent variable)"],
    ["Childcare-worker wage", "OEWS A_MEAN, SOC 39-9011, metro area", "$/year, 2022 $", "Cost model"],
    ["Rent", "ACS B25064_001E median gross rent", "$/month, 2022 $", "Cost model"],
    ["Children needing care", "ACS B23008_004E + 010E + 013E (under 6, all resident parents in the labor force)", "children", "Market-size filter, demand score"],
    ["Care-need share", "children needing care / ACS B01001_001E population", "share", "Demand score"],
    ["Income per capita", "ACS B19301_001E", "$/year, 2022 $", "Demand score"],
    ["Premium (within state)", "exp(residual) − 1 of the final cost model, per year", "%", "Selection, stability"],
    ["National premium", "same model without state effects", "%", "Robustness filter (> 0)"],
    ["Direct survey year", "5th digit of the NDCP imputation code = 0 (not interpolated)", "flag", "Survey-only persistence, data quality"],
    ["Center density", "CBP establishments per 1,000 children needing care", "per 1,000", "Risk check (competition)"],
]
HANDLING = [
    ["Metro sample", "County-year is metro if its OEWS area code in the year-specific crosswalk starts with 00", "Assignment definition; wages exist for metro areas", f"{panel.fips.nunique():,} counties, {len(panel):,} county-years"],
    ["Wage geography", "Every county gets the OEWS wage of its metro area", "OEWS publishes no county wages", "Counties of one metro share a wage → SEs clustered by metro area"],
    ["Large metros 2015–2017", "Use BLS whole-MSA files (aMSA); metropolitan divisions not used", "Crosswalk uses whole-MSA codes", "No wage gaps for the 11 largest metros"],
    ["Legacy FIPS", "Drop 12025 (Dade) and 51515 (Bedford city)", "No longer counties; successors are in the crosswalk", "Identical county set across sources"],
    ["Connecticut 2022", "No ACS values for the 8 old counties (ACS 2022 reports planning regions)", "Geographies not comparable", "CT drops out in 2022"],
    ["Real dollars", "All $ × CPI-U annual average factor to 2022", "Compare years", "Prices, wages, rents, income in 2022 $"],
    ["Complete cases", "Keep county-years with price and all predictors non-missing", "One consistent sample for every model", f"{len(a):,} county-years, {a.fips.nunique():,} counties"],
    ["NDCP gaps", "2021: no prices for CA, NC, PA, VA; years kept as missing, not filled", "Avoid inventing data", "Those counties have 7 of 8 years"],
    ["CA/VA 2022 prices", f"Kept, but selection uses the 2015–2022 average, not 2022 alone", f"NDCP extrapolated them (no 2022 survey); nominal change vs. 2020: SF {pc(chg('06075'))}, Marin {pc(chg('06041'))}, Los Angeles {pc(chg('06037'))}, Arlington {pc(chg('51013'))}, Fairfax {pc(chg('51059'))} ", "Team decision D2"],
    ["Candidates need a 2022 price", "Pool drawn from counties in the 2022 sample", "Current market evidence; demand measured in 2022", f"{len(excl)} counties without 2022 price would otherwise enter (App. D)"],
    ["Identifiers", "FIPS, OEWS codes and imputation codes stored as text", "Keep leading zeros", "Exact joins"],
    ["Raw data", "Never edited; SHA-256 checksums of all downloaded files", "Reproducibility", "data/raw_checksums.sha256"],
]
partA = section("A", "Data sources, samples and data handling", "all slides") + f"""
{box("idea", "Our idea", "<p>Use only official, county-level public data that a provider could also use, keep one consistent sample for every model, "
     "and document every choice that changes which observations enter.</p>")}
<h3>A1. Sources</h3>
{tbl(["Source", "What we use", "Geography", "Years"], src_rows, align=["l", "l", "l", "l"], widths=["30%", "44%", "14%", "12%"], cls="small")}
<h3>A2. Variables</h3>
{tbl(["Variable", "Definition and source code", "Unit", "Used for"], var_rows, align=["l", "l", "l", "l"], widths=["19%", "43%", "13%", "25%"], cls="small")}
<h3>A3. Samples</h3>
<p><b>Analysis dataset</b> (pre-analysis task 1): {len(a):,} metro county-years with the preschool price and all predictors non-missing;
sample flow by year in Task 1.</p>
<p><b>Selection sample.</b> Of the {n_all:,} counties with at least one year in the analysis dataset, {len(d22):,} are in the 2022 data,
{n22_5:,} of these are observed in at least 5 of the 8 years, and {n22_5nat:,} of those also have a positive average national premium.
These are the counties eligible for the candidate pool (Appendix D). The 2022 cross-section has {len(d22)} counties in
{d22.oews_area.nunique()} metro areas and {d22.state_abbr.nunique()} states including DC.</p>
<h3>A4. Data-handling decisions</h3>
{tbl(["Issue", "What we did", "Why", "Effect"], HANDLING, align=["l", "l", "l", "l"], widths=["16%", "33%", "27%", "24%"], cls="small")}
</div>"""

# ================================================================== B: cost model =========================================
mrows = []
for k in ["L", "LL", "LS", "LLS"]:
    r = models.loc[k]
    unit = "$/week, levels" if k in ("L", "LS") else "elasticity"
    mrows.append([r.label, unit, f"{r.wage:.3f} <span class='se'>({r.wage_se:.3f})</span>", f"{r.rent:.3f} <span class='se'>({r.rent_se:.3f})</span>",
                  "yes" if r.n_state_dummies else "–", f"{r.r2:.3f}", f"{r.n:,}"])
yrows = [[str(r.year), f"{r.n:,}", str(r.states), f"{r.wage_el:.2f} <span class='se'>({r.wage_se:.2f})</span>",
          f"{r.rent_el:.2f} <span class='se'>({r.rent_se:.2f})</span>", f"{r.r2:.2f}", f"{r.r2_model_c:.2f}", f"{r.resid_sd:.3f}"]
         for r in yearly.itertuples()]
lls = models.loc["LLS"]
partB = section("B", "The cost model: from model “c” to our prediction", "slide 2") + f"""
{box("idea", "Our idea", "<p>If wages and rents explain what childcare <i>should</i> cost in a county, then a county where parents pay far more than "
     "that has pricing power: willingness to pay that local costs do not explain. That gap is the premium we look for.</p>")}
<h3>B1. Starting point: model “c” from the pre-analysis</h3>
<p>Price = −{abs(c_.loc['const', 'coef']):.2f} + {c_.loc['wage_k', 'coef']:.3f}·wage + {c_.loc['rent_100', 'coef']:.3f}·rent
(2022, N = 998, price in $/week, wage per $1,000/year, rent per $100/month; SEs clustered by metro area:
{c_.loc['wage_k', 'se']:.3f} and {c_.loc['rent_100', 'se']:.3f}; R² {c_.r2.iloc[0]:.3f}). Alone, wage has a slope of {ra.loc['wage_k', 'coef']:.3f}
and rent {rb.loc['rent_100', 'coef']:.3f}; both shrink together because wages and rents are correlated (omitted-variable bias,
pre-analysis task 4). Model “c” already explains {c_.r2.iloc[0]:.0%} of price differences, but three features of the data argue for refining it:</p>
<ol>
<li><b>States set price levels.</b> NDCP prices come from state market-rate surveys, often reported by rate zones: the {len(wi)}
Wisconsin counties in 2022 have only {wi.price_preschool_real2022.nunique()} distinct prices. States also differ in staffing ratios and licensing
rules that we do not observe. A national model therefore mostly finds “expensive states”, not expensive markets.</li>
<li><b>The scatter fans out.</b> Price differences grow with the price level, so a $50 gap means much more in Tennessee than in San Francisco.
A model in logs measures the gap in percent and fits this pattern.</li>
<li><b>Interpretation.</b> In logs the coefficients are elasticities: +10% wage → +{(1.1 ** lls.wage - 1) * 100:.1f}% price; +10% rent → +{(1.1 ** lls.rent - 1) * 100:.1f}% price.</li>
</ol>
<h3>B2. Four candidate models, 2022</h3>
{tbl(["Model", "Units", "Wage", "Rent", "State effects", "R²", "N"], mrows, align=["l", "l", "r", "r", "c", "r", "r"], widths=["30%", "14%", "15%", "15%", "10%", "8%", "8%"], hl=(3,))}
<p class='note'>SEs (in parentheses) clustered by metro area, because counties in one metro area share one OEWS wage. State effects: {int(lls.n_state_dummies)}
dummies (44 states incl. DC). With state effects, the wage coefficient falls (2.08 vs. 7.09 in levels): part of the wage effect in model “c” was a
state effect. Out-of-sample comparison of all four models: Appendix C.</p>
{fig("app_B_models.png", "Figure B1. Actual vs. predicted weekly price, 2022 (numbers = our ranks). Above the line, parents pay more than costs justify. "
     "In model “c”, Hall (9) and Sullivan (10) look ordinary; compared within their own states, all ten lie clearly above the line.")}
{box("decision", "Team decision D1 · premium measure", f"<p><b>Final model</b> (estimated separately for each year 2015–2022): "
     f"log(price) = a + b₁·log(wage) + b₂·log(rent) + state effects. <b>Premium</b> = exp(residual) − 1, i.e. the % by which the actual price exceeds "
     f"the price predicted for a county with the same wage and rent <i>in the same state</i>. As a robustness requirement, the county's average "
     f"national premium (same model without state effects) must also be positive, so that we do not pick counties that are merely pricey for a cheap state.</p>")}
<h3>B3. Worked example: Hall County, GA (rank 9), 2022</h3>
<p>Parents pay <b>${hall.price_preschool_real2022:.0f}/week</b>. Model “c” predicts ${hall_c:.0f} (+{(hall.price_preschool_real2022 / hall_c - 1) * 100:.0f}%,
an ordinary market). Compared within Georgia, the final model predicts <b>${hall_f:.0f}</b>, so Hall has a premium of
<b>+{(hall.price_preschool_real2022 / hall_f - 1) * 100:.0f}%</b>: Georgia's prices are low overall, and Hall is expensive for Georgia.</p>
</div>
<div class='section'>
<h3 style='margin-top:0'>B4. Is the cost model stable over time?</h3>
<p>The final model is fitted separately for each year, so each year's premium is measured against that year's cost relationship. The
coefficients are stable: the wage elasticity stays between {yearly.wage_el.min():.2f} and {yearly.wage_el.max():.2f}, the rent elasticity between
{yearly.rent_el.min():.2f} and {yearly.rent_el.max():.2f}, and R² between {yearly.r2.min():.2f} and {yearly.r2.max():.2f} (model “c”:
{yearly.r2_model_c.min():.2f}–{yearly.r2_model_c.max():.2f}).</p>
{fig("app_B_yearly.png", "Figure B2. Final model by year: elasticities with 95% CIs (SEs clustered by metro area) and R² vs. model “c”. "
     "2021 has fewer observations (no NDCP prices for CA, NC, PA, VA).")}
{tbl(["Year", "N", "States", "Wage elast.", "Rent elast.", "R² final", "R² model “c”", "Resid. SD (log)"], yrows,
     widths=["10%", "9%", "9%", "16%", "16%", "12%", "14%", "14%"], cls="small")}
<h3>B5. Fit and residuals</h3>
{stats_row([(f"{diag['r2']:.0%}", "of 2022 price variation explained"), (f"±{(np.exp(diag['resid_sd_log']) - 1) * 100:.0f}%", "typical miss (1 residual SD = "
            f"{diag['resid_sd_log']:.3f} log points)"), (f"{diag['n_above_95pi_all']:.0f}", f"of 998 counties above the 95% prediction band ({diag['share_above_95pi_all'] * 100:.1f}%)"),
            (f"p &lt; 0.001", "Breusch–Pagan test: heteroskedasticity")])}
{fig("app_B_residuals.png", "Figure B3. Residuals of the final model, 2022 (blue = top 10). Shaded band: ±1.96 residual SD (approximate; the count of counties above the 95% band uses the exact prediction interval).")}
<ul>
<li><b>No systematic pattern:</b> residuals are centered on zero across the range of fitted prices (correlation with fitted values = 0 by construction,
and no visible curvature). Mean residuals are close to zero in every county-size quartile.</li>
<li><b>Shape:</b> close to normal (skewness {diag['resid_skew']:.2f}, excess kurtosis {diag['resid_kurtosis']:.2f}); the Q–Q plot departs from the line only
in the upper tail, which is exactly where our top 10 lie. These are real outliers in the sense that interests us, not a misfit of the bulk.</li>
<li><b>Heteroskedasticity:</b> the Breusch–Pagan test rejects constant variance (p = {diag['breusch_pagan_p']:.1e}). We therefore use standard errors
clustered by metro area throughout, which are robust to unequal variance and to shared wages within a metro area.</li>
<li><b>What the residual contains:</b> 19% of price variation is not explained by wages, rents and states. It contains willingness to pay (our signal),
but also quality differences, local regulation, unobserved costs and NDCP measurement error (our noise). Two features of our rule keep noise
from driving the result: we average the premium over up to eight years, and we require it to be positive in every year (Appendix D).</li>
<li><b>Demand variables are deliberately not in the cost model.</b> Including income or children would explain part of the premium away; we use
them afterwards to choose among counties with a premium.</li>
</ul>
</div>"""

# ================================================================== C: validation =========================================
vt = val.set_index(["model", "validation"])
TV, CV = "temporal: train 2015-2020, test 2022", "2022, 10-fold CV grouped by metro area"
LAB = {"L": "Model “c”: level", "LL": "Log-log", "LS": "Level + state effects", "LLS": "Log-log + state effects (final)"}
vrows = [[LAB[k], f"{vt.loc[(k, TV)].in_sample_r2:.3f}", f"${vt.loc[(k, TV)].rmse:.2f}", f"${vt.loc[(k, TV)].mae:.2f}",
          f"${vt.loc[(k, CV)].rmse:.2f}", f"${vt.loc[(k, CV)].mae:.2f}"] for k in ["L", "LL", "LS", "LLS"]]
drop_t = (1 - vt.loc[("LLS", TV)].rmse / vt.loc[("L", TV)].rmse) * 100
drop_c = (1 - vt.loc[("LLS", CV)].rmse / vt.loc[("L", CV)].rmse) * 100
partC = section("C", "Does the cost model predict prices it has not seen?", "slide 2") + f"""
{box("idea", "Our idea", "<p>A model that only fits the data it was estimated on could be over-fitted. We want “the best predictive model possible”, "
     "so we judged the candidates by how well they predict prices they have never seen.</p>")}
<p>{BEYOND} R² measures fit on the estimation sample. Out-of-sample tests hold data back, fit the model on the rest, and measure the typical
error on the held-back prices (root mean squared error, RMSE, and mean absolute error, MAE, in $/week):</p>
<ul><li><b>New year:</b> fit on 2015–2020 (pooled, with year effects), predict every county's 2022 price (N = {int(vt.loc[('L', TV)].n_test)}).</li>
<li><b>New metro areas:</b> 2022, ten-fold cross-validation in which all counties of a metro area are always held out together, so the model never
sees a county's neighbors or its shared wage (N = {int(vt.loc[('L', CV)].n_test)}).</li></ul>
{tbl(["Model", "R² (2015–20 fit)", "RMSE new year", "MAE new year", "RMSE new metros", "MAE new metros"], vrows,
     widths=["32%", "13%", "14%", "13%", "14%", "14%"], hl=(3,))}
{stats_row([(f"−{drop_t:.0f}%", "forecast error for a new year vs. model “c”"), (f"−{drop_c:.0f}%", "error for unseen metro areas vs. model “c”"),
            ("State effects", "drive the gain; logs alone do not"), ("LLS ≈ LS", "similar accuracy; logs give % premiums")])}
<p><b>Reading.</b> Adding state effects reduces the out-of-sample error by about a sixth in both tests; taking logs alone does not. The level and log
models with state effects predict about equally well, so we chose the log version (D1) because it measures premiums in percent, comparable
between cheap and expensive markets. Both errors refer to prices; the premium of a county is its prediction error by design, so a model that
predicts well in general makes a large, persistent residual more meaningful.</p>
</div>"""

# ================================================================== D: selection & stability =================================
DEC = [
    ["P1", "Readable units: price $/week, wage per $1,000/year, rent per $100/month", "Raw dollar units", "Coefficients that non-statisticians can read (pre-analysis)"],
    ["P2", "Standard errors clustered by metro area", "OLS, state clusters", "Counties in one metro share one OEWS wage; not independent"],
    ["D1", "Within-state log premium (final model); national premium > 0 as robustness", "Model “c” residual; national log model", "State effects cut out-of-sample error by 14–19% (App. C); logs give % premiums, comparable across markets"],
    ["D2", "Rank on the average premium 2015–2022 (≥ 5 years), not on 2022 alone", "2022 premium only", "Goal is a lasting advantage; CA/VA 2022 prices are extrapolations (App. A)"],
    ["D3", "Premium positive in every observed year", "One weak year allowed", "The advantage must have lasted"],
    ["D4", f"Market size ≥ median children needing care ({thr:,.0f})", "25th percentile; no filter", "A high premium in a tiny market cannot fill a center"],
    ["D5", "Score = 50% premium rank + 50% demand rank, both among the finalists", "70/30, 30/70; ranks vs. all counties", "Our ideas weigh price advantage and demand equally; same scale so weights are real"],
    ["D6", "No cap per metro area", "Max. one or two per metro", "Neighboring counties are separate local markets; we want the best counties"],
    ["D7", "Unweighted cost model", "Weighted by children (WLS)", "Every county is one market; size enters through D4 and D5"],
    ["D8", "Plan with the expected premium (after typical fading)", "Use today's premium", "Premiums fade partially (D-stability below)"],
]
crow = []
for r in cand.itertuples():
    ok = r.pass_persistence and r.pass_market
    crow.append([str(r.pool_rank), f"{r.county_name}, {r.state_abbr}", pc(r.mean_prem), pc(r.mean_nat), pc(r.min_prem),
                 f"{r.years_positive}/{r.n_years}", f"{r.kids_under6_allpar_lf:,.0f}",
                 "✓" if r.pass_persistence else "✕", "✓" if r.pass_market else "✕", f"<b>{int(r.final_rank)}</b>" if ok else "–"])
sc = rd("fp_candidates_scored.csv", dtype={"fips": str})
demd = rd("app_demand_premium.csv")
dcor = rd("app_demand_correlations.csv", index_col=0)
star = lambda pv: "**" if pv < 0.01 else ("*" if pv < 0.05 else "")
dem_rows = []
for var in ["Children needing care (log)", "Care-need share", "Income per capita (log)", "Female college share", "Female full-time share",
            "R² (with state effects) / N"]:
    cells = [var]
    for mname in ["Used in the score", "+ the two unused ACS shares"]:
        r_ = demd[(demd.model == mname) & (demd.variable == var)]
        if r_.empty:
            cells.append("–")
        elif var.startswith("R²"):
            cells.append(f"{r_.coef_pct_per_sd.iloc[0]:.3f}")
        else:
            v_ = r_.coef_pct_per_sd.iloc[0]
            cells.append(f"{pc(0 if abs(v_) < 0.05 else v_, 1) if abs(v_) >= 0.05 else '0.0%'}{star(r_.p.iloc[0])} "
                         f"<span class='se'>({r_.se_log.iloc[0]:.3f})</span>")
    dem_rows.append(cells)
for col in ["kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022"]:
    sc["r_" + col] = sc[col].rank(pct=True)
srows = [[str(r.rank), f"{r.county_name.replace(' County', '').replace(' City', '')}, {r.state_abbr}", pc(r.mean_premium_LLS_pct), f"{r.premium_strength:.2f}",
          f"{r.r_kids_under6_allpar_lf:.2f}", f"{r.r_under6_careneed_share:.2f}", f"{r.r_per_capita_income_real2022:.2f}", f"{r.demand_index:.2f}",
          f"<b>{r.score:.2f}</b>"] for r in sc.itertuples()]
prow = [[r.model.replace("premium_", "").replace(" on ", " on "), f"{r.n:,}", f"{r.slope:.2f}", f"{r.se_state_cluster:.2f}", f"{r.r2:.2f}"]
        for r in persist.itertuples() if r.model.startswith("premium_2022")]
qrows = [[str(y), f"{int(quint.loc[y, 'n_top_quintile'])}", pc(quint.loc[y, "share_still_top_quintile_2022"] * 100, sign=False),
          pc(quint.loc[y, "share_still_above_median_2022"] * 100, sign=False), pc(quint.loc[y, "share_positive_premium_2022"] * 100, sign=False)]
         for y in quint.index]
qrows.append(["If premiums were random", "–", "20%", "50%", "≈ 50%"])
erows = [[str(r.rank), SHORT[r.fips], pc(avg_arith[r.fips]), pc(r.avg_premium_pct), f"<b>{pc(r.expected_premium_pct)}</b>",
          f"[{r.expected_low_pct:+.0f}%, {r.expected_high_pct:+.0f}%]"] for r in exp_.sort_values("rank").itertuples()]
lo, hi = sv["slope"] - 1.96 * sv["se"], sv["slope"] + 1.96 * sv["se"]
partD = section("D", "Team decisions, the selection rule, and stability over time", "slides 3 and 5") + f"""
{box("idea", "Our idea", "<p>Start broad, then narrow down: take the 20 counties with the largest lasting price advantage, keep those whose "
     "advantage held every year and whose market is big enough, and rank the rest by price advantage and demand together.</p>")}
<h3>D1. Team decisions</h3>
<p>Each decision was taken by the team after the options and the evidence were laid out (the prompts are in the prompt log).</p>
{tbl(["#", "Decision", "Alternatives considered", "Why"], DEC, align=["c", "l", "l", "l"], widths=["6%", "36%", "22%", "36%"], cls="small")}
<h3>D2. The rule, step by step</h3>
{tbl(["Step", "Counties", "Criterion", "Data"], [
    ["Metro counties with price, wage and rent", f"{n_all:,}", "In the analysis dataset at least once", "NDCP × OEWS × ACS, 2015–2022"],
    ["Eligible", f"{n22_5:,}", "In the 2022 data and observed in ≥ 5 of 8 years", "Current price + enough history"],
    ["Positive nationally", f"{n22_5nat:,}", "Average national premium > 0", "Same model without state effects"],
    ["Candidate pool", "20", "Largest average within-state premium", "Mean of yearly premiums"],
    ["Persistence", f"{int(cand.pass_persistence.sum())}", "Premium > 0 in every observed year", "Yearly premiums"],
    ["Market size", f"{int((cand.pass_persistence & cand.pass_market).sum())}", f"≥ {thr:,.0f} children needing care (2022 median)", "ACS 2022"],
    ["Top 10", "10", "Ordered by the score (removes none)", "50% premium + 50% demand rank"]],
    align=["l", "r", "l", "l"], widths=["26%", "10%", "36%", "28%"])}
<h3>D3. The candidate pool</h3>
{tbl(["#", "County", "Avg. premium", "Avg. national", "Weakest year", "Years > 0", "Children needing care", "Persist.", "Market", "Final rank"], crow,
     align=["c", "l", "r", "r", "r", "c", "r", "c", "c", "c"], widths=["5%", "21%", "10%", "10%", "10%", "8%", "12%", "8%", "8%", "8%"], cls="small")}
<p class='note'>All 20 candidates pass the persistence test; the ten that drop out fail only the market-size test (e.g. Falls Church City, VA,
and Manassas Park City, VA, are too small). Not eligible because NDCP has no 2022 price for their state:
{"; ".join(f"{r.county_name}, {r.state_abbr} (average premium {r.avg:+.1f}%, last price {r.last_year})" for r in excl.itertuples())};
both would otherwise have entered the pool and are worth a look once current prices are available.</p>
</div>
<div class='section'>
<h3 style='margin-top:0'>D4. The score</h3>
<p>Premium strength = percentile rank of the average premium among the ten; demand index = mean of the percentile ranks of children needing care,
care-need share and income per capita among the ten; score = 0.5 × premium strength + 0.5 × demand index. Because both parts are ranked on the
same scale, the 50/50 weights are the effective weights (an earlier version ranked demand against all counties, which tilted the weights; corrected).
The score only orders the ten: 70/30 and 30/70 weights give the same ten counties.</p>
{tbl(["Rank", "County", "Avg. premium", "Premium strength", "Children", "Care-need share", "Income", "Demand index", "Score"], srows,
     align=["c", "l", "r", "r", "r", "r", "r", "r", "r"], widths=["7%", "19%", "11%", "11%", "10%", "11%", "9%", "11%", "11%"], cls="small")}
<h3>D4b. Which market characteristics we use, and why</h3>
<p>Our characteristics (assignment item c): the <b>average premium</b> and its <b>weakest year</b> (price advantage and its persistence), and three
demand measures from the 2022 ACS: <b>children needing care</b> (under 6, all resident parents working: market size), their <b>share of the population</b>
(need intensity) and <b>income per capita</b> (ability to pay). Two further ACS variables from Problem Set 5 are not used: the female college share
correlates {dcor.loc['female_college_share', 'per_capita_income_real2022']:.2f} with income (it would count affluence twice), and the female full-time share
overlaps the care-need share, which measures working parents directly ({dcor.loc['female_ftyr_share', 'under6_careneed_share']:.2f}).</p>
<p>Within states, the demand measures are only weakly related to the premium (regression below): demand adds information the premium does not already
contain, which is why the score weighs both. We deliberately did not pick demand variables by how well they predict the premium; that would count the
premium twice.</p>
{tbl(["Average log premium on (standardized, state effects)", "Used in the score", "+ two unused shares"], dem_rows,
     widths=["46%", "27%", "27%"], cls="small")}
<p class='note'>Coefficient = % change in the average premium per standard deviation; SE clustered by metro area; N = {int(demd.n.iloc[0])} counties
(in the 2022 data, observed ≥ 5 years). ** p &lt; 0.01, * p &lt; 0.05.</p>
<h3>D5. Are premiums stable over time?</h3>
{box("idea", "Our idea", "<p>A price advantage is only worth building on if it lasts. We test whether counties that had a premium in the past still have "
     "one later, and how much of it survives.</p>")}
{fig("app_D_persistence.png", "Figure D1. Left: within-state premium in a county's first and last direct NDCP survey year (≈ 4.7 years apart; blue = top 10). "
     "Right: correlation of county premiums between years, all counties.")}
<p><b>Why survey years matter.</b> NDCP interpolates prices between survey years, which mechanically smooths premiums and would overstate their
stability. The cleanest test therefore uses only years in which both prices are direct survey values (5th digit of the NDCP imputation code = 0):
one pair per county, the first and last survey year, {int(sv['n_counties']):,} counties in {int(sv['n_states'])} states, on average
{sv['mean_gap_years']:.1f} years apart.</p>
{stats_row([(f"{sv['slope']:.2f}", f"of a premium survives ≈ {sv['mean_gap_years']:.1f} years later (95% CI {lo:.2f}–{hi:.2f}, SE clustered by state)"),
            (f"{sv['corr']:.2f}", "correlation of the two survey premiums"), (f"{sv['share_same_sign'] * 100:.0f}%", "of counties keep the sign of their premium"),
            ("&lt; 1", "premiums fade partially (regression to the mean, plus noise in the first survey price)")])}
<div class='cols2'><div>
<p><b>Balanced panel</b> (counties observed in all 8 years): regression of the 2022 premium on an earlier year's premium (log points, SE clustered by state).</p>
{tbl(["Model", "N", "Slope", "SE", "R²"], prow, widths=["40%", "14%", "15%", "15%", "16%"], cls="small")}
</div><div>
<p><b>Quintile transitions</b> (balanced panel): counties in the top fifth of premiums in an earlier year, and where they are in 2022.</p>
{tbl(["Top fifth in", "N", "Top fifth 2022", "Above median", "Positive"], qrows, widths=["30%", "10%", "20%", "20%", "20%"], cls="small")}
</div></div>
{box("decision", "Team decision D8 · plan with the expected premium", f"<p>Because premiums fade partially, we do not promise today's premium. "
     f"Expected premium = exp(a + b · average log premium) − 1, with a and b from the survey-only regression (b = {sv['slope']:.3f}); the range uses the "
     f"95% CI of b, so it reflects the uncertainty of the fading slope, not how much one county scatters around it. The expected premium is computed on the log scale, so the “average” used here is the geometric mean (column 4), which differs slightly from the "
     f"arithmetic average used for ranking (column 3).</p>"
     + tbl(["Rank", "County", "Average premium (arithmetic)", "Average (geometric)", "Expected premium", "Range (slope CI)"], erows,
           widths=["8%", "22%", "20%", "17%", "16%", "17%"], cls="small"))}
</div>"""

# ================================================================== E: reliability =========================================
brows = [[f"{r.county_name}, {r.state_abbr}", pc(r.mean_prem), pc(r.premium_2022) if pd.notna(r.premium_2022) else "no 2022 price",
          f"{r.pct_rank_2022 * 100:.0f}th" if pd.notna(r.pct_rank_2022) else "–", "✓" if r.in_top10_today else "–"] for r in bt18.itertuples()]
VARX = {"Previous design: pool ranked on 2022 premium only": "not counted: replaced by D2 (2022 extrapolations)",
        "National premium, no state effects (LL)": "not counted: rejected in D1 (selects states, not markets)"}
rrows = [[re.sub(r"(\d{4})-(\d{4})", "\\1–\\2", r.variant), f"{r.overlap_with_top10}/10", r.dropped if isinstance(r.dropped, str) else "–",
          r.added if isinstance(r.added, str) else "–", r.status] for r in rob.itertuples()]
capv = rd("fp_metro_cap_variant.csv", dtype={"fips": str})
caprows = [[str(r.rank), f"{r.county_name}, {r.state_abbr}", r.metro_area.split(",")[0], pc(r.mean_premium_LLS_pct), f"{r.score:.2f}",
            "✓" if r.in_top10 else "<b>new</b>"] for r in capv.itertuples()]
wrows = [[r.specification, f"{r.overlap_with_top10}/10", r.dropped if isinstance(r.dropped, str) else "–", r.added if isinstance(r.added, str) else "–"]
         for r in ww.itertuples()]
b2x = b2.set_index("fips")
sigx = sig.assign(fips=sig.apply(lambda r: top.set_index(top.county_name + top.state_abbr).loc[r.county_name + r.state_abbr, "fips"], axis=1)).set_index("fips")
krows = [[str(r.rank), SHORT[r.fips], f"{b2x.loc[r.fips, 'z']:.2f}", f"{b2x.loc[r.fips, 'pct_rank'] * 100:.1f}",
          pc(sigx.loc[r.fips, "premium_pct"]), f"{sigx.loc[r.fips, 'student']:.2f}", "✓" if sigx.loc[r.fips, "above_95pi"] else "–"]
         for r in top.itertuples()]
qrows2 = [[str(int(r.rank)), f"{r.county_name.replace(' County', '').replace(' City', '')}, {r.state_abbr}", f"{r.survey_years} of {r.years}", r.survey_list,
           pc(r.mean_premium_survey_years), pc(r.mean_premium_all_years)] for r in qual.itertuples()]
partE = section("E", "How reliable is the prediction?", "slide 4") + f"""
{box("idea", "Our idea", "<p>Test the whole approach the way it would have been used: decide with old data only, then check what happened. And make "
     "sure the list does not hinge on any single design choice.</p>")}
<h3>E1. Backtest: the complete rule as if we had decided in 2018</h3>
<p>Every step of the rule (premiums, average over 2015–2018 with at least 3 years, national premium, persistence, market size and demand from 2018,
score) applied with data up to 2018 only; outcome = the county's within-state premium in 2022, four years later.</p>
<div class='cols2'><div>
{tbl(["Picked in 2018", "Avg. 2015–18", "Premium 2022", "Pct. 2022", "Top 10 today"], brows, widths=["34%", "17%", "19%", "14%", "16%"], cls="small")}
</div><div>
{stats_row([(pc(bt.iloc[0].mean_premium_2022, 1), f"average 2022 premium of the {int(bt.iloc[0].n_in_2022)} picks still in the 2022 data"),
            (pc(bt.iloc[1].mean_premium_2022, 1), f"all other {int(bt.iloc[1].n_in_2022):,} counties")])}
{stats_row([(pc(bt.iloc[2].mean_premium_2022, 1), f"the same without CA/VA ({int(bt.iloc[2].n_in_2022)} picks), whose 2022 prices are extrapolated"),
            (pc(bt.iloc[3].mean_premium_2022, 1), f"all other counties without CA/VA ({int(bt.iloc[3].n_in_2022):,})")])}
{stats_row([(f"{bt.iloc[0].share_positive * 100:.0f}%", "of the picks still have a positive premium (others: " + f"{bt.iloc[1].share_positive * 100:.0f}%)"),
            (f"{int(bt.iloc[0].overlap_with_2022_top10)}/10", "of the 2018 picks are in today's top 10")])}
</div></div>
<p class='note'>Two honest caveats. The headline +{bt.iloc[0].mean_premium_2022:.1f}% includes Arlington and Alexandria, whose 2022 prices are NDCP
extrapolations; without CA/VA the picks still beat all other counties by about {bt.iloc[2].mean_premium_2022 - bt.iloc[3].mean_premium_2022:.0f}
percentage points. And today's ranking averages 2015–2022, which includes the 2015–2018 years the backtest used, so the overlap of
{int(bt.iloc[0].overlap_with_2022_top10)} of 10 is partly mechanical; the 2022 outcome itself is not.</p>
<h3>E2. Robustness: the whole rule rerun with one change at a time</h3>
{tbl(["Variant", "Same", "Dropped", "Added", "Status"], rrows, align=["l", "c", "l", "l", "l"], widths=["26%", "7%", "25%", "22%", "20%"], cls="small")}
<p class='note'>Counted variants: {int(robc['of'].iloc[0])} (the two weight variants and “one negative year allowed” are reported but cannot change the
list by construction: the score only orders the ten, and all 20 candidates already pass the persistence filter). Selected in all counted variants:
{int((robc.selected_in_variants == robc['of']).sum())} of 10;
{"; ".join(f"{r.county.replace(' County', '').replace(' City', '')} {r.selected_in_variants}/{r.of}" for r in robc.itertuples() if r.selected_in_variants < r.of)}.</p>
<h3>E2b. Portfolio view: at most two counties per metro area</h3>
<p>Not a robustness test but a business view of the Northern Virginia cluster (Appendix F3): the same rule, walking down the ranking until ten counties
qualify with at most two per metro area. The two lower-ranked Northern Virginia counties give way to the next qualifying markets; the other eight stay.</p>
{tbl(["Rank", "County", "Metro area", "Avg. premium", "Score", "In top 10"], caprows, align=["c", "l", "l", "r", "r", "c"],
     widths=["8%", "26%", "30%", "13%", "11%", "12%"], cls="small")}
<h3>E3. Different wage measures and weighting</h3>
{tbl(["Specification", "Same", "Dropped", "Added"], wrows, align=["l", "c", "l", "l"], widths=["34%", "8%", "30%", "28%"], cls="small")}
<p class='note'>Centers employ preschool teachers (SOC 25-2011) as well as childcare workers (SOC 39-9011, the assignment's measure). With both wages
in the 2022 model, the childcare-worker elasticity is {wfit.set_index('model').loc['both wages', 'coef_childcare_wage']:.2f} vs.
{wfit.set_index('model').loc['both wages', 'coef_teacher_wage']:.2f} for teachers, and R² barely changes (sample with both wages,
N = {int(wfit.n_2022.iloc[0])})
({wfit.set_index('model').loc['childcare-worker wage', 'r2']:.3f} vs. {wfit.set_index('model').loc['both wages', 'r2']:.3f}). Weighting by children
lets large counties dominate the cost line; we keep every county as one market observation (D7).</p>
</div>
<div class='section'>
<h3 style='margin-top:0'>E4. Statistical checks</h3>
<p><b>Average premium</b> (what we select on): z-score and percentile among all {n5_all:,} counties observed in ≥ 5 years (log scale).
<b>Single year 2022:</b> studentized residual of the final model and whether the county lies above the 95% prediction band.</p>
{tbl(["Rank", "County", "z (average)", "Percentile (average)", "Premium 2022", "Studentized 2022", "Above 95% band 2022"], krows,
     align=["c", "l", "r", "r", "r", "r", "c"], widths=["7%", "21%", "12%", "15%", "14%", "15%", "16%"], cls="small")}
<p>All ten average premiums are in the top 2% (z {b2.z.min():.1f}–{b2.z.max():.1f}). This describes how extreme they are; it is not an independent
test, because the candidate pool is the 20 largest averages. In 2022 alone, {int(sig.above_95pi.sum())} of the ten lie above the 95% prediction band,
against {diag['share_above_95pi_all'] * 100:.1f}% of all counties; four of those six have extrapolated CA/VA 2022 prices. The other four have clear but not
extreme 2022 premiums and qualify through their persistence over all years: a single year is noisy, a premium that holds for 7–8 years is not.</p>
<h3>E5. Data quality: are the premiums real survey prices?</h3>
{tbl(["Rank", "County", "Survey years", "Which", "Avg. premium, survey years", "Avg. premium, all years"], qrows2,
     align=["c", "l", "c", "l", "r", "r"], widths=["7%", "20%", "12%", "21%", "20%", "20%"], cls="small")}
<p class='note'>NDCP surveys each state every few years and interpolates (or, for CA and VA in 2022, extrapolates) in between. Every top-10
county also has a large premium in its direct survey years, so the advantage is not an artifact of interpolation.</p>
</div>"""

# ================================================================== F: local factors =========================================
q = lambda v, k: bm.loc[v, k]
FLAGS = [
    ["Competition", "CBP child day care establishments per 1,000 children needing care (2022)",
     f"! above {q('centers_per_1000_kids', '75%'):.2f} (crowded) or below {q('centers_per_1000_kids', '25%'):.2f} (untested market)", f"{int(bm.loc['centers_per_1000_kids', 'count'])}"],
    ["Child trend", "Change in children under 6, ACS 2015 → 2022",
     f"! below median ({pc(q('kids_change_2015_2022_pct', '50%'), 1)}); ✕ bottom quarter (below {pc(q('kids_change_2015_2022_pct', '25%'), 1)})", f"{int(bm.loc['kids_change_2015_2022_pct', 'count'])}"],
    ["Wage growth", "Real childcare-worker wage, 2019 → 2022", f"! top quarter (above {q('wage_change_2019_2022_pct', '75%'):+.1f}%)", f"{int(bm.loc['wage_change_2019_2022_pct', 'count'])}"],
    ["Rent growth", "Real median gross rent, 2015 → 2022", f"! top quarter (above {q('rent_change_2015_2022_pct', '75%'):+.1f}%)", f"{int(bm.loc['rent_change_2015_2022_pct', 'count'])}"],
    ["Public pre-K", "Free public pre-K for all incomes (universal) in the county", "! universal program", "10 (sourced)"],
]
mrows2 = [[SHORT[r.fips], f"{r.estab_2022:.0f}", f"{r.centers_per_1000_kids:.2f}", pc(r.kids_change_2015_2022_pct, 1), pc(r.wage_change_2019_2022_pct, 1),
           pc(r.rent_change_2015_2022_pct, 1)] for r in mf.itertuples()]
krows3 = [[SHORT[f], r.program, r.scope, r.eligibility, "<b>!</b>" if r.flag == "yes" else "–",
           f"<span class='url'>{r.source_url}</span>"] for f, r in prek.iterrows()]
OTHERS = [
    ["Washington, DC", f"{pc(float(dcg['dc_premium_2022_pct']))} in 2022 when grouped with MD and VA", "NDCP price only for 2022: no history to test persistence; with state effects a one-county “state” has a premium of 0 by construction"],
    ["Milwaukee, WI", "Selected when 2022 is excluded, pre-COVID only, or with $ premiums", "Robustness variants (E2)"],
    ["Ramsey (St. Paul), MN", "Selected with $ premiums, a top-30 pool, the preschool-teacher wage, and in the portfolio view", "Robustness variants (E2, E2b, E3)"],
    ["Norfolk, MA", "Selected with $ premiums", "Robustness variant (E2)"],
    ["Fairfax City, VA", "Selected with the smaller market threshold", "Robustness variant (E2)"],
    ["Clayton, GA", "Selected with the preschool-teacher wage", "Robustness variant (E3)"],
    ["St. Louis, MO", "Average premium +29.5%; picked by the 2018 backtest", "No NDCP price after 2020 (D3)"],
    ["Trumbull (Youngstown), OH", "Enters the portfolio view with at most 2 counties per metro area (E2b)", "Lower premium and demand than the ten"],
]
wash = rd("app_washington_counties.csv", dtype={"fips": str}).set_index("fips")
vsp = rd("app_state_premium_spread.csv").set_index("state_abbr")
partF = section("F", "What the model does not see yet", "slide 6") + f"""
{box("idea", "Our idea", "<p>A premium tells us where parents pay more than costs justify, not whether a new center would succeed there. Before "
     "recommending a market we check what could erode the premium: competition, shrinking demand, rising costs and free public alternatives.</p>")}
<h3>F1. Risk checks and thresholds</h3>
{tbl(["Check", "Measure", "Flag (vs. quartiles of all metro counties with data)", "Counties"], FLAGS, align=["l", "l", "l", "r"],
     widths=["14%", "38%", "38%", "10%"], cls="small")}
{tbl(["County", "Centers 2022", "per 1,000 children", "Children <6, 2015–22", "Wage, 2019–22", "Rent, 2015–22"], mrows2,
     widths=["24%", "13%", "15%", "17%", "15%", "16%"], cls="small")}
<p class='note'>CBP counts employer establishments (not capacity, quality, or home-based providers without employees). Across all counties,
premium and center density are only weakly related, so a premium is not simply a sign of missing supply.
<b>Recommendation rule:</b> start where at most one minor flag appears (Arlington, Alexandria, Loudoun, Fairfax: one Northern Virginia market, F3);
next in line are Olmsted and Howard.</p>
<h3>F2. Free public pre-K (checked against program rules)</h3>
{tbl(["County", "Program", "Scope", "Eligibility", "Flag", "Source"], krows3, align=["l", "l", "l", "l", "c", "l"],
     widths=["12%", "19%", "10%", "33%", "5%", "21%"], cls="tiny")}
<p class='note'>Universal programs compete directly with paid preschool for 4-year-olds (Georgia's lottery-funded Pre-K; California's universal
transitional kindergarten, fully phased in for 2025–26, plus San Francisco's Preschool for All; Multnomah's Preschool for All, ages 3–4, scaling to
universal access by 2030). Income-targeted programs (VA, MD, MN, TN) mainly serve families outside the target segment of a premium-priced center.
Georgia's program dates from the 1990s, so it is already reflected in Hall's prices; California's TK and Multnomah's Preschool for All started
during or after our price data and are a forward-looking risk. Sources accessed in October 2026
(<code>data/manual/public_prek_programs.csv</code>).</p>
<h3>F3. Four of ten in one market: the Northern Virginia cluster</h3>
<p>Arlington, Alexandria, Loudoun and Fairfax (ranks 1, 2, 4, 6) are neighbors in the Washington metro area. We checked whether this is a real market
effect or an artifact of the data:</p>
<ul>
<li><b>A sharp inner core, not the whole metro.</b> Of the {len(wash)} Washington-metro counties with enough history, the inner Northern Virginia
jurisdictions all have premiums of about +30% to +{wash.avg.max():.0f}%, while outer counties are near zero or negative (e.g.
{"; ".join(f"{r.county_name.replace(' County', '')} {pc(r.avg)}" for r in wash[wash.index.isin(['51153', '24033', '51179', '51061'])].itertuples())}).</li>
<li><b>Real survey prices, national comparison.</b> The four keep large premiums in their direct survey years (E5) and against the national model
(Arlington {wash.loc['51013', 'nat']:+.0f}%); all four stay selected without the 2022 data (E2).</li>
<li><b>Partly structural.</b> Virginia reports many small jurisdictions ({int(vsp.loc['VA', 'counties'])} in our data, incl. independent cities), and its premiums are
the {int(vsp.loc['VA', 'rank'])}rd most dispersed of {len(vsp)} states (SD {vsp.loc['VA', 'sd']:.3f} vs. median {vsp.sd.median():.3f}). More, smaller units
produce more extreme values: 9 of the 20 candidates are Virginian; the market-size filter keeps only the four large ones.</li>
<li><b>Not four independent confirmations.</b> They share one OEWS wage, one labor market, one state survey (direct prices only in 2015 and 2018) and the
same exposure to federal employment changes. We therefore recommend one first site in Northern Virginia, with current prices checked on the ground, and
show a portfolio view with at most two counties per metro area (E2b).</li>
</ul>
<h3>F4. Other promising counties (teal on the slide 1 map; St. Louis and Trumbull not shown)</h3>
{tbl(["County", "Evidence", "Why not in the top 10"], OTHERS, align=["l", "l", "l"], widths=["20%", "42%", "38%"], cls="small")}
</div>"""

# ================================================================== G: limits & reproducibility ================================
scripts = sorted(ROOT.glob("scripts/[0-3][0-9]_*.py"))
ROLE = {**{n: "data" for n in (1, 2, 3, 4, 5, 8, 12, 13, 15)}, **{n: "homework only" for n in (6, 7, 9, 10, 11, 14, 16, 17)},
        **{n: "pre-analysis" for n in range(18, 25)}, **{n: "final project" for n in range(25, 39)}}
srows2 = []
for s_ in scripts:
    doc = ast.get_docstring(ast.parse(s_.read_text(encoding="utf-8"))) or ""
    para = " ".join(doc.strip().split(chr(10) * 2)[0].split())
    first = re.split(r"(?<=[.?])\s+(?=[A-Z])", para)[0]
    first = first if first.endswith((".", "?")) else first + "."
    srows2.append([f"<code>{s_.name}</code>", ROLE.get(int(s_.name[:2]), ""), first])
n_ck = len((ROOT / "data/raw_checksums.sha256").read_text().strip().splitlines())
partG = section("G", "Limitations and reproducibility", "") + f"""
<h3>G1. Limitations</h3>
<ul>
<li><b>Prices are survey medians, not offers.</b> NDCP prices are county medians from state market-rate surveys; each top-10 county has only 2–5 direct
survey years. A new premium provider may be able to charge more or less than the median.</li>
<li><b>Costs are proxies.</b> We use residential rent (a center pays commercial rent) and average metro wages (not vacancies or turnover); all counties
of a metro area share one wage.</li>
<li><b>The residual mixes signal and noise.</b> Part of each premium reflects quality, regulation or measurement error. Averaging over years, the
persistence filter, the survey-only checks and the robustness variants reduce but cannot remove this.</li>
<li><b>Demand is measured once.</b> Market size and the demand score use the 2022 ACS; post-COVID shifts such as remote work are not captured.</li>
<li><b>Associations, not causal effects.</b> The cost model describes how prices co-move with costs; it is used to measure unusual prices, not to claim
what would happen if wages changed.</li>
<li><b>Free public pre-K</b> is universal in three of the ten counties (new or expanding in San Francisco and Multnomah); its future effect on paid preschool demand is not in our price data.</li>
</ul>
<h3>G2. Reproducibility</h3>
<p><code>python run_pipeline.py</code> reruns all scripts in order from the included data (no downloads or keys needed; see the README;
<code>--full</code> re-downloads the raw data). Scripts marked “homework only” are not needed for the project (Python 3.14; pandas, statsmodels,
scikit-learn, scipy, matplotlib, python-pptx, pyshp; versions in <code>requirements.txt</code>). The raw BLS OEWS zip files (275 MB) are not included;
<code>02_get_oews.py</code> downloads them, and the extracted wages are in <code>data/interim/</code>.
Downloaded raw files are never edited; {n_ck} files are fixed by SHA-256 checksums in <code>data/raw_checksums.sha256</code>. The Census API key
is read from a local, git-ignored file (<code>census_api_key.txt</code>) and is not part of the submission; BLS downloads use the contact e-mail of
whoever runs the code (environment variable <code>BLS_CONTACT_EMAIL</code>). <b>Number check:</b> <code>35_fp_check_deck_numbers.py</code>
recomputes every number stated on the slides from the result tables ({check_line.replace('Result: ', '').rstrip('.')}).</p>
{tbl(["Script", "Role", "Purpose"], srows2, align=["l", "l", "l"], widths=["31%", "12%", "57%"], cls="tiny")}
<p class='note'>AI use: the analysis code, figures and drafts of this text were produced with Claude Code at the team's direction (https://claude.ai/code); every
prompt, verbatim and dated, is in the prompt log submitted with the code (<code>MGT403_Prompt_Log.pdf</code>). Decisions marked as team decisions
were taken by the team.</p>
</div>"""


# ================================================================== part title pages ========================================
def divider(part, title, sub, items):
    rows = "".join(f"<div class='toc-row'><span class='toc-key'>{k}</span><span class='toc-txt'>{t}</span><span class='toc-ref'>{r}</span></div>"
                   for k, t, r in items)
    return (f"<div class='divider'><div class='div-top'><div class='div-part'>{part}</div><h1 class='div-title'>{title}</h1>"
            f"<div class='div-sub'>{sub}</div></div><div class='toc'>{rows}</div>"
            "</div>")


divP = divider("Part I", "Pre-analysis", "Project data work: prices and costs. Answers to the four pre-analysis tasks and the work behind them.", [
    ("Task 1", "The analysis dataset: merge, definition, sample flow", f"N = {len(a):,} county-years"),
    ("Task 2", "Descriptive statistics, 2022", f"N = {len(d22)} counties"),
    ("Task 3", "Prices vs. wages and rents: scatter plots and team interpretation", "bivariate OLS"),
    ("Task 4", "Multivariate regression, model “c”: team decisions and interpretation", "metro-clustered SEs")])
divA = divider("Part II", "Appendix", "Final project analysis: data handling, methods, decisions and checks behind our ten recommended counties.", [
    ("0", "From our ideas to measurable steps; which years enter which analysis", ""),
    ("A", "Data sources, variables, samples and data-handling decisions", "all slides"),
    ("B", "Cost model: from model “c” to our prediction; fit and residuals", "slide 2"),
    ("C", "Out-of-sample validation of the cost model", "slide 2"),
    ("D", "Team decisions, selection rule, candidates, score; stability", "slides 3, 5"),
    ("E", "Reliability: backtest, robustness, portfolio view, statistical checks, data quality", "slide 4"),
    ("F", "Risk checks, public pre-K, the Northern Virginia cluster, other candidates", "slide 6"),
    ("G", "Limitations and reproducibility", "")])

# ================================================================== CSS / HTML ===============================================
CSS = """
@page { size: Letter; margin: 0.72in 0.75in 0.78in 0.75in;
  @bottom-left { content: "MGT 403 · Where should we open our next preschool? · Pre-analysis and appendix"; font: 7pt 'Segoe UI', sans-serif; color: #86868b; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7pt 'Segoe UI', sans-serif; color: #86868b; } }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
:root { --accent: #2b6cd0; --tint: #eef4fc; --card: #f5f5f7; --ink: #1d1d1f; --ink2: #6e6e73; --muted: #86868b; --line: #e5e5ea; --orange: #f56300; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.2pt; line-height: 1.42; color: var(--ink); margin: 0; }
p { margin: 0 0 6pt; } ul, ol { margin: 2pt 0 7pt; padding-left: 15pt; } li { margin-bottom: 2.5pt; }
h1 { font-size: 24pt; font-weight: 600; letter-spacing: -0.02em; line-height: 1.08; margin: 6pt 0 8pt; }
h2 { font-size: 18pt; font-weight: 600; letter-spacing: -0.01em; margin: 2pt 0 10pt; line-height: 1.15; }
h3 { font-size: 10.6pt; font-weight: 600; margin: 13pt 0 5pt; }
h2, h3 { break-after: avoid; }
.section { break-before: page; }
.eyebrow { font-size: 8pt; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: var(--accent); }
.slideref { color: var(--muted); margin-left: 8pt; letter-spacing: .06em; }
.slideref:before { content: "·  "; }
.cover { padding-top: 12pt; border-top: 4pt solid var(--accent); margin-bottom: 8pt; }
.kicker { font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: var(--ink2); font-weight: 600; }
.subtitle { font-size: 13pt; color: var(--ink2); margin-bottom: 10pt; }
.team { font-size: 9pt; color: var(--ink2); }
.lead { font-size: 10.2pt; line-height: 1.42; margin: 0 0 4pt; }
.cover-page table td { padding: 1.6pt 5pt; } .cover-page h3 { margin: 7pt 0 2pt; } .cover-page .note { margin-bottom: 3pt; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 8pt; font-size: 8.3pt; font-variant-numeric: tabular-nums; table-layout: fixed; }
tr { break-inside: avoid; } thead { display: table-header-group; }
th { font-weight: 600; color: var(--ink2); font-size: 7.2pt; text-transform: uppercase; letter-spacing: .035em; border-bottom: 0.9pt solid var(--ink2);
     padding: 3pt 5pt; vertical-align: bottom; }
td { padding: 2.6pt 5pt; border-bottom: 0.5pt solid var(--line); vertical-align: top; }
td.r, th.r { text-align: right; } td.c, th.c { text-align: center; } td.l, th.l { text-align: left; }
tr.hl td { background: var(--tint); font-weight: 600; }
table.small { font-size: 7.8pt; } table.small td { padding: 2.2pt 4.5pt; }
table.tiny { font-size: 7.1pt; } table.tiny td { padding: 2pt 4pt; }
.se { color: var(--muted); font-size: 0.9em; font-weight: 400; }
.url { word-break: break-all; color: var(--accent); font-size: 6.6pt; }
.note { font-size: 7.9pt; color: var(--ink2); line-height: 1.38; }
.box { border-radius: 7pt; padding: 8pt 12pt 3pt; margin: 4pt 0 10pt; break-inside: avoid; }
.box p { margin-bottom: 5pt; }
.boxlabel { font-size: 7.4pt; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; margin-bottom: 3pt; }
.idea { background: var(--tint); } .idea .boxlabel { color: var(--accent); } .idea p { font-size: 9.8pt; }
.decision { background: #fff; border: 0.9pt solid var(--accent); } .decision .boxlabel { color: var(--accent); }
.team { background: #fff; border-left: 3pt solid var(--accent); border-radius: 0 7pt 7pt 0; background: #fafbfd; } .team .boxlabel { color: var(--accent); }
.team p { font-size: 9.4pt; } .task { background: var(--card); border-radius: 6pt; padding: 5pt 9pt; font-size: 8.4pt; color: var(--ink2); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); gap: 9pt; margin: 6pt 0 9pt; break-inside: avoid; }
.stat { background: var(--card); border-radius: 7pt; padding: 7pt 10pt; }
.stat .num { font-size: 17pt; font-weight: 600; color: var(--accent); line-height: 1.1; }
.stat .lab { font-size: 7.6pt; color: var(--ink2); line-height: 1.3; margin-top: 2pt; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14pt; align-items: start; }
figure { margin: 5pt 0 9pt; break-inside: avoid; } figure img { display: block; }
figcaption { font-size: 7.8pt; color: var(--ink2); margin-top: 3pt; line-height: 1.35; }
.beyond { display: inline-block; background: #ededf0; color: var(--ink2); font-size: 7pt; font-weight: 600; letter-spacing: .03em;
          border-radius: 8pt; padding: 1pt 7pt; vertical-align: 1pt; }
.tagteam { display: inline-block; border: 0.8pt solid var(--accent); color: var(--accent); font-size: 7pt; font-weight: 600; border-radius: 8pt; padding: 0 6pt; }
.divider { break-before: page; break-after: page; height: 9.2in; display: flex; flex-direction: column; }
.div-top { margin-top: 1.9in; border-top: 4pt solid var(--accent); padding-top: 16pt; }
.div-part { font-size: 10pt; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); }
.div-title { font-size: 40pt; margin: 4pt 0 8pt; }
.div-sub { font-size: 12pt; color: var(--ink2); max-width: 5.6in; line-height: 1.4; }
.toc { margin-top: 30pt; border-top: 0.8pt solid var(--ink2); }
.toc-row { display: flex; padding: 6pt 0; border-bottom: 0.5pt solid var(--line); font-size: 10pt; }
.toc-key { width: 0.85in; font-weight: 600; color: var(--accent); }
.toc-txt { flex: 1; } .toc-ref { width: 1.5in; text-align: right; color: var(--muted); font-size: 8.5pt; }
.div-foot { margin-top: auto; font-size: 7.5pt; color: var(--muted); }
.partI { page: partI; } .partII { page: partII; }
@page partI { @bottom-left { content: "MGT 403 · Where should we open our next preschool? · Part I · Pre-analysis"; font: 7pt 'Segoe UI', sans-serif; color: #86868b; } }
@page partII { @bottom-left { content: "MGT 403 · Where should we open our next preschool? · Part II · Appendix"; font: 7pt 'Segoe UI', sans-serif; color: #86868b; } }
code { font-family: Consolas, monospace; font-size: 0.92em; background: var(--card); padding: 0 2pt; border-radius: 2pt; }
"""
HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>MGT 403 Pre-analysis and appendix: Where should we open our next preschool?</title>
<style>{CSS}</style></head><body>{cover}<div class='partI'>{divP}{partP}</div><div class='partII'>{divA}{part0}{partA}{partB}{partC}{partD}{partE}{partF}{partG}</div></body></html>"""

out_html = SUB / "MGT403_PreAnalysis_and_Appendix.html"
out_html.write_text(HTML, encoding="utf-8")
out_pdf = SUB / "MGT403_PreAnalysis_and_Appendix.pdf"
out_pdf.unlink(missing_ok=True)
profile = Path(tempfile.mkdtemp(prefix="edge_pdf_"))
subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}", "--no-first-run",
                "--disable-extensions", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
                f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=True, capture_output=True)
last = -1
for _ in range(120):
    time.sleep(0.5)
    size = out_pdf.stat().st_size if out_pdf.exists() else -1
    if size > 0 and size == last:
        break
    last = size
print("written", out_pdf, out_pdf.stat().st_size)
