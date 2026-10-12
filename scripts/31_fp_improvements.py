"""Final project: four improvements / robustness checks of the selection.

1. Wage measure: re-estimate the within-state premium with the mean annual wage of PRESCHOOL TEACHERS
   (SOC 25-2011, excl. special education) instead of childcare workers (SOC 39-9011), and with both wages
   together; rerun the full selection rule. OEWS files as in 02_get_oews.py (incl. 2015-2017 aMSA whole-MSA
   files; metropolitan divisions not used), merged to counties with the course crosswalk on [year, oews_area].
2. Expected future premium: shrink each county's average premium with the persistence estimated from direct
   survey prices only (29_fp_stability.py: log premium about 4.7 years later = a + b * log premium today).
3. Weighting: cost model weighted by the number of children under 6 (WLS); rerun the selection.
4. DC: with state fixed effects, DC (one county) has a premium of 0 by construction. Test: treat DC, MD and VA as
   one group for the fixed effect and report DC's premium and rank.

Inputs:  data/raw/oews/oesmYYma.zip, data/crosswalks/county_oews_crosswalk.csv, data/interim/cpi_u_annual.csv,
         data/analysis/analysis_dataset_2015_2022.csv, data/analysis/fp_premiums_2015_2022.csv,
         output/tables/fp_top10_final.csv
Outputs: data/interim/oews_preschool_teachers_2015_2022.csv, output/tables/fp_imp_*.csv
"""
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "output/tables"
TOP10 = pd.read_csv(T / "fp_top10_final.csv", dtype={"fips": str})
BASE = set(TOP10.fips)

# --- 1a. preschool teacher wages ------------------------------------------------------------------------
out = ROOT / "data/interim/oews_preschool_teachers_2015_2022.csv"
if not out.exists():
    frames = []
    for y in range(2015, 2023):
        with zipfile.ZipFile(ROOT / f"data/raw/oews/oesm{y % 100:02d}ma.zip") as z:
            for name in z.namelist():
                base = Path(name).name.upper()
                if not base.endswith(".XLSX") or not base.startswith(("MSA", "AMSA", "BOS")):
                    continue
                df = pd.read_excel(io.BytesIO(z.read(name)), dtype=str)
                df.columns = df.columns.str.strip().str.lower()
                df = df.rename(columns={"area_name": "area_title"})
                df = df[df.occ_code.str.strip() == "25-2011"]
                frames.append(df.assign(year=y)[["year", "area", "area_title", "a_mean", "tot_emp"]])
    t = pd.concat(frames)
    t["oews_area"] = t.area.str.strip().str.zfill(7)
    t = t[~t.area_title.str.contains("Metropolitan Division", na=False)].drop_duplicates(["year", "oews_area"])
    t["teacher_wage"] = pd.to_numeric(t.a_mean.str.replace(",", ""), errors="coerce")
    t[["year", "oews_area", "area_title", "teacher_wage", "tot_emp"]].to_csv(out, index=False)
tw = pd.read_csv(out, dtype={"oews_area": str})
cpi = pd.read_csv(ROOT / "data/interim/cpi_u_annual.csv")
tw = tw.merge(cpi[["year", "to_2022_dollars"]], on="year")
tw["teacher_wage_real2022"] = tw.teacher_wage * tw.to_2022_dollars

a = pd.read_csv(ROOT / "data/analysis/analysis_dataset_2015_2022.csv", dtype={"fips": str, "oews_area": str})
a = a.merge(tw[["year", "oews_area", "teacher_wage_real2022"]], on=["year", "oews_area"], how="left")
a["lp"], a["lw"], a["lr"] = np.log(a.price_preschool_real2022), np.log(a.childcare_wage_real2022), np.log(a.median_gross_rent_real2022)
a["lt"] = np.log(a.teacher_wage_real2022)
cover = a.groupby("year").teacher_wage_real2022.apply(lambda s: s.notna().mean())


def premiums(df, formula, weights=None, group="state_abbr"):
    res = []
    for y, g in df.groupby("year"):
        g = g.dropna(subset=[c for c in ["lt"] if "lt" in formula]).copy()
        f = formula.replace("GROUP", group)
        fit = (smf.wls(f, data=g, weights=g[weights]).fit() if weights else smf.ols(f, data=g).fit())
        g["prem"] = (np.exp(fit.resid) - 1) * 100
        nat = smf.ols(f.replace(f" + C({group})", ""), data=g).fit()
        g["nat"] = (np.exp(nat.resid) - 1) * 100
        res.append(g[["year", "fips", "county_name", "state_abbr", "prem", "nat", "kids_under6_allpar_lf",
                      "under6_careneed_share", "per_capita_income_real2022"]])
    return pd.concat(res)


def select(pr, n=10, pool=20, min_years=5):
    d = pr[pr.year == 2022].copy()
    h = pr.groupby("fips")
    d["n_years"], d["mean_prem"], d["mean_nat"] = d.fips.map(h.size()), d.fips.map(h.prem.mean()), d.fips.map(h.nat.mean())
    d["all_pos"] = d.fips.map(h.prem.apply(lambda s: (s > 0).all()))
    cand = d[(d.n_years >= min_years) & (d.mean_nat > 0)].nlargest(pool, "mean_prem")
    ok = cand[cand.all_pos & (cand.kids_under6_allpar_lf >= d.kids_under6_allpar_lf.median())].copy()
    ok["dem"] = ok[["kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022"]].rank(pct=True).mean(axis=1)
    ok["score"] = 0.5 * ok.mean_prem.rank(pct=True) + 0.5 * ok.dem
    return ok.sort_values("score", ascending=False).head(n)


label = a[a.year == 2022].set_index("fips").apply(lambda r: f"{r.county_name}, {r.state_abbr}", axis=1)
rows = []
specs = {
    "Baseline: childcare-worker wage (SOC 39-9011)": ("lp ~ lw + lr + C(GROUP)", None, a),
    "Preschool-teacher wage (SOC 25-2011)": ("lp ~ lt + lr + C(GROUP)", None, a),
    "Both wages": ("lp ~ lw + lt + lr + C(GROUP)", None, a),
    "Weighted by children under 6 (WLS)": ("lp ~ lw + lr + C(GROUP)", "kids_under6", a),
}
sel = {}
for name, (f, wts, df) in specs.items():
    s = select(premiums(df, f, wts))
    sel[name] = s
    rows.append({"specification": name, "overlap_with_top10": len(set(s.fips) & BASE),
                 "dropped": "; ".join(sorted(label.reindex(list(BASE - set(s.fips))).dropna())),
                 "added": "; ".join(sorted(label.reindex(list(set(s.fips) - BASE)).dropna()))})
spec = pd.DataFrame(rows)
spec.to_csv(T / "fp_imp_wage_weight_robustness.csv", index=False)
d22 = a[a.year == 2022]
fit_t = smf.ols("lp ~ lt + lr + C(state_abbr)", data=d22.dropna(subset=["lt"])).fit()
fit_w = smf.ols("lp ~ lw + lr + C(state_abbr)", data=d22.dropna(subset=["lt"])).fit()
fit_b = smf.ols("lp ~ lw + lt + lr + C(state_abbr)", data=d22.dropna(subset=["lt"])).fit()
fitcmp = pd.DataFrame({"model": ["childcare-worker wage", "preschool-teacher wage", "both wages"],
                       "n_2022": [int(fit_w.nobs), int(fit_t.nobs), int(fit_b.nobs)],
                       "r2": [fit_w.rsquared, fit_t.rsquared, fit_b.rsquared],
                       "coef_childcare_wage": [fit_w.params.get("lw"), np.nan, fit_b.params.get("lw")],
                       "coef_teacher_wage": [np.nan, fit_t.params.get("lt"), fit_b.params.get("lt")],
                       "coef_rent": [fit_w.params["lr"], fit_t.params["lr"], fit_b.params["lr"]]})
fitcmp.to_csv(T / "fp_imp_wage_model_fit.csv", index=False)

# --- 2. expected future premium --------------------------------------------------------------------------
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
sv = p[p.price_imp_code.str[4] == "0"][["fips", "year", "prem_LLS_log", "state_abbr"]].sort_values("year")
pairs = []
for fips, g in sv.groupby("fips"):
    if len(g) >= 2 and g.year.iloc[-1] - g.year.iloc[0] >= 2:
        pairs.append({"fips": fips, "state": g.state_abbr.iloc[0], "p1": g.prem_LLS_log.iloc[0], "p2": g.prem_LLS_log.iloc[-1],
                      "gap": g.year.iloc[-1] - g.year.iloc[0]})
pairs = pd.DataFrame(pairs)
pf = smf.ols("p2 ~ p1", data=pairs).fit(cov_type="cluster", cov_kwds={"groups": pairs["state"]})
a0, b1 = pf.params["Intercept"], pf.params["p1"]
mean_log = p.groupby("fips").prem_LLS_log.mean()
exp = TOP10[["rank", "fips", "county_name", "state_abbr"]].copy()
exp["avg_premium_pct"] = (np.exp(exp.fips.map(mean_log)) - 1) * 100
exp["expected_premium_pct"] = (np.exp(a0 + b1 * exp.fips.map(mean_log)) - 1) * 100
lo, hi = pf.conf_int().loc["p1"]
exp["expected_low_pct"] = (np.exp(a0 + lo * exp.fips.map(mean_log)) - 1) * 100
exp["expected_high_pct"] = (np.exp(a0 + hi * exp.fips.map(mean_log)) - 1) * 100
exp.to_csv(T / "fp_imp_expected_premium.csv", index=False)

# --- 4. DC grouped with MD and VA ------------------------------------------------------------------------
a["grp"] = a.state_abbr.where(~a.state_abbr.isin(["DC", "MD", "VA"]), "DC-MD-VA")
pr_dc = premiums(a, "lp ~ lw + lr + C(GROUP)", group="grp")
dc = pr_dc[pr_dc.fips == "11001"]
dc_rank = select(pr_dc, n=30)
dc_out = {"dc_mean_premium_pct": dc.prem.mean(), "dc_premium_2022_pct": dc[dc.year == 2022].prem.squeeze(),
          "dc_years_positive": int((dc.prem > 0).sum()), "dc_years": len(dc),
          "dc_in_top10_with_grouping": "11001" in set(select(pr_dc).fips),
          "dc_rank_if_candidate": int(dc_rank.reset_index().index[dc_rank.fips.values == "11001"][0] + 1) if "11001" in set(dc_rank.fips) else None,
          "overlap_top10_with_grouping": len(set(select(pr_dc).fips) & BASE)}
pd.Series(dc_out).to_csv(T / "fp_imp_dc_grouping.csv")

pd.set_option("display.width", 260, "display.float_format", lambda v: f"{v:,.3f}", "display.max_colwidth", 90)
print("Preschool-teacher wage coverage in analysis dataset by year:", cover.round(3).to_dict())
print("\n2022 model fit (same counties):\n", fitcmp.to_string(index=False))
print("\nSelection robustness:\n", spec.to_string(index=False))
for k in ["Preschool-teacher wage (SOC 25-2011)", "Both wages", "Weighted by children under 6 (WLS)"]:
    print(f"\n{k}: ", ", ".join(label[sel[k].fips]))
print(f"\nPersistence (survey prices only): log prem later = {a0:.4f} + {b1:.3f} x log prem now  (n={len(pairs)}, "
      f"mean gap {pairs.gap.mean():.1f} y, slope 95% CI [{lo:.3f}, {hi:.3f}])")
print(exp.to_string(index=False))
print("\nDC grouping test:", dc_out)
