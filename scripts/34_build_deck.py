"""Build the final-project slide deck (PowerPoint, 16:9) in a clean, Apple-inspired style.

Design system: white canvas, generous margins, Segoe UI (closest Windows system font to Apple's SF), near-black text
#1D1D1F, secondary #6E6E73, soft cards #F5F5F7 with rounded corners, one accent (#2B6CD0) = our top 10,
orange (#F56300) = model "c", Yale Blue #00356B for brand elements. Section eyebrow + action title on every slide,
footer with sample/method note, page number and Yale SOM shield.

Output: project/deck/MGT403_FinalProject_Deck.pptx (+ PDF / PNG previews via PowerPoint, see export step)
"""
import os
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "project/deck"
OUT.mkdir(parents=True, exist_ok=True)
FIG, T, A = ROOT / "output/figures", ROOT / "output/tables", ROOT / "project/assets"

INK, INK2, MUTED, CARD, LINE = "1D1D1F", "6E6E73", "86868B", "F5F5F7", "E5E5EA"
ACCENT, ORANGE, YALE, WHITE = "2B6CD0", "F56300", "00356B", "FFFFFF"
TINT = "EEF4FC"  # lightest step of the blue ramp (cards, highlighted rows)
FONT, FONT_SB, FONT_LT = "Segoe UI", "Segoe UI Semibold", "Segoe UI Light"
SECTIONS = ["Answer", "Model", "Selection", "Reliability", "Stability", "Outlook"]

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height
MX = Inches(0.6)  # side margin


def rgb(h):
    return RGBColor.from_string(h)


def text(slide, x, y, w, h, runs, size=14, color=INK, font=FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         spacing=1.0, bold=False):
    """runs: str or list of paragraphs; a paragraph is str or list of (text, dict(size,color,font,bold))."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        segs = para if isinstance(para, list) else [(para, {})]
        for seg, fmt in segs:
            r = p.add_run()
            r.text = seg
            f = r.font
            f.name = fmt.get("font", font)
            f.size = Pt(fmt.get("size", size))
            f.bold = fmt.get("bold", bold)
            f.color.rgb = rgb(fmt.get("color", color))
        if isinstance(para, list) is False and para == "":
            p.space_after = Pt(2)
    return tb


def card(slide, x, y, w, h, fill=CARD, radius=0.06):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def pill(slide, x, y, label, fill=ACCENT, color=WHITE, size=10):
    w = Inches(0.068 * len(label) * size / 10 + 0.35)
    s = card(slide, x, y, w, Inches(0.3), fill=fill, radius=0.5)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size, r.font.name, r.font.color.rgb = Pt(size), FONT_SB, rgb(color)
    return s


def chrome(slide, idx, eyebrow, title, footer):
    """Eyebrow, action title, progress dots, footer with method note, page number and shield."""
    text(slide, MX, Inches(0.42), Inches(8), Inches(0.3), [[(f"{idx:02d}  ", {"color": ACCENT, "font": FONT_SB}),
                                                         (eyebrow.upper(), {"color": INK2, "font": FONT_SB})]], size=11)
    # progress dots
    for i, sec in enumerate(SECTIONS):
        x = W - MX - Inches(0.22) * (len(SECTIONS) - i)
        d = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, Inches(0.5), Inches(0.1), Inches(0.1))
        d.fill.solid()
        d.fill.fore_color.rgb = rgb(ACCENT if i == idx - 1 else LINE)
        d.line.fill.background()
    text(slide, MX, Inches(0.78), W - 2 * MX, Inches(1.0), title, size=28, font=FONT_SB, spacing=0.95)
    line = slide.shapes.add_connector(1, MX, H - Inches(0.62), W - MX, H - Inches(0.62))
    line.line.color.rgb = rgb(LINE)
    line.line.width = Pt(0.75)
    text(slide, MX, H - Inches(0.52), Inches(10.6), Inches(0.35), footer, size=8.5, color=MUTED, spacing=1.0)
    text(slide, W - MX - Inches(1.3), H - Inches(0.52), Inches(0.6), Inches(0.3), f"{idx}", size=9, color=MUTED,
         align=PP_ALIGN.RIGHT)
    slide.shapes.add_picture(str(A / "yale_som_shield.png"), W - MX - Inches(0.42), H - Inches(0.56), height=Inches(0.36))


def hero(slide, x, y, w, number, label, color=ACCENT, size=40):
    text(slide, x, y, w, Inches(0.75), number, size=size, font=FONT_SB, color=color)
    text(slide, x, y + Pt(size * 1.45), w, Inches(0.6), label, size=11, color=INK2, spacing=1.05)


def table(slide, x, y, w, rows, col_w, header_color=INK2, size=10.5, row_h=0.32, bold_first=True, aligns=None,
          highlight_rows=(), zebra=False):
    """Clean table: header in small caps gray, thin separators, no fills (Apple style)."""
    nr, nc = len(rows), len(rows[0])
    rh = list(row_h) if isinstance(row_h, (list, tuple)) else [row_h] * nr
    shp = slide.shapes.add_table(nr, nc, x, y, w, Inches(sum(rh)))
    tbl = shp.table
    tblPr = shp._element.graphic.graphicData.tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    style = tblPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId")
    if style is None:
        from pptx.oxml.ns import qn
        style = tblPr.makeelement(qn("a:tableStyleId"), {})
        tblPr.append(style)
    style.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # "No Style, No Grid"
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(nr):
        tbl.rows[i].height = Inches(rh[i])
        for j in range(nc):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            val = rows[i][j]
            segs = val if isinstance(val, list) else [(str(val), {})]
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = (aligns[j] if aligns else (PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT))
            for seg, fmt in segs:
                r = p.add_run()
                r.text = seg
                hdr = i == 0
                r.font.size = Pt(fmt.get("size", size - 1.5 if hdr else size))
                r.font.name = fmt.get("font", FONT_SB if hdr or (bold_first and j == 0) or i in highlight_rows else FONT)
                r.font.color.rgb = rgb(fmt.get("color", header_color if hdr else INK))
            if i in highlight_rows:
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(TINT)
            elif zebra and i % 2 == 0 and i > 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(CARD)
            else:
                cell.fill.background()
    # thin separators
    for i in range(1, nr + 1):
        yy = y + Inches(sum(rh[:i]))
        ln = slide.shapes.add_connector(1, x, yy, x + w, yy)
        ln.line.color.rgb = rgb(INK2 if i == 1 else LINE)
        ln.line.width = Pt(0.75 if i == 1 else 0.5)
    return shp


def beyond(slide, x, y, label="Beyond course scope · Appendix"):
    pill(slide, x, y, label, fill="EDEDF0", color=INK2, size=8.5)


# ---- slide grid: 12 columns, 0.6 in margins, 0.25 in gutters; fixed label row, body top and body bottom ----
COLW, GUT = (12.133 - 11 * 0.25) / 12, 0.25
colx = lambda i: Inches(0.6 + i * (COLW + GUT))
span = lambda n: Inches(n * COLW + (n - 1) * GUT)
LABEL_Y, BODY, BOT = Inches(2.0), Inches(2.32), Inches(6.62)
PAD = Inches(0.22)  # inner padding of cards


def label(slide, x, y, w, txt, color=ACCENT, align=PP_ALIGN.LEFT):
    """Section label: one style everywhere (9.5 pt semibold caps)."""
    text(slide, x, y, w, Inches(0.25), txt.upper(), size=9.5, font=FONT_SB, color=color, align=align)


top = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
exp = pd.read_csv(T / "fp_imp_expected_premium.csv", dtype={"fips": str})
reg = pd.read_csv(T / "pre_t4_regressions.csv")
c = reg[(reg.se_type == "metro") & (reg.spec == "(c) wage + rent")].set_index("term")
r2c = c.r2.iloc[0]

# ===================================== Slide 1: the answer =======================================
s = prs.slides.add_slide(BLANK)
chrome(s, 1, "Where should we open our next preschool?",
       "Ten counties where parents are expected to pay 18–37% more than local costs predict, an advantage that has lasted since 2015",
       "MGT 403 Data Project · Carson Tavares, Lee Itzhaki, Vusala Suleymanova, Philipp Romberg. Sample: 998 metro counties (2022), prices 2015–2022. "
       "Premium = actual price vs. price predicted from childcare-worker wages and rents within the same state; expected premium = after typical fading (slide 5); "
       "bar = range from the uncertainty of the fading slope.")
label(s, colx(0), LABEL_Y, span(6), "Top 10 · price premium above what local costs predict")
label(s, colx(6), LABEL_Y, span(6), "Location · 1, 2, 4 and 6 form one market: Northern Virginia")
s.shapes.add_picture(str(FIG / "deck_F1_top10_premium.png"), colx(0), BODY, width=span(6))
s.shapes.add_picture(str(FIG / "deck_F1b_map.png"), colx(6), BODY, width=span(6))

# ===================================== Slide 2: model "c" -> final model ===========================
import numpy as np  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

an = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
d22 = an[an.year == 2022].copy()
d22["lp"], d22["lw"], d22["lr"] = (np.log(d22.price_preschool_real2022), np.log(d22.childcare_wage_real2022),
                                   np.log(d22.median_gross_rent_real2022))
fl = smf.ols("lp ~ lw + lr + C(state_abbr)", data=d22).fit(cov_type="cluster", cov_kwds={"groups": d22.oews_area})

s = prs.slides.add_slide(BLANK)
chrome(s, 2, "From model “c” to our prediction",
       f"Comparing each county with its own state lifts explained price variation from {r2c:.0%} to {fl.rsquared:.0%} "
       f"and reveals hidden premiums",
       f"Model “c” (pre-analysis): price = a + b₁·wage + b₂·rent. Final: log(price) = a + b₁·log(wage) + b₂·log(rent) + state dummies, estimated per year "
       f"2015–2022. 2022: N = {int(fl.nobs)}, {d22.state_abbr.nunique()} states/DC, SEs clustered by metro area. NDCP price, BLS OEWS childcare-worker wage, "
       f"ACS median gross rent, 2022 $. Premium = residual. Appendix B–C.")
for k, (img, head, eq, note, col) in enumerate([
        ("deck_F2c_model_c.png", "Step 1 · model “c”",
         f"Price = −{abs(c.loc['const', 'coef']):.0f} + {c.loc['wage_k', 'coef']:.2f}·wage + {c.loc['rent_100', 'coef']:.2f}·rent",
         "Above the line, parents pay more than costs justify. Here Hall and Sullivan look like ordinary markets.", ORANGE),
        ("deck_F3c_final.png", "Step 2 · within state, in %",
         f"+10% wage → +{(1.1 ** fl.params['lw'] - 1) * 100:.1f}%   ·   +10% rent → +{(1.1 ** fl.params['lr'] - 1) * 100:.1f}%",
         "Against their own state, all ten counties lie above the line.", ACCENT)]):
    x = colx(4 * k)
    label(s, x, LABEL_Y, span(4), head, color=col)
    text(s, x, Inches(2.3), span(4), Inches(0.3), eq, size=12, font=FONT_SB, color=INK)
    s.shapes.add_picture(str(FIG / img), x, Inches(2.7), width=span(4))
    text(s, x, Inches(6.26), span(4), Inches(0.36), note, size=9, color=INK2, spacing=1.0)
x0, wR = colx(8), span(4)
card(s, x0, LABEL_Y, wR, BOT - LABEL_Y)
xi, wi = x0 + PAD, wR - 2 * PAD
label(s, xi, Inches(2.17), wi, "Why the two steps")
text(s, xi, Inches(2.47), wi, Inches(1.0),
     [[("State dummies: ", {"font": FONT_SB, "color": INK}),
       ("states set rate zones and staffing rules, so each county is compared with its own state.", {})],
      [("Logs: ", {"font": FONT_SB, "color": INK}), ("the gap becomes a % premium; $50 means more in Tennessee than in SF.", {})]],
     size=9.5, color=INK2, spacing=1.05)
cse = lambda v, e: [(f"{v:.2f} ", {}), (f"({e:.2f})", {"color": MUTED, "size": 8.5})]
rows = [["2022, N = 998", "Model “c”", "Final"],
        ["Wage", cse(c.loc["wage_k", "coef"], c.loc["wage_k", "se"]), cse(fl.params["lw"], fl.bse["lw"])],
        ["Rent", cse(c.loc["rent_100", "coef"], c.loc["rent_100", "se"]), cse(fl.params["lr"], fl.bse["lr"])],
        ["State dummies", "–", f"yes ({d22.state_abbr.nunique() - 1})"],
        ["R²", f"{r2c:.2f}", f"{fl.rsquared:.2f}"]]
table(s, xi, Inches(3.62), wi, rows, [1.2, 1.12, 1.114], size=9.5, row_h=0.29, highlight_rows=(4,))
r2_ls = smf.ols("price_preschool_real2022 ~ I(childcare_wage_real2022 / 1000) + I(median_gross_rent_real2022 / 100) + C(state_abbr)",
                data=d22).fit().rsquared
val = pd.read_csv(T / "fp_model_validation.csv").set_index(["model", "validation"])
TV = "temporal: train 2015-2020, test 2022"
err_drop = (1 - val.loc[("LLS", TV)].rmse / val.loc[("L", TV)].rmse) * 100
text(s, xi, Inches(5.1), wi, Inches(0.45),
     f"Model “c”: $/week per $1,000 wage, $100 rent. Final: % change in price per 1% change. (SE, clustered by metro.) "
     f"Like for like in $: R² {r2c:.2f} → {r2_ls:.2f} with state effects; forecast error on unseen prices −{err_drop:.0f}% (App. C).",
     size=7.5, color=MUTED, spacing=1.0)
hl = d22.assign(pred_c=c.loc["const", "coef"] + c.loc["wage_k", "coef"] * d22.childcare_wage_real2022 / 1000
                + c.loc["rent_100", "coef"] * d22.median_gross_rent_real2022 / 100,
                pred_f=np.exp(fl.fittedvalues)).set_index("fips").loc["13139"]
label(s, xi, Inches(5.62), wi, "Example: Hall, GA (rank 9), 2022")
text(s, xi, Inches(5.9), wi, Inches(0.7),
     [[("Parents pay ", {}), (f"${hl.price_preschool_real2022:.0f}/week.", {"font": FONT_SB, "color": INK})],
      [("Model “c” predicts ", {}), (f"${hl.pred_c:.0f}", {"font": FONT_SB, "color": INK}),
       (f": +{(hl.price_preschool_real2022 / hl.pred_c - 1) * 100:.0f}%, looks ordinary.", {})],
      [("Within Georgia: ", {}), (f"${hl.pred_f:.0f}", {"font": FONT_SB, "color": INK}),
       (" predicted, so a ", {}), (f"+{(hl.price_preschool_real2022 / hl.pred_f - 1) * 100:.0f}% premium.", {"font": FONT_SB, "color": ACCENT})]],
     size=9.5, color=INK2, spacing=1.05)

# ===================================== Slide 3: selection & market characteristics ===================
prem = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str})
gp = prem.groupby("fips")
n_all, n5 = prem.fips.nunique(), int((gp.size() >= 5).sum())
n5nat = int(((gp.size() >= 5) & (gp.prem_LL_pct.mean() > 0)).sum())
in22 = gp.size().index.isin(d22.fips)  # the rule draws candidates from counties in the 2022 sample (27_fp_select_top10.py)
n22_5 = int(((gp.size() >= 5) & in22).sum())
n22_5nat = int(((gp.size() >= 5) & in22 & (gp.prem_LL_pct.mean() > 0)).sum())
thr = int(round(d22.kids_under6_allpar_lf.median()))
s = prs.slides.add_slide(BLANK)
chrome(s, 3, "How we selected",
       "From 1,159 counties to ten: a large, lasting price advantage, a market big enough to fill a center, and demand to rank them",
       "Premium = within-state % premium (slide 2), averaged over observed years 2015–2022 (≥ 5). Market size = children under 6 whose resident parents all "
       "work (ACS B23008). Score = 50% premium rank + 50% demand rank (children needing care, their share, income) among the ten; it only orders them. "
       "Female college share not used (r = 0.83 with income). Appendix D.")
STEPS = [(f"{n_all:,}", "metro counties with price, wage and rent data"),
         (f"{n22_5:,}", "in the 2022 data, observed ≥ 5 of 8 years"),
         (f"{n22_5nat:,}", "positive premium also nationally"),
         ("20", "largest average within-state premium"),
         ("20", "premium positive in every single year"),
         ("10", f"≥ {thr:,} children needing care"),
         ("Top 10", "ranked by score, removes none")]
WHY = ["NDCP prices × BLS wages × ACS rents, 2015–2022", "current market evidence + enough history",
       "not just pricey relative to a cheap state", "within-state model, averaged over 2015–2022",
       "lasting, not a one-off spike", "median market size; the other 10 fail only here", "50% premium + 50% demand rank"]
label(s, colx(0), LABEL_Y, span(5), "The funnel: from all metro counties to ten")
label(s, colx(5), LABEL_Y, span(7), "Market characteristics of the ten")
BH = Inches(0.56)
BG = (BOT - BODY - 7 * BH) / 6
y = BODY
for k, (num, lab) in enumerate(STEPS):
    wbar = span(5) - Inches(0.22 * k)
    shade = ["EEF4FC", "D3E3F7", "A8C8EE", "6FA2E0", "3A7CD0", "1D5AA6", "0B3C7A"][k]  # same ramp as the heatmap
    card(s, colx(0), y, wbar, BH, fill=shade, radius=0.25)
    dark = k >= 4
    text(s, colx(0) + Inches(0.18), y, Inches(0.95), BH, num, size=15, font=FONT_SB, color=WHITE if dark else INK,
         anchor=MSO_ANCHOR.MIDDLE)
    lab = [lab, [(WHY[k], {"size": 8.3, "color": "DCE7F7" if dark else (INK if k == 3 else INK2)})]]  # why + data
    text(s, colx(0) + Inches(1.08), y, wbar - Inches(1.15), BH, lab, size=10, color=WHITE if dark else INK,
         anchor=MSO_ANCHOR.MIDDLE, spacing=0.95)
    y += BH + BG
s.shapes.add_picture(str(FIG / "deck_F3b_characteristics.png"), colx(5), BODY, width=span(7))

# ===================================== Slide 4: reliability (b) ====================================
bt = pd.read_csv(T / "fp_checks_D_backtest_full_rule.csv")
rc = pd.read_csv(T / "fp_robustness_counts.csv")
ww = pd.read_csv(T / "fp_imp_wage_weight_robustness.csv").set_index("specification")
b2 = pd.read_csv(T / "fp_checks_B2_average_premium.csv")
dg = pd.read_csv(T / "fp_checks_C_diagnostics.csv", index_col=0).squeeze()
sig = pd.read_csv(T / "fp_checks_B_significance.csv")  # 2022 studentized residuals of the top 10
n_full = int((rc.selected_in_variants == rc["of"]).sum())
n5_all = n5  # counties observed in >= 5 years (basis of the percentile check)
assert b2.pct_rank.min() >= 0.98  # "top 2%"
s = prs.slides.add_slide(BLANK)
chrome(s, 4, "How reliable is the prediction?",
       f"With 2018 data only, our rule already picked {int(bt.iloc[0].overlap_with_2022_top10)} of today’s ten, and the list barely changes when we vary the design",
       f"Backtest: complete rule applied with 2015–2018 data only (these years are also part of today’s average); outcome = within-state premium in 2022 "
       f"({int(bt.iloc[0].n_in_2022)} of 10 picks still in the 2022 sample). Robustness: whole rule rerun with one change at a time. Appendix C and E.")
label(s, colx(0), LABEL_Y, span(6), "Backtest: as if we had decided in 2018")
s.shapes.add_picture(str(FIG / "deck_F4_backtest.png"), colx(0), BODY, width=span(6))
label(s, colx(0), Inches(4.45), span(6), "Statistical checks")
pp = prem[prem.fips.isin(top.fips)].copy()
pp["survey"] = pp.price_imp_code.astype(str).str.zfill(5).str[4] == "0"  # direct NDCP survey year (not interpolated)
surv_min = pp[pp.survey].groupby("fips").prem_LLS_pct.mean().min()
val = pd.read_csv(T / "fp_model_validation.csv").set_index(["model", "validation"])
err_drop = (1 - val.loc[("LLS", TV)].rmse / val.loc[("L", TV)].rmse) * 100
tiles = [(f"≥ +{np.floor(surv_min):.0f}%", "average premium of every one of the ten in its direct survey years only (no interpolated prices)"),
         (f"−{err_drop:.0f}%", "forecast error of our cost model vs. model “c” on 2022 prices it never saw (fitted 2015–20)"),
         (f"{int(ww.loc['Both wages', 'overlap_with_top10'])}/10", f"same list with both wage measures "
          f"({int(ww.loc['Preschool-teacher wage (SOC 25-2011)', 'overlap_with_top10'])}/10 if the teacher wage replaces ours)")]
TWd = (span(6) - 2 * Inches(GUT)) / 3
TY = Inches(4.77)
for i, (num, lab) in enumerate(tiles):
    xx = colx(0) + (TWd + Inches(GUT)) * i
    card(s, xx, TY, TWd, BOT - TY)
    text(s, xx + Inches(0.18), TY + Inches(0.14), TWd - Inches(0.36), Inches(0.5), num, size=24, font=FONT_SB, color=ACCENT)
    text(s, xx + Inches(0.18), TY + Inches(0.74), TWd - Inches(0.36), BOT - TY - Inches(0.8), lab, size=9.5, color=INK2,
         spacing=1.05)
n_of = int(rc["of"].iloc[0])
label(s, colx(6), LABEL_Y, span(6), f"Robustness: {n_full} of 10 selected in all {n_of} alternative designs")
s.shapes.add_picture(str(FIG / "deck_F4b_robustness_grid.png"), colx(6), BODY, width=span(6))
capv = pd.read_csv(T / "fp_metro_cap_variant.csv", dtype={"fips": str})
cname = lambda r: r.county_name.replace(" County", "").replace(" City", "")
out_cap = [cname(r) for r in top.itertuples() if r.fips not in set(capv.fips)]
in_cap = [f"{cname(r)}, {r.state_abbr}" for r in capv.itertuples() if not r.in_top10]
wls = ww.loc["Weighted by children under 6 (WLS)", "overlap_with_top10"]
text(s, colx(6), Inches(5.7), span(6), Inches(0.92),
     [[("Not counted: ", {"font": FONT_SB, "color": INK}),
       (f"weights 70/30 or 30/70 and “one weak year allowed” cannot change the list by construction. Weighting counties by children keeps {wls} of 10.", {})],
      [("Portfolio view (max. 2 per metro): ", {"font": FONT_SB, "color": INK}),
       (f"{' and '.join(out_cap)} give way to {' and '.join(in_cap)}; the other {10 - len(out_cap)} stay.", {})]],
     size=9, color=INK2, spacing=1.03)

# ===================================== Slide 5: stability (d) ======================================
sv = pd.read_csv(T / "fp_d_survey_only.csv", index_col=0).squeeze()
qt = pd.read_csv(T / "fp_d_quintile_transitions.csv").set_index("from_year")
ex = pd.read_csv(T / "fp_imp_expected_premium.csv")
s = prs.slides.add_slide(BLANK)
chrome(s, 5, "Are the premiums stable over time?",
       "Premiums above cost-based predictions last for years, but fade: about two thirds remain after five years",
       f"Within-state premium per county and year, 2015–2022 (log model, fitted per year). Survey test: two direct NDCP survey prices ≈ {sv['mean_gap_years']:.1f} years apart, "
       f"{int(sv['n_counties']):,} counties, {int(sv['n_states'])} states, SE clustered by state. Quintile test: counties observed every year, incl. interpolated years "
       f"(may overstate stability). Appendix D.")
label(s, colx(0), LABEL_Y, span(7), "Premium per year: each top-10 county vs. typical counties (gray: 10th–90th pct.)")
s.shapes.add_picture(str(FIG / "deck_F5_stability.png"), colx(0), BODY, width=span(7))
text(s, colx(0), Inches(6.27), span(7), Inches(0.35),
     "Dashed: 2021 missing (no NDCP prices for CA, VA). The 2022 jumps in Arlington, Alexandria and San Francisco come from "
     "NDCP-extrapolated CA/VA prices, so we rank on the 8-year average.", size=8.5, color=MUTED, spacing=1.0)
x0, wR = colx(7), span(5)
label(s, x0, LABEL_Y, wR, "How much of a premium survives?")
HWd = (wR - Inches(GUT)) / 2
hero(s, x0, BODY, HWd, f"{sv['slope']:.2f}", "of a premium (log scale) remains ≈ 5 years later (survey prices only)", size=30)
hero(s, x0 + HWd + Inches(GUT), BODY, HWd, f"{sv['share_same_sign'] * 100:.0f}%", "of counties keep the sign of their premium", size=30)
lo, hi = sv["slope"] - 1.96 * sv["se"], sv["slope"] + 1.96 * sv["se"]
text(s, x0, Inches(3.55), wR, Inches(0.25), f"95% CI for the slope: [{lo:.2f}, {hi:.2f}]; correlation {sv['corr']:.2f}", size=9, color=MUTED)
rows = [["Counties in the top fifth in…", "still top fifth in 2022", "still positive"],
        ["2015", f"{qt.loc[2015, 'share_still_top_quintile_2022'] * 100:.0f}%", f"{qt.loc[2015, 'share_positive_premium_2022'] * 100:.0f}%"],
        ["2018", f"{qt.loc[2018, 'share_still_top_quintile_2022'] * 100:.0f}%", f"{qt.loc[2018, 'share_positive_premium_2022'] * 100:.0f}%"],
        ["2019", f"{qt.loc[2019, 'share_still_top_quintile_2022'] * 100:.0f}%", f"{qt.loc[2019, 'share_positive_premium_2022'] * 100:.0f}%"],
        ["If premiums were random", "20%", "≈ 50%"]]
table(s, x0, Inches(3.92), wR, rows, [2.1, 1.55, 1.259], size=10, row_h=0.31)
CY = Inches(5.66)
card(s, x0, CY, wR, BOT - CY, fill=TINT)
text(s, x0 + PAD, CY, wR - 2 * PAD, BOT - CY,
     [[("So we plan with the expected premium: ", {"font": FONT_SB, "color": INK}),
       (f"each county’s average premium, faded by the slope of {sv['slope']:.2f} on the log scale: +{ex.expected_premium_pct.min():.0f}% "
        f"to +{ex.expected_premium_pct.max():.0f}% for our ten (slide 1).", {})]], size=10, color=INK2, spacing=1.05, anchor=MSO_ANCHOR.MIDDLE)

# ===================================== Slide 6: outlook ===========================================
mf = pd.read_csv(T / "fp_e_missing_factors_top10.csv", dtype={"fips": str})
bm = pd.read_csv(T / "fp_e_sample_benchmarks.csv", index_col=0)
q = lambda v, k: bm.loc[v, k]
GOOD, WARN, BAD = ("✓", "0CA30C"), ("!", "C98500"), ("✕", "D03B3B")


import re as _re
neg = lambda t: _re.sub(r"(?<![\w.])-(\d)", "\u2212\\1", t)  # typographic minus for negative numbers


def flag(sym_col, txt):
    sym, col = sym_col
    return [(sym + "  ", {"color": col, "font": "Segoe UI Symbol", "size": 11}), (neg(txt), {"color": INK})]


prek = pd.read_csv(ROOT / "data/manual/public_prek_programs.csv", dtype={"fips": str}).set_index("fips")  # sourced, see Appendix F
why = lambda t: [(neg(t), {"size": 7.8, "color": INK2, "font": FONT})]
rows = [["County", "Competition", "Child trend", "Wage growth", "Rent growth", "Public pre-K*"],
        [[("Why it matters", {"size": 7.8, "color": ACCENT, "font": FONT_SB})],
         why(f"Centers per 1,000 children needing care. ! above {q('centers_per_1000_kids', '75%'):.2f} (crowded) or below {q('centers_per_1000_kids', '25%'):.2f} (untested)"),
         why(f"Children <6, 2015–22: future demand. ! below median ({q('kids_change_2015_2022_pct', '50%'):+.1f}%), ✕ below {q('kids_change_2015_2022_pct', '25%'):+.1f}%"),
         why(f"2019–22: staff cost pressure. ! top quarter (above {q('wage_change_2019_2022_pct', '75%'):+.1f}%)"),
         why(f"2015–22: site cost pressure. ! top quarter (above {q('rent_change_2015_2022_pct', '75%'):+.1f}%)"),
         why("Free public pre-K competes directly. ! if free for all incomes (universal)")]]
nflags = {}
for r in mf.itertuples():
    comp = r.centers_per_1000_kids
    c_f = WARN if (comp > q("centers_per_1000_kids", "75%") or comp < q("centers_per_1000_kids", "25%")) else GOOD
    c_t = "dense" if comp > q("centers_per_1000_kids", "75%") else ("thin" if comp < q("centers_per_1000_kids", "25%") else "typical")
    k = r.kids_change_2015_2022_pct
    k_f = GOOD if k > q("kids_change_2015_2022_pct", "50%") else (WARN if k > q("kids_change_2015_2022_pct", "25%") else BAD)
    wg = r.wage_change_2019_2022_pct
    w_f = WARN if wg > q("wage_change_2019_2022_pct", "75%") else GOOD
    rg = r.rent_change_2015_2022_pct
    r_f = WARN if rg > q("rent_change_2015_2022_pct", "75%") else GOOD
    p_f = WARN if prek.loc[r.fips, "flag"] == "yes" else GOOD
    nflags[r.fips] = sum(f is not GOOD for f in (c_f, k_f, w_f, r_f, p_f)) + sum(f is BAD for f in (k_f,))
    nm = r.county_name.replace(" County", "").replace(" City", "")
    rows.append([f"{nm}, {r.state_abbr}", flag(c_f, f"{comp:.2f}  {c_t}"), flag(k_f, f"{k:+.1f}%"), flag(w_f, f"{wg:+.1f}%"),
                 flag(r_f, f"{rg:+.1f}%"), flag(p_f, prek.loc[r.fips, "short_label"])])
start = [f for f in mf.fips if nflags[f] <= 1]  # at most one minor flag, in rank order
nxt = [f for f in mf.fips if nflags[f] == 2]
names = {r.fips: r.county_name.replace(" County", "").replace(" City", "") for r in mf.itertuples()}
s = prs.slides.add_slide(BLANK)
chrome(s, 6, "What the model does not see yet",
       "Our recommendation: open first in Northern Virginia, one market with four top counties, after checking local prices on the ground",
       f"Benchmarks: quartiles of all metro counties with data ({int(bm.loc['centers_per_1000_kids', 'count'])}–{int(bm.loc['wage_change_2019_2022_pct', 'count'])} counties). "
       "Competition: Census County Business Patterns (NAICS 624410, 2022), children needing care (ACS). *Public pre-K: state/county program rules, "
       "accessed Oct 2026 (sources in Appendix F).")
label(s, colx(0), LABEL_Y, span(5), "Five local checks the cost model cannot see")
text(s, colx(0), LABEL_Y, span(8), Inches(0.25),
     [[("✓", {"color": GOOD[1], "font": "Segoe UI Symbol"}), (" typical     ", {}),
       ("!", {"color": WARN[1], "font": "Segoe UI Symbol"}), (" watch     ", {}),
       ("✕", {"color": BAD[1], "font": "Segoe UI Symbol"}), (" risk   (vs. all metro counties)", {})]],
     size=9.5, color=INK2, align=PP_ALIGN.RIGHT)
table(s, colx(0), BODY, span(8), rows, [1.4, 1.62, 1.3, 1.1, 1.1, 1.485], size=10,
      row_h=[0.34, 0.66] + [0.33] * 10, aligns=[PP_ALIGN.LEFT] * 6)
xr, wr = colx(8), span(4)
C1B = Inches(4.62)
card(s, xr, LABEL_Y, wr, C1B - LABEL_Y, fill=TINT)
label(s, xr + PAD, Inches(2.17), wr - 2 * PAD, "Where to start: Northern Virginia")
text(s, xr + PAD, Inches(2.45), wr - 2 * PAD, Inches(0.6), ", ".join(names[f] for f in start), size=14,
     font=FONT_SB, color=INK, spacing=1.0)
text(s, xr + PAD, Inches(3.08), wr - 2 * PAD, Inches(1.5),
     [f"Lasting premiums of +{top.set_index('fips').loc[start].mean_premium_LLS_pct.min():.0f}% to "
      f"+{top.set_index('fips').loc[start].mean_premium_LLS_pct.max():.0f}%, large care-need markets, at most one minor flag.",
      [("One market, not four bets: ", {"font": FONT_SB, "color": INK}),
       ("shared wage, labor market and state survey, so open one site first. Virginia’s last direct price surveys are from 2015 and "
        "2018: check current prices locally.", {})],
      f"Next in line: {' and '.join(names[f] for f in nxt)}."],
     size=9.5, color=INK2, spacing=1.04)
C2T = C1B + Inches(GUT)
card(s, xr, C2T, wr, BOT - C2T)
label(s, xr + PAD, C2T + Inches(0.17), wr - 2 * PAD, "Not in our data yet", color=INK2)
text(s, xr + PAD, C2T + Inches(0.47), wr - 2 * PAD, BOT - C2T - Inches(0.55),
     ["•  Commercial rents and sites (we use residential rent)",
      "•  Staff availability and turnover, not just average wages",
      "•  Local licensing rules and quality mix of competitors",
      "•  Remote work; federal job changes (DC area)",
      "•  Price data: only 2–5 direct survey years per county"], size=9.5, color=INK2, spacing=1.12)

pptx_path = OUT / os.environ.get("FP_DECK_NAME", "MGT403_FinalProject_Deck.pptx")
prs.save(pptx_path)
print("saved", pptx_path)
