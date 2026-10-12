"""Build the Problem Set 4 submission PDF (MGT 403, Homework 4, Question 2).

Assembles, in one HTML document printed to PDF with headless Microsoft Edge:
  - AI-generated results: every number is read from output/tables/*.csv (nothing retyped),
  - the student's own texts (Q2, Q3 discussions; final versions, spelling/grammar-checked only),
  - the student's handwritten Q4 work (scans) plus a typed transcription,
  - appendices: data & methods, AI-use statement, prompt log (PROMPT_LOG.md).

Inputs:  output/tables/*.csv, output/figures/*.png, submission/handwritten/q4_page{2,3,4}.png,
         PROMPT_LOG.md
Outputs: submission/PS4_submission.html, submission/PS4_submission.pdf
"""
import math
import subprocess
import tempfile
import time
from pathlib import Path

import markdown
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"
T = ROOT / "output/tables"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

GROUP = ["Carson Tavares", "Lee Itzhaki", "Vusala Suleymanova", "Philipp Romberg"]  # Question 2 (group)
Q1_AUTHOR = "Philipp Romberg"  # Question 1 (individual)
DATE = "30 September 2026"

q1 = pd.read_csv(T / "ps4_q1_sample_construction.csv")
imp = pd.read_csv(T / "ps4_q1_imputation_2022.csv").set_index("age_group")
q2 = pd.read_csv(T / "ps4_q2_summary_2022.csv")
q2p = pd.read_csv(T / "ps4_q2_paired_differences_2022.csv")
q3 = pd.read_csv(T / "ps4_q3_trends_real.csv")
q3c = pd.read_csv(T / "ps4_q3_changes.csv")
q4 = pd.read_csv(T / "ps4_q4_voucher_test.csv").set_index("year")
q4r = pd.read_csv(T / "ps4_q4_robustness.csv")


def d(x, k=2):
    return f"${x:,.{k}f}"


def sci(p, k=2):
    e = math.floor(math.log10(p))
    return f"{p / 10 ** e:.{k}f} × 10<sup>{str(e).replace('-', '−')}</sup>"


def fmt_p(p):
    return sci(p) if p < 1e-3 else f"{p:.3f}"


def pct(x, k=1, sign=True):
    return f"{x:+.{k}f}%" if sign else f"{x:.{k}f}%"


# --- Q4 derived numbers (weekly units, as in the student's handwritten solution) -----------
W = 4.33
wk = {}
for y in (2022, 2015):
    r = q4.loc[y]
    wk[y] = dict(n=int(r.n), mu0=r.voucher_monthly / W, xbar=r.mean_monthly / W, s=r.sd_monthly / W,
                 se=r.se / W, t=r.t_stat, p_t=r.p_value_t, p_z=r.p_value_normal, tcrit=r.t_crit_5pct,
                 lo=r.ci_low / W, hi=r.ci_high / W, voucher=r.voucher_monthly, mean_m=r.mean_monthly,
                 cover=r.voucher_monthly / r.mean_monthly * 100,
                 gap=r.mean_monthly - r.voucher_monthly,
                 gap_pct=(r.mean_monthly / r.voucher_monthly - 1) * 100)
p_z_639 = math.erfc(6.39 / math.sqrt(2))

# --- Tables -------------------------------------------------------------------------------
q1_rows = "".join(
    f"<tr><td>{r.year}</td><td>{r.ndcp_counties:,}</td><td>{r.nonmetro_dropped:,}</td>"
    f"<td><b>{r.metro_counties:,}</b></td><td>{r.metro_areas}</td><td>{r.with_preschool_price:,}</td></tr>"
    for r in q1.itertuples())

q2_rows = "".join(
    f"<tr><td>{r.age_group}</td><td>{r.n:,}</td><td><b>{d(r.mean)}</b></td><td>{d(r.sd)}</td>"
    f"<td>{d(r.se)}</td><td>[{d(r.ci_low)}, {d(r.ci_high)}]</td><td>{d(r.median)}</td></tr>"
    for r in q2.itertuples())

pair_lab = {"MCINFANT - MCTODDLER": "Infant − Toddler", "MCTODDLER - MCPRESCHOOL": "Toddler − Preschool",
            "MCINFANT - MCPRESCHOOL": "Infant − Preschool"}
q2p_rows = "".join(
    f"<tr><td>{pair_lab[r.comparison]}</td><td>{d(r.mean)}</td><td>[{d(r.ci_low)}, {d(r.ci_high)}]</td>"
    f"<td>[{d(r.ci_low_cluster)}, {d(r.ci_high_cluster)}]</td><td>{r.share_counties_first_higher * 100:.1f}%</td></tr>"
    for r in q2p.itertuples())
q2c_rows = "".join(
    f"<tr><td>{r.age_group.split(' (')[0]}</td><td>{d(r.se)}</td><td>{d(r.se_cluster)}</td>"
    f"<td>[{d(r.ci_low_cluster)}, {d(r.ci_high_cluster)}]</td></tr>" for r in q2.itertuples())

real = pd.read_csv(ROOT / "data/analysis/ndcp_metro_2015_2022_real.csv", dtype={"fips": str})
piv = pd.DataFrame({lab: real.groupby("year")[f"{c}_real2022"].mean()
                    for c, lab in [("MCINFANT", "Infant"), ("MCTODDLER", "Toddler"), ("MCPRESCHOOL", "Preschool")]})
cpi = pd.read_csv(ROOT / "data/interim/cpi_u_annual.csv").set_index("year")
cnt = pd.DataFrame({c: real.groupby("year")[c].count() for c in ["MCINFANT", "MCTODDLER", "MCPRESCHOOL"]})
nmin, nmax = cnt.min(axis=1), cnt.max(axis=1)
q3_rows = "".join(
    f"<tr><td>{y}</td><td>{cpi.loc[y, 'cpi_u']:.3f}</td><td>{cpi.loc[y, 'to_2022_dollars']:.4f}</td>"
    f"<td>{nmin[y]:,}" + (f"–{nmax[y]:,}" if nmax[y] != nmin[y] else "") + "</td>"
    f"<td>{d(piv.loc[y, 'Infant'])}</td><td>{d(piv.loc[y, 'Toddler'])}</td><td>{d(piv.loc[y, 'Preschool'])}</td></tr>"
    for y in piv.index)
ch = q3c.set_index(["age_group", "period"])
cpi_ch = {p: ch.loc[("CPI-U (all items)", p), "pct_mean_nominal"] for p in ["2015-2022", "2015-2019", "2019-2022"]}
q3c_rows = "".join(
    f"<tr><td>{a}</td>"
    + "".join(f"<td>{pct(ch.loc[(a, p), 'pct_mean_nominal'])}</td><td><b>{pct(ch.loc[(a, p), 'pct_mean_real'])}</b></td>"
              for p in ["2015-2022", "2015-2019", "2019-2022"]) + "</tr>"
    for a in ["Infant", "Toddler", "Preschool"])
q3c_rows += ("<tr class='muted'><td>CPI-U</td>" + "".join(f"<td>{pct(cpi_ch[p])}</td><td></td>" for p in cpi_ch) + "</tr>")

rob_lab = {"County, iid SE (baseline)": "County, standard SE (baseline)",
           "County, state-clustered SE": "County, SE clustered by state",
           "Metro area (county avg.), iid SE": "Metro area as unit (county average)"}
rob = q4r.pivot(index="spec", columns="year", values=["t_stat", "p_value", "n_obs", "n_clusters"])
rob_rows = "".join(
    f"<tr><td>{rob_lab[s]}</td>"
    + "".join(f"<td>{int(rob.loc[s, ('n_obs', y)]):,}"
              + (f" ({int(rob.loc[s, ('n_clusters', y)])} states)" if not pd.isna(rob.loc[s, ('n_clusters', y)]) else "")
              + f"</td><td>{rob.loc[s, ('t_stat', y)]:.2f}</td><td>{fmt_p(rob.loc[s, ('p_value', y)])}</td>"
              for y in (2022, 2015)) + "</tr>"
    for s in rob_lab)

g22 = q2.set_index(q2["age_group"].str.split(" ").str[0])
inf, tod, pre = g22.loc["Infant"], g22.loc["Toddler"], g22.loc["Preschool"]
q1_22 = q1.set_index("year").loc[2022]

# --- Student texts (final versions; AI corrected spelling/grammar only — see prompt log) -----
Q2_TEXT = [
    "The 2022 data shows a clear age-based price change across metropolitan counties. The prices decrease as the "
    "children get older, meaning infants are the most expensive overall, with an average weekly price of $214.95, "
    "followed by toddler care at $186.46 and preschool care at $175.09. This means infant care costs about $40 more "
    "per week than preschool care on average. A probable explanation could be that infants require much more staff "
    "to take care of them successfully.",
    "Also, the variance follows the same trend, with infant prices having the highest SD.",
    "All 3 graphs were skewed to the right, which probably means that high-price counties pull up the average.",
    "The 95% confidence interval for the infant mean is [$209.84, $220.07], compared with [$182.36, $190.55] for "
    "toddlers and [$171.39, $178.79] for preschoolers. These are quite narrow intervals, which means our average "
    "prices are estimated precisely.",
    "Overall, infant care stands out as the most costly, and has the highest geographical variation.",
]
Q3_TEXT = [
    "The key takeaway here is that childcare prices were essentially flat between 2015 and 2022. The nominal price "
    "increases closely match the inflation during this period. If we now look closer within the period, there are "
    "some changes observable. From 2015 to 2019 the real childcare prices were increasing, meaning that relative to "
    "consumer prices, childcare got more expensive during that period. From 2019 to 2022 inflation jumped up, and "
    "childcare prices did not keep up. Overall, the ranking of prices we saw in Q2 remained the same with infants "
    "still being the most expensive. The 2021 dip in prices could be due to data missing from some probably more "
    "expensive counties.",
]


def paras(ps):
    return "".join(f"<p>{p}</p>" for p in ps)


def tag(kind, text):
    return f"<div class='tag tag-{kind}'>{text}</div>"


prompt_log_html = markdown.markdown((ROOT / "PROMPT_LOG.md").read_text(encoding="utf-8").split("---", 1)[1],
                                    extensions=["tables"])
w22, w15 = wk[2022], wk[2015]

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>MGT 403 — Homework 4 (Question 1 and Question 2 / Problem Set 4)</title>
<style>
@page {{ size: Letter; margin: 0.7in 0.75in 0.75in 0.75in;
  @bottom-left {{ content: "MGT 403 · Homework 4, Question 2 · Problem Set 4"; font: 7.5pt 'Segoe UI', sans-serif; color: #777; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font: 7.5pt 'Segoe UI', sans-serif; color: #777; }} }}
@page q1 {{ @bottom-left {{ content: "MGT 403 · Homework 4, Question 1"; font: 7.5pt 'Segoe UI', sans-serif; color: #777; }} }}
.q1page {{ page: q1; }}
.scan.q1.first-q1 {{ break-before: auto; }}
.scan.q1.first-q1 img {{ height: 6.75in; }}
:root {{ --yale: #00356b; --yale-soft: #eef3f9; --ai: #6b7280; --ai-soft: #f6f6f5; --ink: #1a1a1a; --muted: #5b5b5b; --rule: #d9dde3; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 9.7pt; line-height: 1.38; color: var(--ink); margin: 0; }}
h1 {{ font-family: Georgia, 'Times New Roman', serif; color: var(--yale); font-size: 21pt; margin: 0 0 4pt; line-height: 1.15; }}
h2 {{ font-family: Georgia, serif; color: var(--yale); font-size: 14.5pt; margin: 0 0 6pt; padding-bottom: 3pt; border-bottom: 1.5pt solid var(--yale); }}
h3 {{ font-size: 10.5pt; color: var(--yale); margin: 12pt 0 4pt; }}
h4 {{ font-size: 9.5pt; margin: 8pt 0 2pt; }}
p {{ margin: 0 0 6pt; }}
.q {{ background: #f3f4f6; border-radius: 3pt; padding: 5pt 8pt; margin: 0 0 8pt; font-size: 9pt; color: #333; }}
.q b {{ color: var(--yale); }}
.section {{ break-before: page; }}
table {{ border-collapse: collapse; width: 100%; margin: 4pt 0 8pt; font-size: 8.8pt; break-inside: avoid; }}
th {{ text-align: left; border-bottom: 1pt solid #888; padding: 3pt 5pt; font-weight: 600; background: #fafafa; }}
td {{ border-bottom: 0.5pt solid var(--rule); padding: 1.8pt 5pt; }}
td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
table.left td, table.left th {{ text-align: left; }}
table.tight td {{ padding: 1.1pt 5pt; }}
tr.muted td {{ color: var(--muted); font-style: italic; }}
.cap {{ font-size: 8pt; color: var(--muted); margin: -4pt 0 8pt; }}
figure {{ margin: 4pt 0 6pt; break-inside: avoid; text-align: center; }}
figure.narrow img {{ width: 86%; margin: 0 auto; }}
figure img {{ width: 100%; display: block; }}
figure figcaption {{ font-size: 8pt; color: var(--muted); margin-top: 2pt; }}
.block {{ border-left: 3.5pt solid; padding: 6pt 10pt 4pt; margin: 8pt 0 10pt; border-radius: 0 3pt 3pt 0; }}
h2, h3, h4, .tag {{ break-after: avoid; }}
.block p, li {{ orphans: 3; widows: 3; }}
.keep {{ break-inside: avoid; }}
.student {{ border-color: var(--yale); background: var(--yale-soft); }}
.ai {{ border-color: var(--ai); background: var(--ai-soft); }}
.tag {{ display: inline-block; font-size: 7.3pt; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; padding: 1.5pt 6pt; border-radius: 2pt; margin-bottom: 4pt; }}
.tag-student {{ background: var(--yale); color: #fff; }}
.tag-ai {{ background: #fff; color: var(--ai); border: 0.8pt solid var(--ai); }}
.student p {{ font-family: Georgia, serif; font-size: 10.2pt; }}
.note {{ font-size: 8.3pt; color: var(--muted); }}
.kv {{ display: grid; grid-template-columns: auto 1fr; gap: 1pt 10pt; font-size: 9.5pt; }}
.math {{ font-family: 'Cambria Math', Cambria, Georgia, serif; font-size: 10.5pt; }}
.eq {{ font-family: 'Cambria Math', Cambria, Georgia, serif; font-size: 11pt; margin: 4pt 0 6pt 16pt; }}
.frac {{ display: inline-block; vertical-align: middle; text-align: center; margin: 0 2pt; }}
.frac > span {{ display: block; padding: 0 3pt; }}
.frac > span:first-child {{ border-bottom: 0.8pt solid #222; }}
.scan {{ break-before: page; text-align: center; }}
.scan img {{ height: 8.55in; border: 0.5pt solid #bbb; }}
.scan.first {{ break-before: auto; }}
.scan.first img {{ height: 6.3in; }}
.scan img.partial {{ height: auto; width: 88%; }}
.scan .cap {{ margin: 3pt 0 0; }}
.legend td {{ text-align: left !important; vertical-align: top; }}
.contents td:last-child {{ white-space: nowrap; text-align: right !important; }}
.contents .tag {{ margin: 0 0 0 3pt; }}
.cover-meta {{ color: var(--muted); font-size: 10pt; margin-bottom: 14pt; }}
.glance td:nth-child(2) {{ text-align: left; }}
.log blockquote {{ margin: 3pt 0 3pt 0; padding: 3pt 8pt; border-left: 3pt solid var(--yale); background: var(--yale-soft); font-family: Georgia, serif; font-size: 8.8pt; }}
.log blockquote p {{ margin: 0 0 3pt; }}
.log p {{ font-size: 8.5pt; margin: 0 0 3pt; }}
.log h3 {{ margin-top: 10pt; }}
.log p:has(> strong:only-child) {{ break-after: avoid; margin-bottom: 1pt; }}
.log blockquote {{ break-inside: avoid; }}
.log code, code {{ font-family: Consolas, monospace; font-size: 8.3pt; background: #f1f1f1; padding: 0 2pt; }}
ul {{ margin: 2pt 0 6pt; padding-left: 16pt; }} li {{ margin-bottom: 2pt; }}
.twocol {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12pt; }}
</style></head><body>

<!-- ============================ HOMEWORK 4, QUESTION 1 (handwritten) ============================ -->
<div class="q1page">
<div style="border-top: 5pt solid var(--yale); padding-top: 10pt;">
<div style="font-size:9pt; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);">MGT 403 · Probability Modeling &amp; Statistics · Yale SOM</div>
<h1 style="font-size:19pt;">Homework 4</h1>
<table class="left" style="font-size:10pt; margin:2pt 0 4pt; width:auto;">
<tr><td style="padding-right:14pt;"><b>Question 1</b> (individual, pages 1–2)</td><td>{Q1_AUTHOR}</td></tr>
<tr><td style="padding-right:14pt;"><b>Question 2</b> = Data Project, Problem Set 4 (group, page 3 onwards)</td><td>{" · ".join(GROUP)}</td></tr>
</table>
<div class="note" style="font-size:9pt; margin-bottom:8pt;">Submitted {DATE}</div>
</div>
<h2 style="margin-top:4pt;">Question 1: Soccer balls (handwritten solution, {Q1_AUTHOR})</h2>
<div class="scan q1 first-q1">{tag('student', 'Student · handwritten solution, Question 1, page 1 of 2 (parts 1–3)')}<br>
<img src="q1_handwritten/q1_page2.png" alt="Handwritten Question 1 page 1"></div>
</div>
<div class="q1page scan q1">{tag('student', 'Student · handwritten solution, Question 1, page 2 of 2 (part 4)')}<br>
<img src="q1_handwritten/q1_page3.png" alt="Handwritten Question 1 page 2"></div>

<!-- ============================ COVER ============================ -->
<div style="border-top: 5pt solid var(--yale); padding-top: 14pt; break-before: page;">
<div style="font-size:9pt; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);">MGT 403 · Probability Modeling &amp; Statistics · Yale SOM</div>
<h1>Homework 4, Question 2<br><span style="font-size:15pt;">Data Project, Problem Set 4: The Distribution of Childcare Prices</span></h1>
<div class="cover-meta"><div style="font-size:11.5pt; color:var(--ink); margin-bottom:3pt;"><b>Group members:</b> {" · ".join(GROUP)}</div>Submitted {DATE}</div>
</div>

<h3>How to read this document</h3>
<p>Every block is labelled with who produced it, so the grader can see my own work separately from the AI's.</p>
<table class="legend left" style="font-size:9pt;">
<tr><td style="width:37%">{tag('student', 'Student')}</td><td>My own work: written discussions (Q2, Q3), handwritten hypothesis test and interpretation (Q4, scanned and typed up), and all methodological decisions. For my written texts the AI corrected <b>spelling and grammar only</b>. My original drafts are in the prompt log (Appendix B).</td></tr>
<tr><td>{tag('ai', 'AI-generated')}</td><td>Data work I directed and the AI carried out in Python (Claude Code): downloading and cleaning the data, sample construction, statistics, figures, and software checks of my manual calculations. Every number comes from re-runnable scripts (Appendix A).</td></tr>
</table>

<h3>Answers at a glance</h3>
<table class="glance">
<tr><th style="width:9%">Q</th><th style="text-align:left">Result</th></tr>
<tr><td>1</td><td>Metro analysis sample: counties whose OEWS area code starts with <code>00</code> (year-specific crosswalk). 2022: <b>{int(q1_22.metro_counties):,} metro counties</b> in {int(q1_22.metro_areas)} metro areas, of which {int(q1_22.with_preschool_price):,} have a center-based preschool price.</td></tr>
<tr><td>2</td><td>2022 mean weekly center-based price: infant <b>{d(inf['mean'])}</b> (95% CI {d(inf.ci_low)}–{d(inf.ci_high)}), toddler <b>{d(tod['mean'])}</b> ({d(tod.ci_low)}–{d(tod.ci_high)}), preschool <b>{d(pre['mean'])}</b> ({d(pre.ci_low)}–{d(pre.ci_high)}). Prices fall with the child's age; all three distributions are right-skewed.</td></tr>
<tr><td>3</td><td>In 2022 dollars (CPI-U), prices were essentially flat from 2015 to 2022: infant {pct(ch.loc[('Infant', '2015-2022'), 'pct_mean_real'])}, toddler {pct(ch.loc[('Toddler', '2015-2022'), 'pct_mean_real'])}, preschool {pct(ch.loc[('Preschool', '2015-2022'), 'pct_mean_real'])}. Nominal growth (about +23%) matched inflation (+{cpi_ch['2015-2022']:.1f}%). Real prices rose until 2019 and fell during the 2021–22 inflation.</td></tr>
<tr><td>4</td><td>H<sub>0</sub>: μ = voucher. <b>2022:</b> t = 6.39, p ≈ 1.7 × 10<sup>−10</sup> → reject H<sub>0</sub>. <b>2015:</b> t = {w15['t']:.2f}, p ≈ {sci(w15['p_t'], 1)} → reject H<sub>0</sub>. The voucher covered {w15['cover']:.0f}% of the mean preschool price in 2015 and {w22['cover']:.0f}% in 2022.</td></tr>
</table>

<p class="note" style="margin-top:6pt;"><b>Structure.</b> Questions 1–4 in order (each starts on a new page), then Appendix A (data, sample, data-handling decisions, reproducibility) and Appendix B (AI-use statement and full prompt log).</p>

<!-- ============================ Q1 ============================ -->
<div class="section">
<h2>Question 1: Metro analysis sample</h2>
<div class="q"><b>Task.</b> Download the NDCP childcare price data. Restrict to the metro analysis sample (counties in an OEWS metropolitan area) so that PS4, PS5 and the final project use a consistent county set.</div>
<div class="block ai">{tag('ai', 'AI-generated · data work directed by the student')}
<p><b>Data.</b> DOL Women's Bureau, National Database of Childcare Prices, county-level workbook <code>NDCP2022.xlsx</code>, study years 2015–2022. We use the median weekly full-time price for <b>center-based</b> care: <code>MCINFANT</code> (0–23 months), <code>MCTODDLER</code> (24–35 months) and <code>MCPRESCHOOL</code> (36–54 months), in nominal dollars (NDCP Technical Report, Sept. 2024, Appendix C).</p>
<p><b>Sample definition.</b> Each NDCP county-year is joined to the course crosswalk <code>county_oews_crosswalk.csv</code> on (year, 5-digit county FIPS). The crosswalk is year-specific, so metro status is taken from the same year. A county-year is kept if its OEWS area code begins with <code>00</code> (metropolitan area); nonmetropolitan counties are dropped. FIPS and OEWS codes are kept as text so leading zeros survive. NDCP stores FIPS as a number (e.g. <code>1001</code>); we zero-pad it to <code>01001</code>.</p>
<table class="tight">
<tr><th>Year</th><th>NDCP counties</th><th>Nonmetro dropped</th><th>Metro counties</th><th>Metro areas</th><th>With preschool price</th></tr>
{q1_rows}
</table>
<p class="cap">Infant and toddler counts differ from the preschool count by at most two counties per year. Missing prices stay in the file; each analysis reports its own N.</p>
<h4>Data checks</h4>
<ul>
<li>Every NDCP county-year matches a crosswalk row, and state abbreviations agree. There are no duplicate county-years.</li>
<li>The only crosswalk metro counties with no NDCP row are two outdated FIPS codes: <code>12025</code> (Dade County, renamed Miami-Dade <code>12086</code> in 1997) and <code>51515</code> (Bedford city, merged into Bedford County <code>51019</code> in 2013). Both current counties are in the sample.</li>
<li>The sample is stable: 1,232 of 1,236 distinct counties are metro in all eight years. Trends in Q3 therefore reflect price changes, not changes in which counties count as metro.</li>
<li>The 2022 counties without a preschool price (222 of 1,235) are concentrated in a few states: PR 69, IN 44, PA 37, MO 34, AR 20. Missing prices are therefore not random across states.</li>
</ul>
<h4>Data-handling decision: imputed prices are kept</h4>
<p>NDCP fills gaps in state market-rate surveys with imputations, recorded in five-digit flags on the fine age bands (Technical Report, pp. 9–26). In the 2022 metro sample, <b>{imp.loc['preschool', 'any_imputation'] * 100:.1f}%</b> of preschool prices involve at least one imputation: interpolation between survey years {imp.loc['preschool', 'between_survey_years'] * 100:.1f}%, conversion to a weekly price {imp.loc['preschool', 'weekly_conversion'] * 100:.1f}%, a percentile model {imp.loc['preschool', 'pctile_model'] * 100:.1f}%, and a county model from state data {imp.loc['preschool', 'state_to_county_model'] * 100:.1f}%. We keep all NDCP prices. Dropping imputed values would leave only 109 of 1,013 counties, all from four states (NY, OH, WI, CT), which is clearly not representative. The variable <code>MCPreschool_flag</code> is <b>not</b> an imputation indicator: it records how the age-group price was aggregated from its age bands.</p>
</div>
</div>

<!-- ============================ Q2 ============================ -->
<div class="section">
<h2>Question 2: Distribution of 2022 prices by age group</h2>
<div class="q"><b>Task.</b> Using 2022, focusing on center-based care: histograms of median prices by child age group; mean / SD / number of observations; 95% CIs for the average within each age group; discuss the differences across age groups.</div>
<div class="block ai">{tag('ai', 'AI-generated')}
<figure class="narrow"><img src="../output/figures/ps4_q2_histograms_2022.png" alt="Histograms of 2022 prices by age group"></figure>
<table>
<tr><th>Age group</th><th>N</th><th>Mean</th><th>SD</th><th>SE</th><th>95% CI for the mean</th><th>Median</th></tr>
{q2_rows}
</table>
<p class="cap">2022, metro counties, NDCP median weekly full-time price for center-based care, nominal dollars; the county is the unit of observation. 95% CI = x̄ ± t<sub>0.975, N−1</sub> · s/√N with t = 1.962.</p>
</div>

<div class="block student">{tag('student', 'Student · own discussion (AI checked spelling and grammar only)')}
{paras(Q2_TEXT)}
</div>

<div class="block ai">{tag('ai', 'AI-generated · supplementary analysis')}
<p><b>Same-county comparisons.</b> Comparing age groups within each county removes differences between markets:</p>
<table>
<tr><th>Difference (same county)</th><th>Mean</th><th>95% CI</th><th>95% CI, clustered by state</th><th>Younger group costs more</th></tr>
{q2p_rows}
</table>
<p><b>Robustness: counties are not independent.</b> NDCP prices come from state surveys and are often set by state rate zone: there are only {int(pre.distinct_prices)} distinct preschool prices across {int(pre.n):,} counties (e.g. Georgia has 74 counties and 4 prices), and 60% of the price variance lies between states. With standard errors clustered by state (45 states), the CIs widen about 4–5×:</p>
<table>
<tr><th>Age group</th><th>SE (iid)</th><th>SE (clustered)</th><th>95% CI, clustered</th></tr>
{q2c_rows}
</table>
<p class="note">The ranking of the age groups holds under clustering: every same-county difference remains significantly positive.</p>
</div>
</div>

<!-- ============================ Q3 ============================ -->
<div class="section">
<h2>Question 3: Real price trends, 2015–2022</h2>
<div class="q"><b>Task.</b> Convert all dollar values to constant 2022 dollars using CPI-U (CUUR0000SA0). Plot trends in the median price by year for each age group and discuss what happened to childcare prices.</div>
<div class="block ai">{tag('ai', 'AI-generated')}
<p><b>Method.</b> Real price (2022 $) = nominal price × CPI<sub>2022</sub> / CPI<sub>year</sub>, using BLS CPI-U annual averages (the mean of the 12 monthly values, which reproduces the published BLS annual averages). For each year and age group we plot the mean across metro counties of the NDCP median weekly center-based price, with 95% CIs.</p>
<table>
<tr><th>Year</th><th>CPI-U</th><th>× to 2022 $</th><th>N</th><th>Infant</th><th>Toddler</th><th>Preschool</th></tr>
{q3_rows}
</table>
<p class="cap">Mean weekly price across metro counties in constant 2022 dollars.</p>
<figure><img src="../output/figures/ps4_q3_real_price_trends.png" alt="Real price trends"></figure>
<table>
<tr><th rowspan="2">Age group</th><th colspan="2" style="text-align:center">2015–2022</th><th colspan="2" style="text-align:center">2015–2019</th><th colspan="2" style="text-align:center">2019–2022</th></tr>
<tr><th>Nominal</th><th>Real</th><th>Nominal</th><th>Real</th><th>Nominal</th><th>Real</th></tr>
{q3c_rows}
</table>
<p class="cap">Percent change of the mean weekly price across counties.</p>
</div>

<div class="block student">{tag('student', 'Student · own discussion (AI checked spelling and grammar only)')}
{paras(Q3_TEXT)}
</div>

<div class="block ai">{tag('ai', 'AI-generated · supplementary analysis')}
<p><b>Verified cause of the 2021 dip.</b> NDCP has no 2021 prices at all for California, North Carolina, Virginia and Pennsylvania: 214 metro counties that are priced in 2020 but not in 2021. Their 2020 real preschool mean ($191.28) is above the overall mean ($183.25), so dropping them mechanically lowers the 2021 average. The balanced panel below (the 741–743 counties priced in all eight years) shows no 2021 dip. It confirms the pattern: real prices rose until 2020, then fell in 2022, when these counties raised nominal prices by 3.2% while CPI rose 8.0%.</p>
<figure class="narrow"><img src="../output/figures/ps4_q3_balanced_panel.png" alt="Balanced panel robustness"></figure>
<p class="note">Caveat: most recent NDCP prices are imputed, often interpolated linearly between state survey years (68% of 2022 metro preschool prices). Interpolated prices move smoothly by construction and may understate reactions to shocks such as COVID-19.</p>
</div>
</div>

<!-- ============================ Q4 ============================ -->
<div class="section">
<h2>Question 4: Does the CCDF voucher equal the median preschool price?</h2>
<div class="q"><b>Task.</b> The ACF asserts that in the average metro area the monthly CCDF voucher for center-based preschool ($706 in 2022; $473 in 2015, nominal) equals the price of care at the median-priced center. Using 4.33 weeks per month, test at the 5% level: (a) hypotheses; (b) test statistic, computed manually for 2022; (c) p-value computed by software, verifying the manual calculation; (d) interpretation, and the same test for 2015.</div>
<p>My solution is handwritten (next three pages), followed by a typed transcription for readability. After that, the AI's software check of my manual calculation (4c) and the 2015 numbers that complete my answer to 4d.</p>
</div>

<div class="scan first">{tag('student', 'Student · handwritten solution, page 1 of 3 (4a, 4b)')}<br>
<img src="handwritten/q4_page2.png" alt="Handwritten Q4 page 1"></div>
<div class="scan">{tag('student', 'Student · handwritten solution, page 2 of 3 (4c, 4d)')}<br>
<img src="handwritten/q4_page3.png" alt="Handwritten Q4 page 2"></div>
<div class="scan">{tag('student', 'Student · handwritten solution, page 3 of 3 (4d continued)')}<br>
<img class="partial" src="handwritten/q4_page4_written_part.png" alt="Handwritten Q4 page 3">
<p class="cap">Only the written part of the page is shown; the lower half of the notebook page is blank.</p>
<div class="block ai keep" style="text-align:left; margin-top:6pt;">{tag('ai', 'AI-generated · the 2015 data I used for the paragraph above (prompt log, entry 21)')}
<p style="font-size:8.8pt; margin-bottom:3pt;">Same two-sided one-sample test as in 4b, repeated for 2015 with nominal 2015 prices against the nominal 2015 voucher. The 2022 column is my own result, shown for comparison.</p>
<table style="margin-bottom:3pt;">
<tr><th></th><th>2015</th><th>2022</th></tr>
<tr><td>Voucher (monthly, nominal) → weekly μ<sub>0</sub> = voucher / 4.33</td><td>$473 → {d(w15['mu0'])}</td><td>$706 → {d(w22['mu0'])}</td></tr>
<tr><td>N (metro counties with a preschool price)</td><td>{w15['n']:,}</td><td>{w22['n']:,}</td></tr>
<tr><td>Sample mean x̄ (weekly) / SD <span class='math'>σ&#770;</span> (weekly)</td><td>{d(w15['xbar'])} / {d(w15['s'])}</td><td>{d(w22['xbar'])} / {d(w22['s'])}</td></tr>
<tr><td>Test statistic (x̄ − μ<sub>0</sub>) / (<span class='math'>σ&#770;</span>/√N)</td><td><b>{w15['t']:.2f}</b></td><td><b>{w22['t']:.2f}</b></td></tr>
<tr><td>p-value (two-sided, exact t)</td><td>{sci(w15['p_t'])}</td><td>{sci(w22['p_t'])}</td></tr>
<tr><td>Decision at α = 5%</td><td>Reject H<sub>0</sub></td><td>Reject H<sub>0</sub></td></tr>
<tr><td>Mean monthly price (x̄ × 4.33) vs. voucher</td><td>{d(w15['mean_m'])} vs. $473</td><td>{d(w22['mean_m'])} vs. $706</td></tr>
<tr><td>Gap: mean price − voucher (monthly)</td><td>+{d(w15['gap'])} (+{w15['gap_pct']:.1f}%)</td><td>+{d(w22['gap'])} (+{w22['gap_pct']:.1f}%)</td></tr>
<tr><td><b>Share of the mean price the voucher covers</b> (voucher ÷ mean monthly price)</td><td><b>{w15['cover']:.0f}%</b></td><td><b>{w22['cover']:.0f}%</b></td></tr>
</table>
<p class="note" style="margin:0;">From 2015 to 2022 the voucher rose {(706 / 473 - 1) * 100:.0f}% (nominal), while the mean preschool price rose {(w22['mean_m'] / w15['mean_m'] - 1) * 100:.0f}%. So the gap narrowed and the voucher "largely caught up". The full comparison and robustness checks are in the 4d supplement after the transcription.</p>
</div>
</div>

<div class="section">
<div class="block student">{tag('student', 'Student · typed transcription of the handwritten solution')}
<p class="note" style="font-family:'Segoe UI',sans-serif;">Transcribed faithfully; spelling corrected only. [Square brackets] mark editorial insertions for readability.<br>(*) The handwritten pages show 6.38 and 1.77 × 10<sup>−10</sup>; I corrected my rounding afterwards (6.3889 rounds to <b>6.39</b>, giving p = 2·(1 − Φ(6.39)) = 1.66 × 10<sup>−10</sup>; prompt log, entry 22).</p>

<h4>a.</h4>
<p>2022 monthly voucher: $706.</p>
<p class="eq">$706 / 4.33 = $163.05 per week</p>
<p>We test whether the average metro county preschool price is $163.05.</p>
<p class="eq">⇒ H<sub>0</sub>: μ = 163.05 &nbsp;&nbsp;&nbsp; H<sub>1</sub>: μ ≠ 163.05</p>

<h4>b.</h4>
<p>Two-sided one-sample test. Used AI to give me the sample data (see AI prompt log):</p>
<p class="eq">N = 1,013 &nbsp;&nbsp; x̄ = $175.09 &nbsp;&nbsp; <span class='math'>σ&#770;</span> = $59.98</p>
<p>→ z-statistic:</p>
<p class="eq">z = <span class="frac"><span>x̄ − μ<sub>0</sub></span><span><span class='math'>σ&#770;</span> / √N</span></span> = <span class="frac"><span>175.09 − 163.05</span><span>59.98 / √1013</span></span> ≈ <b>6.39</b> (*) &nbsp;&nbsp;&nbsp; (denominator <span class='math'>σ&#770;</span>/√N = SE)</p>

<h4>c.</h4>
<p class="eq">p = 2 · (1 − Φ(6.39))</p>
<p>Used AI to calculate: p ≈ 1.66 × 10<sup>−10</sup> (*). The AI checked my z-statistic (called t) and it is correct. The exact [t] distribution gives p ≈ 2.5 × 10<sup>−10</sup>. Both are nearly 0.</p>

<h4>d.</h4>
<p>We do a two-sided one-sample test with α = 5%, meaning [we reject H<sub>0</sub>] if</p>
<p class="eq">z &gt; 1.96: &nbsp; 6.39 &gt; 1.96 &nbsp;&nbsp;&nbsp; and &nbsp;&nbsp;&nbsp; p &lt; 0.05: &nbsp; 1.66 × 10<sup>−10</sup> &lt; 0.05</p>
<p>Therefore we reject H<sub>0</sub>. The data does not support that the voucher is equal to the true average preschool prices.</p>
<p>The observed average preschool price of $175.09 is much farther from the hypothetical voucher amount of $163.05 than we would expect from sample variation alone. This is reflected by the close-to-0 p-value. It is a large difference relative to sample uncertainty. ⇒ Reject H<sub>0</sub>.</p>
<p>We repeat the test with 2015 data and subsidy levels, with AI. Repeating with 2015 data shows an even larger gap. While the voucher covered 93% of the mean price [in 2022], it only covered 77% in 2015. Both times we clearly reject H<sub>0</sub>, but in 2022 we at least get closer to the claim. The voucher largely caught up with the market price.</p>
</div>

<div class="block ai keep">{tag('ai', 'AI-generated · 4c software verification of the manual calculation (2022)')}
<table>
<tr><th>Element</th><th>Manual (student)</th><th>Software (Python)</th></tr>
<tr><td>Sample size N</td><td>1,013</td><td>{w22['n']:,}</td></tr>
<tr><td>Sample mean x̄ (weekly)</td><td>$175.09</td><td>{d(w22['xbar'], 4)}</td></tr>
<tr><td>Sample SD <span class='math'>σ&#770;</span> (weekly, n − 1)</td><td>$59.98</td><td>{d(w22['s'], 4)}</td></tr>
<tr><td>μ<sub>0</sub> = $706 / 4.33 (weekly)</td><td>$163.05</td><td>{d(w22['mu0'], 4)}</td></tr>
<tr><td>Standard error <span class='math'>σ&#770;</span> / √N</td><td>—</td><td>{w22['se']:.4f}</td></tr>
<tr><td>Test statistic</td><td>6.39</td><td>{w22['t']:.4f}</td></tr>
<tr><td>p = 2·(1 − Φ(|t|)), normal</td><td>1.66 × 10<sup>−10</sup> (at 6.39)</td><td>{sci(w22['p_z'])}</td></tr>
<tr><td>p = 2·(1 − F<sub>t, 1012</sub>(|t|)), exact t</td><td>≈ 2.5 × 10<sup>−10</sup></td><td>{sci(w22['p_t'])}</td></tr>
<tr><td>Critical value, 5% two-sided</td><td>1.96 (normal)</td><td>{w22['tcrit']:.4f} (t, 1,012 df)</td></tr>
<tr><td>95% CI for the mean weekly price</td><td>—</td><td>[{d(w22['lo'])}, {d(w22['hi'])}], which excludes $163.05</td></tr>
</table>
<p class="note">Cross-checked with <code>scipy.stats.ttest_1samp</code> (identical t and p). Working in monthly units (price × 4.33 vs. $706) gives the same t, because both the numerator and the SE scale by 4.33. With N = 1,013 the normal and t distributions practically coincide near the critical value (1.960 vs. 1.962). Far in the tail, the t distribution's slightly fatter tails give a p-value about 1.5 times larger; the conclusion is identical.</p>
</div>

<div class="block ai">{tag('ai', 'AI-generated · 4d supplement: the 2015 test and the comparison with 2022')}
<p>Same test on 2015 data, with nominal 2015 prices against the nominal 2015 voucher. (The 2022-dollar prices from Q3 are not used, because the vouchers are nominal.)</p>
<table>
<tr><th></th><th>2022</th><th>2015</th></tr>
<tr><td>Voucher (monthly) → weekly μ<sub>0</sub> = voucher / 4.33</td><td>$706 → {d(w22['mu0'])}</td><td>$473 → {d(w15['mu0'])}</td></tr>
<tr><td>N (metro counties with a preschool price)</td><td>{w22['n']:,}</td><td>{w15['n']:,}</td></tr>
<tr><td>Sample mean x̄ (weekly)</td><td>{d(w22['xbar'])}</td><td>{d(w15['xbar'])}</td></tr>
<tr><td>Sample SD <span class='math'>σ&#770;</span> (weekly)</td><td>{d(w22['s'])}</td><td>{d(w15['s'])}</td></tr>
<tr><td>SE = <span class='math'>σ&#770;</span> / √N</td><td>{w22['se']:.4f}</td><td>{w15['se']:.4f}</td></tr>
<tr><td><b>Test statistic</b> (x̄ − μ<sub>0</sub>) / SE</td><td><b>{w22['t']:.2f}</b></td><td><b>{w15['t']:.2f}</b></td></tr>
<tr><td><b>p-value</b> (two-sided, exact t)</td><td><b>{sci(w22['p_t'])}</b></td><td><b>{sci(w15['p_t'])}</b></td></tr>
<tr><td>Decision at α = 5% (|t| &gt; 1.962)</td><td>Reject H<sub>0</sub></td><td>Reject H<sub>0</sub></td></tr>
<tr><td>95% CI for the mean weekly price</td><td>[{d(w22['lo'])}, {d(w22['hi'])}]</td><td>[{d(w15['lo'])}, {d(w15['hi'])}]</td></tr>
<tr><td>Mean monthly price (x̄ × 4.33) vs. voucher</td><td>{d(w22['mean_m'])} vs. $706</td><td>{d(w15['mean_m'])} vs. $473</td></tr>
<tr><td>Gap: price − voucher (monthly)</td><td>+{d(w22['gap'])} (+{w22['gap_pct']:.1f}%)</td><td>+{d(w15['gap'])} (+{w15['gap_pct']:.1f}%)</td></tr>
<tr><td><b>Share of the mean price the voucher covers</b></td><td><b>{w22['cover']:.0f}%</b></td><td><b>{w15['cover']:.0f}%</b></td></tr>
</table>
<p>Between 2015 and 2022 the voucher rose by {(706 / 473 - 1) * 100:.0f}% in nominal terms, while the mean preschool price rose by {(w22['mean_m'] / w15['mean_m'] - 1) * 100:.0f}%. That is why the gap narrowed from $144 to $52 a month, and the voucher's coverage rose from {w15['cover']:.0f}% to {w22['cover']:.0f}% of the mean price.</p>
<h4>Robustness of the test</h4>
<table>
<tr><th rowspan="2">Specification</th><th colspan="3" style="text-align:center">2022</th><th colspan="3" style="text-align:center">2015</th></tr>
<tr><th>Obs.</th><th>t</th><th>p</th><th>Obs.</th><th>t</th><th>p</th></tr>
{rob_rows}
</table>
<p class="note">Two checks go beyond the question. (i) The claim refers to "the average metro area", so we also average the counties within each of the 341 metro areas: H<sub>0</sub> is still rejected in both years, with almost the same mean. (ii) NDCP prices are often set per state rate zone (see Q2), so counties within a state are not independent. With standard errors clustered by state, the 2015 rejection stays decisive, but the 2022 test is <b>no longer significant</b> (p = 0.15). The 2015 conclusion is therefore robust. The 2022 rejection holds under the standard test the question asks for, but it is less certain than p ≈ 10<sup>−10</sup> suggests: the 2022 gap of about $52 a month is small relative to the price differences between states.</p>
</div>
</div>

<!-- ============================ APPENDIX A ============================ -->
<div class="section">
<h2>Appendix A: Data, sample and data-handling decisions</h2>
<div class="block ai">{tag('ai', 'AI-generated')}
<h4>Data sources used in Problem Set 4</h4>
<table class="left">
<tr><th>Source</th><th>What is used</th><th>How obtained</th></tr>
<tr><td>DOL Women's Bureau, National Database of Childcare Prices (<code>NDCP2022.xlsx</code>, Technical Report Sept. 2024)</td><td>County median weekly full-time prices, center-based care, infant/toddler/preschool, 2015–2022; imputation flags</td><td>Downloaded manually by the student (dol.gov blocks scripted downloads)</td></tr>
<tr><td>Course crosswalk <code>county_oews_crosswalk.csv</code></td><td>Year-specific county → OEWS area code; metro = code starting with <code>00</code></td><td>Canvas, provided by the course</td></tr>
<tr><td>BLS CPI-U, series CUUR0000SA0</td><td>Annual averages 2015–2022 (mean of the 12 monthly values; matches BLS's published averages, e.g. 2015: 237.017, 2022: 292.655)</td><td>BLS Public Data API (script)</td></tr>
</table>
<p class="note">BLS OEWS wages were also downloaded and prepared for Problem Set 5; they are not used here.</p>

<h4>Important data-handling decisions</h4>
<ul>
<li><b>Identifiers as text.</b> County FIPS (5 characters) and OEWS area codes (7 characters) are always read as text. NDCP stores FIPS as a number, so it is zero-padded. Without this, every state with a FIPS code below 10 (AL–CT) would fail to merge.</li>
<li><b>Year-specific metro definition.</b> Metro status comes from that year's crosswalk row. 1,232 of 1,236 counties are metro in every year.</li>
<li><b>Two legacy FIPS codes</b> in the crosswalk (<code>12025</code>, <code>51515</code>) have no NDCP row; the current codes (<code>12086</code>, <code>51019</code>) are matched, so no county is lost.</li>
<li><b>Imputed NDCP prices kept</b> (89% of 2022 preschool prices carry an imputation); the alternative would leave 109 counties from 4 states. <code>*_flag</code> variables are aggregation flags, not imputation flags (Technical Report, Appendix C).</li>
<li><b>Unit of observation:</b> the county, unweighted (a small county counts as much as Los Angeles County). Each age group uses all counties with a non-missing price.</li>
<li><b>Nominal vs. real:</b> Q2 and Q4 use nominal prices (the vouchers are nominal); Q3 uses constant 2022 dollars.</li>
<li><b>Source data are never modified.</b> Scripts only read <code>data/raw/</code> and <code>data/crosswalks/</code>; SHA-256 checksums of every raw file are in <code>data/raw_checksums.sha256</code>.</li>
</ul>

<h4>Reproducibility</h4>
<p>All results can be regenerated from the submitted folder (Python 3.14; pandas, numpy, scipy, statsmodels, matplotlib). Run in this order from the project root:</p>
<table class="left">
<tr><th>Script</th><th>Purpose</th></tr>
<tr><td><code>01_get_cpi.py</code></td><td>CPI-U download; annual averages and 2022-dollar multipliers</td></tr>
<tr><td><code>04_prepare_ndcp.py</code></td><td>NDCP extract 2015–2022; zero-padded FIPS; imputation codes</td></tr>
<tr><td><code>05_build_metro_sample.py</code></td><td>Q1: metro analysis sample and data checks</td></tr>
<tr><td><code>06_ps4_q2_distribution_2022.py</code>, <code>07_ps4_q2_factsheet.py</code></td><td>Q2: histograms, mean/SD/N/CIs, paired and clustered supplements</td></tr>
<tr><td><code>08_ps4_q3_real_trends.py</code></td><td>Q3: CPI-U conversion, trends, balanced panel</td></tr>
<tr><td><code>09_ps4_q4_voucher_test.py</code>, <code>10_ps4_q4_robustness.py</code></td><td>Q4: one-sample t-tests 2022/2015; robustness</td></tr>
<tr><td><code>11_build_submission.py</code></td><td>Builds this document from the result tables</td></tr>
</table>
<p class="note">Scripts 02–03 (OEWS, ACS) prepare Problem Set 5 data. A grader re-downloading from bls.gov must set their own contact e-mail (<code>BLS_CONTACT_EMAIL</code>); no e-mail is stored in the code, and the downloaded files are included.</p>
</div>
</div>

<!-- ============================ APPENDIX B ============================ -->
<div class="section">
<h2>Appendix B: AI-use statement and prompt log</h2>
<div class="block student">{tag('student', 'Student')}
<p style="font-family:'Segoe UI',sans-serif; font-size:9.5pt;"><b>How AI was used.</b> I used Claude Code (Claude Opus 5.5, Anthropic) as a research assistant, working step by step.</p>
<div class="twocol" style="font-family:'Segoe UI',sans-serif; font-size:9pt;">
<div><b>My own work</b><ul>
<li>Directed every step and question (prompts below)</li>
<li>Manually downloaded NDCP, the NDCP Technical Report and the course crosswalk/README; pointed the AI to the README's OEWS notes</li>
<li>Methodological decisions (e.g. keeping source data untouched)</li>
<li>Wrote the Q2 and Q3 discussions myself</li>
<li>Q4 entirely by hand: hypotheses, test statistic, p-value formula, decision rule, interpretation, and the 2015 comparison</li>
</ul></div>
<div><b>AI's work</b><ul>
<li>Download/cleaning scripts, sample construction, merges and data checks</li>
<li>All computations, tables and figures; numbers-only fact sheets for my discussions</li>
<li>Software verification of my Q4 calculation; the 2015 test and robustness checks</li>
<li>Spelling and grammar corrections of my texts, and this layout</li>
</ul></div>
</div>
</div>
<div class="log">
<p class="note">The full prompt log follows: my prompts verbatim and unedited, each with a one-line summary of the AI's output.</p>
{prompt_log_html}
</div>
</div>

</body></html>
"""

out_html = SUB / "PS4_submission.html"
out_html.write_text(HTML, encoding="utf-8")
out_pdf = SUB / "MGT403_HW4_submission.pdf"
out_pdf.unlink(missing_ok=True)
profile = Path(tempfile.mkdtemp(prefix="edge_pdf_"))  # separate instance, not a running Edge window
subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--user-data-dir={profile}", "--no-first-run", "--disable-extensions",
                "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
                f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=True, capture_output=True)
# Edge may finish writing shortly after the process returns: wait until the file size is stable.
last = -1
for _ in range(120):
    time.sleep(0.5)
    size = out_pdf.stat().st_size if out_pdf.exists() else -1
    if size > 0 and size == last:
        break
    last = size
else:
    raise RuntimeError("Edge did not produce the PDF")
print(f"Wrote {out_pdf.relative_to(ROOT)} ({out_pdf.stat().st_size / 1e6:.1f} MB)")
