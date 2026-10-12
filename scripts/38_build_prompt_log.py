"""Build the prompt logs in the submitted format: the team's prompts only, verbatim (typos included), no AI output.

Sources (the detailed working logs, kept outside the submission in archive/):
  archive/PROMPT_LOG_PS4_detailed.md       Problem Set 4 (29-30 Sep 2026)
  hw5/PROMPT_LOG_HW5_Q3_submission.md      Problem Set 5, Question 3 (6 Oct 2026; already prompts only)
  archive/PROMPT_LOG_PROJECT_detailed.md   Pre-analysis and final project (10-11 Oct 2026)
Outputs:
  PROMPT_LOG.md, hw5/PROMPT_LOG_HW5_Q3.md, project/PROMPT_LOG_PROJECT.md   prompts-only working logs
  project/submission/MGT403_Prompt_Log.md / .html / .pdf                    combined log for the grader
The Census API key never appears (checked at the end).
"""
import html
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "project/submission"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
TEAM = "Carson Tavares · Lee Itzhaki · Vusala Suleymanova · Philipp Romberg"
TOOL = "Claude Code (desktop app), model Claude Opus 5.5, Anthropic"
URL = "https://claude.ai/code"
read = lambda p: (ROOT / p).read_text(encoding="utf-8")


EMAIL_RE = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"


def quote_text(block):
    """'> ...' lines -> plain text (keeps line breaks)."""
    text = "\n".join(re.sub(r"^> ?", "", l) for l in block.strip().splitlines()).strip()
    return re.sub(EMAIL_RE, "[e-mail redacted]", text)  # no personal e-mail addresses in the published log


# ---------------- Problem Set 4 ------------------------------------------------------------------------------------------
ps4_src = read("archive/PROMPT_LOG_PS4_detailed.md")
ps4 = []  # (section, text)
section = None
for chunk in re.split(r"\n(?=### |\*\*\d+\.\*\*)", ps4_src):
    if chunk.startswith("### "):
        section = chunk.splitlines()[0][4:].strip()
        continue
    m = re.match(r"\*\*(\d+)\.\*\*\n(.*?)(?:\n\n\*AI output:\*.*)?$", chunk.strip(), flags=re.S)
    if m:
        ps4.append((section, quote_text(m.group(2))))
assert len(ps4) == 23, len(ps4)

# ---------------- Problem Set 5, Question 3 ---------------------------------------------------------------------------------
ps5_src = read("hw5/PROMPT_LOG_HW5_Q3_submission.md")
ps5 = [quote_text(b) for b in re.findall(r"\*\*\d+\.\*\*\n(.*?)(?=\n\n\n\*\*\d+\.\*\*|\Z)", ps5_src, flags=re.S)]
assert len(ps5) == 21, len(ps5)

# ---------------- Pre-analysis and final project -----------------------------------------------------------------------------
pj_src = read("archive/PROMPT_LOG_PROJECT_detailed.md")
ents = re.findall(r"## Prompt (\d+): [^\n]+\n\n\*\*Prompt \(verbatim(?:, ([^)]*))?\):\*\*\n(.*?)\n\n(?:\*\*What the AI did|---)", pj_src, flags=re.S)
pj, seen = [], set()
FIRST_ATTEMPT = ("No we want to do Pre-Analysis Project Data Work", "All variables. follow the suggestions",
                 "we only have to do own word write ups for 3 and 4")
# prompts in which the team chose between options laid out by the AI (working-log numbers)
DECISIONS = {10, 23, 24, 25, 26, 28, 38, 43, 51, 53, 57}
for n, kind, body in ents:
    t = quote_text(body)
    if t in seen:  # the same prompt recorded twice in the working log
        continue
    seen.add(t)
    if t.startswith(FIRST_ATTEMPT):  # first pre-analysis attempt, restarted from scratch (team decision: not in the log)
        continue
    t = re.sub(r"^\*\((.*?)\)\*", lambda m_: f"[Attachment: {m_.group(1)}]", t, flags=re.S)
    if "own text" in (kind or ""):
        tag = "own text"
    elif t.startswith("we want to find the top 10 most attractive counties"):
        tag = "own idea"  # the team's guiding ideas for the selection
    elif int(n) in DECISIONS and not t.startswith("No we want"):
        tag = "decision"
    else:
        tag = ""
    pj.append({"n": int(n), "text": t, "team": tag})
# phases (in order of the working log) with dates
PHASES = [("Setting up the prompt log", "10 October 2026", lambda i, e: i < 2),
          ("Pre-analysis: tasks 1–4", "10 October 2026", lambda i, e: 2 <= i and e["n"] <= 19),
          ("Final project analysis: model, selection, reliability, stability, missing factors", "10 October 2026", lambda i, e: 20 <= e["n"] <= 32),
          ("Presentation: story, visuals and slide design", "10 October 2026", lambda i, e: 33 <= e["n"] <= 44),
          ("Presentation: design refinements", "11 October 2026", lambda i, e: 45 <= e["n"] <= 53),
          ("Number check, public pre-K check, appendix", "11 October 2026", lambda i, e: e["n"] == 54),
          ("Submission documents", "11 October 2026", lambda i, e: e["n"] >= 55)]
for i, e in enumerate(pj):
    e["phase"] = next(k for k, (_, _, f) in enumerate(PHASES) if f(i, e))
RESULTS = ["This prompt log",
           "Pre-analysis and appendix, Part I (tasks 1–4)",
           "Slides 1–6; Pre-analysis and appendix, Part II (Appendix 0, A–F)",
           "Slide deck (structure, figures, design)",
           "Slide deck (design)",
           "Slides (number corrections, public pre-K); Pre-analysis and appendix, Part II",
           "Pre-analysis and appendix (combined document, title pages)"]

# ---------------- write prompts-only working logs --------------------------------------------------------------------------------
def md_quote(t):
    return "\n".join("> " + l if l else ">" for l in t.splitlines())


NOTE = ("This log lists **every prompt we gave the AI**, verbatim and unedited (typos included). It contains no AI output: what the AI "
        "produced is shown in the submitted documents. The Census API key and a personal e-mail address are redacted.")
ps4_md = [f"# AI Prompt Log: Problem Set 4\n\n**Tool:** {TOOL}, {URL}, 29–30 September 2026.\n"
          "**Scope:** MGT 403, Homework 4, Question 2 = Data Project Problem Set 4, “The Distribution of Childcare Prices”.\n\n" + NOTE + "\n\n---"]
sec = None
for k, (s_, t) in enumerate(ps4, 1):
    if s_ != sec:
        ps4_md.append(f"\n### {s_}")
        sec = s_
    ps4_md.append(f"\n**{k}.**" + (" *(team's own text)*" if k in (8, 10, 12, 13) else "") + f"\n{md_quote(t)}")
(ROOT / "PROMPT_LOG.md").write_text("\n".join(ps4_md) + "\n", encoding="utf-8")
(ROOT / "hw5/PROMPT_LOG_HW5_Q3.md").write_text(ps5_src, encoding="utf-8")
pj_md = [f"# AI Prompt Log: Pre-Analysis and Final Project\n\n**Tool:** {TOOL}, {URL}, 10–11 October 2026.\n**Team:** {TEAM}\n\n" + NOTE + "\n\n---"]
ph = None
for k, e in enumerate(pj, 1):
    if e["phase"] != ph:
        ph = e["phase"]
        pj_md.append(f"\n### {PHASES[ph][0]} ({PHASES[ph][1]})\n*Results in: {RESULTS[ph]}*")
    pj_md.append(f"\n**{k}.**" + ((" *(team decision)*" if e["team"] == "decision" else f" *(team's {e['team']})*") if e["team"] else "") + f"\n{md_quote(e['text'])}")
(ROOT / "project/PROMPT_LOG_PROJECT.md").write_text("\n".join(pj_md) + "\n", encoding="utf-8")

# ---------------- combined document ---------------------------------------------------------------------------------------------
PARTS = [
    ("1", "Problem Set 4", "The distribution of childcare prices: data collection, NDCP prices, CPI, voucher test", "29–30 September 2026", len(ps4),
     "Submitted PS4 document"),
    ("2", "Problem Set 5, Question 3", "Cost drivers: ACS via Census API, OEWS wages to counties, descriptives, real trends, tests, regression", "6 October 2026",
     len(ps5), "Submitted PS5 document"),
    ("3", "Pre-analysis and final project", "Pre-analysis tasks 1–4; selection model, checks, slides, appendix", "10–11 October 2026", len(pj),
     "Slide deck; Pre-analysis and appendix"),
]


def prompt_html(num, text, team=""):
    t = html.escape(text).replace("\n", "<br>")
    t = re.sub(r"\[Attachment: (.*?)\]", r"<span class='att'>Attachment: \1</span>", t, flags=re.S)
    team = "own text" if team is True else team
    badge = (f"<span class='teamtag decision'>team decision</span>" if team == "decision"
             else f"<span class='teamtag'>team's {team}</span>" if team else "")
    return f"<div class='prompt'><div class='pnum'>{num}</div><div class='ptext'>{badge}{t}</div></div>"


body = []
body.append(f"""
<div class='cover'>
  <div class='kicker'>MGT 403 · Probability Modeling &amp; Statistics · Yale SOM · Data Project</div>
  <h1>AI prompt log</h1>
  <div class='subtitle'>Where should we open our next preschool? · every prompt we gave the AI, from Problem Set 4 to the final project</div>
  <div class='team'>{TEAM}</div>
</div>
<table class='meta'>
<tr><td>Tool</td><td>{TOOL}</td></tr>
<tr><td>URL</td><td>{URL}</td></tr>
<tr><td>Dates of access</td><td>29–30 September, 6 October, 10–11 October 2026 (per part and section below)</td></tr>
<tr><td>Content</td><td>All prompts, verbatim and unedited (typos included), in the order given. No AI output: what the AI produced is in the
submitted documents. Attachments are named in brackets. The Census API key and a personal e-mail address are redacted.</td></tr>
<tr><td>Not included</td><td>Homework 5, Questions 1–2 (individual homework on stock returns and gelato sales, not part of the data project).</td></tr>
</table>
<h3>Overview</h3>
<table class='ov'><tr><th>Part</th><th>Scope</th><th>Dates</th><th>Prompts</th><th>Results in</th></tr>
{''.join(f"<tr><td><b>{p} · {t}</b></td><td>{s}</td><td>{d}</td><td class='r'>{n}</td><td>{w}</td></tr>" for p, t, s, d, n, w in PARTS)}
<tr><td><b>Total</b></td><td></td><td></td><td class='r'><b>{len(ps4) + len(ps5) + len(pj)}</b></td><td></td></tr></table>
<p class='note'>Prompts marked <span class='teamtag'>team's own text</span> contain interpretations the team wrote itself; the submitted versions differ only
by spelling and grammar corrections the AI made on request. <span class='teamtag'>team's own idea</span> marks the team's guiding ideas for the county
selection, which the whole final analysis is built on. <span class='teamtag decision'>team decision</span> marks prompts in which the team chose between
options the AI had laid out (the decisions are explained in Appendix D). Each phase of Part 3 names the document where its results appear. Numbering restarts in each part (1.1, 2.1, 3.1, …).</p>
""")


def part_head(no, title, dates, n, desc):
    return (f"<div class='part'><div class='eyebrow'>Part {no} · {dates} · {n} prompts</div><h2>{title}</h2><p class='pdesc'>{desc}</p>")


body.append(part_head("1", "Problem Set 4", "29–30 September 2026", len(ps4), PARTS[0][2] + "."))
sec = None
for k, (s_, t) in enumerate(ps4, 1):
    if s_ != sec:
        body.append(f"<h3>{s_}</h3>")
        sec = s_
    body.append(prompt_html(f"1.{k}", t, team=k in (8, 10, 12, 13)))  # discussions Q2, Q3 written by the team
body.append("</div>")
body.append(part_head("2", "Problem Set 5, Question 3", "6 October 2026", len(ps5), PARTS[1][2] + "."))
for k, t in enumerate(ps5, 1):
    body.append(prompt_html(f"2.{k}", t, team=k in (9, 11, 15, 18, 20)))  # team answers tasks 6-7
body.append("</div>")
body.append(part_head("3", "Pre-analysis and final project", "10–11 October 2026", len(pj), PARTS[2][2] + "."))
ph = None
for k, e in enumerate(pj, 1):
    if e["phase"] != ph:
        ph = e["phase"]
        body.append(f"<h3>{PHASES[ph][0]} <span class='date'>{PHASES[ph][1]}</span></h3><div class='results'>Results in: {RESULTS[ph]}</div>")
    body.append(prompt_html(f"3.{k}", e["text"], e["team"]))
body.append("</div>")

CSS = """
@page { size: Letter; margin: 0.72in 0.75in 0.78in 0.75in;
  @bottom-left { content: "MGT 403 · Where should we open our next preschool? · AI prompt log"; font: 7pt 'Segoe UI', sans-serif; color: #86868b; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7pt 'Segoe UI', sans-serif; color: #86868b; } }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
:root { --accent: #2b6cd0; --tint: #eef4fc; --card: #f5f5f7; --ink: #1d1d1f; --ink2: #6e6e73; --muted: #86868b; --line: #e5e5ea; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.2pt; line-height: 1.42; color: var(--ink); margin: 0; }
h1 { font-size: 30pt; font-weight: 600; letter-spacing: -0.02em; margin: 6pt 0 6pt; }
h2 { font-size: 18pt; font-weight: 600; margin: 2pt 0 4pt; }
h3 { font-size: 10.4pt; font-weight: 600; margin: 14pt 0 6pt; break-after: avoid; }
h3 .date { font-weight: 400; color: var(--muted); font-size: 8.5pt; margin-left: 6pt; }
.cover { padding-top: 26pt; border-top: 4pt solid var(--accent); margin-bottom: 16pt; }
.kicker { font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: var(--ink2); font-weight: 600; }
.subtitle { font-size: 12pt; color: var(--ink2); margin-bottom: 8pt; }
.team { font-size: 9pt; color: var(--ink2); }
table { width: 100%; border-collapse: collapse; font-size: 8.6pt; margin: 4pt 0 8pt; }
td, th { padding: 4pt 6pt; border-bottom: 0.5pt solid var(--line); vertical-align: top; text-align: left; }
th { font-size: 7.2pt; text-transform: uppercase; letter-spacing: .04em; color: var(--ink2); border-bottom: 0.9pt solid var(--ink2); }
table.meta td:first-child { width: 18%; font-weight: 600; color: var(--ink2); }
td.r { text-align: right; }
.note { font-size: 7.9pt; color: var(--ink2); }
.part { break-before: page; }
.eyebrow { font-size: 8pt; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: var(--accent); }
.pdesc { color: var(--ink2); margin: 0 0 6pt; }
.prompt { display: flex; gap: 10pt; margin: 0 0 7pt; break-inside: avoid; }
.pnum { flex: 0 0 34pt; font-weight: 600; color: var(--accent); font-size: 8.6pt; padding-top: 5pt; text-align: right; }
.ptext { flex: 1; background: var(--card); border-radius: 6pt; padding: 5pt 9pt; font-size: 8.8pt; line-height: 1.4; word-wrap: break-word; }
.teamtag { display: inline-block; border: 0.8pt solid var(--accent); color: var(--accent); font-size: 6.8pt; font-weight: 600;
           border-radius: 8pt; padding: 0 6pt; margin-right: 6pt; }
.att { color: var(--ink2); font-style: italic; }
.results { font-size: 7.8pt; color: var(--ink2); margin: -3pt 0 7pt 44pt; }
.teamtag.decision { border-color: var(--ink2); color: var(--ink2); }
"""
HTML = f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>MGT 403 AI prompt log</title><style>{CSS}</style></head><body>{''.join(body)}</body></html>"

# combined markdown (same content)
md = [f"# MGT 403 Data Project: AI Prompt Log\n\n**Team:** {TEAM}  \n**Tool:** {TOOL}  \n**URL:** {URL}  \n"
      "**Dates of access:** 29–30 September, 6 October, 10–11 October 2026\n\n" + NOTE +
      " Homework 5, Questions 1–2 are not part of the data project and are not included.\n"]
md.append(f"\n## Part 1 · Problem Set 4 (29–30 September 2026)")
sec = None
for k, (s_, t) in enumerate(ps4, 1):
    if s_ != sec:
        md.append(f"\n### {s_}")
        sec = s_
    md.append(f"\n**1.{k}**" + (" *(team's own text)*" if k in (8, 10, 12, 13) else "") + f"\n{md_quote(t)}")
md.append(f"\n## Part 2 · Problem Set 5, Question 3 (6 October 2026)")
for k, t in enumerate(ps5, 1):
    md.append(f"\n**2.{k}**" + (" *(team's own text)*" if k in (9, 11, 15, 18, 20) else "") + f"\n{md_quote(t)}")
md.append(f"\n## Part 3 · Pre-analysis and final project (10–11 October 2026)")
ph = None
for k, e in enumerate(pj, 1):
    if e["phase"] != ph:
        ph = e["phase"]
        md.append(f"\n### {PHASES[ph][0]} ({PHASES[ph][1]})\n*Results in: {RESULTS[ph]}*")
    md.append(f"\n**3.{k}**" + ((" *(team decision)*" if e["team"] == "decision" else f" *(team's {e['team']})*") if e["team"] else "") + f"\n{md_quote(e['text'])}")
(SUB / "MGT403_Prompt_Log.md").write_text("\n".join(md) + "\n", encoding="utf-8")

# key check
key_file = ROOT / "census_api_key.txt"
if key_file.exists():
    key = key_file.read_text().strip()
    for f in [ROOT / "PROMPT_LOG.md", ROOT / "hw5/PROMPT_LOG_HW5_Q3.md", ROOT / "project/PROMPT_LOG_PROJECT.md", SUB / "MGT403_Prompt_Log.md"]:
        assert key not in f.read_text(encoding="utf-8"), f
        assert not re.search(EMAIL_RE, f.read_text(encoding="utf-8")), f"e-mail address in {f}"
    assert key not in HTML
assert not re.search(EMAIL_RE, HTML), "e-mail address in the prompt log"

out_html = SUB / "MGT403_Prompt_Log.html"
out_html.write_text(HTML, encoding="utf-8")
out_pdf = SUB / "MGT403_Prompt_Log.pdf"
out_pdf.unlink(missing_ok=True)
profile = Path(tempfile.mkdtemp(prefix="edge_pdf_"))
subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}", "--no-first-run",
                "--disable-extensions", "--virtual-time-budget=10000", f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=True, capture_output=True)
last = -1
for _ in range(120):
    time.sleep(0.5)
    size = out_pdf.stat().st_size if out_pdf.exists() else -1
    if size > 0 and size == last:
        break
    last = size
print(f"PS4 {len(ps4)}, PS5 Q3 {len(ps5)}, project {len(pj)} prompts; phases:",
      {PHASES[k][0][:25]: sum(e['phase'] == k for e in pj) for k in range(len(PHASES))})
