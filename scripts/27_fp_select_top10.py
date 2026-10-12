"""Final project step 3: select the top 10 counties (team decisions) and test the robustness of the selection.

Selection rule (team decisions):
  1. Premium: within-state % premium (LLS: log price ~ log wage + log rent + state FE, fitted per year).
     The candidate pool is ranked on the county's AVERAGE premium over all observed years 2015-2022 (at least 5
     years observed), not on 2022 alone. Reason: the advantage must have lasted over time, and NDCP's 2022 prices
     for CA and VA are model-based extrapolations that create implausible one-year jumps (see 29_fp_stability.py).
     Robustness requirement: average national % premium (LL) > 0.  -> candidate pool = top 20.
  2. Persistence: LLS premium > 0 in every observed year.
  3. Market size: children under 6 with all resident parents in the labor force >= 2022 sample median.
  4. Score = 0.5 * premium strength + 0.5 * demand index, both as percentile ranks among the remaining candidates
     (same scale -> effective 50/50 weights). Premium strength = average LLS premium; demand index = mean
     percentile of children needing care, under-6 care-need share, per-capita income (2022).
  5. Top 10 by score. No cap per metro area.

Robustness: each variant reruns the whole rule with one change.

Inputs:  data/analysis/fp_premiums_2015_2022.csv
Outputs: output/tables/fp_top10_final.csv, output/tables/fp_candidates_scored.csv, output/tables/fp_robustness.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
p = pd.read_csv(ROOT / "data/analysis/fp_premiums_2015_2022.csv", dtype={"fips": str, "price_imp_code": str})
NAT = {"prem_LLS_pct": "prem_LL_pct", "prem_LS_usd": "prem_L_usd", "prem_LL_pct": "prem_LL_pct"}


def select(prem="prem_LLS_pct", year=2022, years=None, basis="mean", w_prem=0.5, allow_neg=0, market_q=0.5,
           pool=20, min_years=5, n=10, full=False):
    years = years or list(range(2015, year + 1))
    d = p[p.year == year].copy()
    h = p[p.year.isin(years)].groupby("fips")
    d["n_years"] = d.fips.map(h.size())
    d["mean_prem"] = d.fips.map(h[prem].mean())
    d["mean_nat"] = d.fips.map(h[NAT[prem]].mean())
    if basis == "mean":
        cand = d[(d.n_years >= min_years) & (d.mean_nat > 0)].nlargest(pool, "mean_prem").copy()
    else:  # single-year basis (previous design)
        cand = d[d[NAT[prem]] > 0].nlargest(pool, prem).copy()
    cand["years_positive"] = cand.fips.map(h[prem].apply(lambda s: (s > 0).sum()))
    cand["pass_persistence"] = cand.n_years - cand.years_positive <= allow_neg
    thr = d.kids_under6_allpar_lf.quantile(market_q)
    cand["pass_market"] = cand.kids_under6_allpar_lf >= thr
    ok = cand[cand.pass_persistence & cand.pass_market].copy()
    ok["pct_market"] = ok.kids_under6_allpar_lf.rank(pct=True)
    ok["pct_careneed_share"] = ok.under6_careneed_share.rank(pct=True)
    ok["pct_income"] = ok.per_capita_income_real2022.rank(pct=True)
    ok["demand_index"] = ok[["pct_market", "pct_careneed_share", "pct_income"]].mean(axis=1)
    ok["premium_strength"] = ok.mean_prem.rank(pct=True)
    ok["score"] = w_prem * ok.premium_strength + (1 - w_prem) * ok.demand_index
    ok = ok.sort_values("score", ascending=False)
    ok["rank"] = range(1, len(ok) + 1)
    if full:
        return cand, ok, thr
    return set(ok.head(n).fips)


cand, scored, thr = select(full=True)
top10 = scored.head(10)
cols = ["rank", "fips", "county_name", "state_abbr", "metro_area", "price", "mean_prem", "prem_LLS_pct", "mean_nat",
        "n_years", "years_positive", "kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022",
        "premium_strength", "demand_index", "score", "price_imp_code"]
scored[cols].rename(columns={"mean_prem": "mean_premium_LLS_pct", "prem_LLS_pct": "premium_2022_LLS_pct",
                             "mean_nat": "mean_premium_national_pct"}).to_csv(ROOT / "output/tables/fp_candidates_scored.csv", index=False)
top10[cols].rename(columns={"mean_prem": "mean_premium_LLS_pct", "prem_LLS_pct": "premium_2022_LLS_pct",
                            "mean_nat": "mean_premium_national_pct"}).to_csv(ROOT / "output/tables/fp_top10_final.csv", index=False)
cand_out = cand[~cand.fips.isin(scored.fips)][["county_name", "state_abbr", "mean_prem", "n_years", "years_positive",
                                               "kids_under6_allpar_lf", "pass_persistence", "pass_market"]]
base = set(top10.fips)

variants = {
    "Previous design: pool ranked on 2022 premium only": dict(basis="year"),
    "Average premium 2015-2020 (excludes NDCP 2022 extrapolation)": dict(years=list(range(2015, 2021))),
    "Average premium 2015-2019 (pre-COVID)": dict(years=list(range(2015, 2020))),
    "Level instead of log premium (LS, $/week, state effects)": dict(prem="prem_LS_usd"),
    "National premium, no state effects (LL)": dict(prem="prem_LL_pct"),
    "Weights 70% premium / 30% demand": dict(w_prem=0.7),
    "Weights 30% premium / 70% demand": dict(w_prem=0.3),
    "Persistence: one negative year allowed": dict(allow_neg=1),
    "Market threshold: 25th percentile": dict(market_q=0.25),
    "Candidate pool: top 30 instead of top 20": dict(pool=30),
}
name = p[p.year == 2022].set_index("fips").apply(lambda r: f"{r.county_name}, {r.state_abbr}", axis=1)
rob, sets = [], {}
for vname, kw in variants.items():
    s = select(**kw)
    sets[vname] = s
    rob.append({"variant": vname, "overlap_with_top10": len(s & base),
                "dropped": "; ".join(sorted(name[list(base - s)])), "added": "; ".join(sorted(name[list(s - base)]))})
rob = pd.DataFrame(rob)
# Variants that cannot change the list by construction: the score only orders the ten (all ten pass the filters), and all
# 20 pool members already pass the persistence filter. They are reported but not counted as robustness evidence.
NONBINDING = {"Weights 70% premium / 30% demand", "Weights 30% premium / 70% demand", "Persistence: one negative year allowed"}
rob["status"] = ["not counted: replaced by D2 (2022 extrapolations)" if v.startswith("Previous design")
                 else "not counted: rejected in D1 (selects states, not markets)" if v.startswith("National premium")
                 else "not counted: cannot change the list by construction" if v in NONBINDING else "counted" for v in rob.variant]
rob.to_csv(ROOT / "output/tables/fp_robustness.csv", index=False)
countable = [v for v in variants if not v.startswith(("Previous design", "National premium")) and v not in NONBINDING]
counts = {f: sum(f in sets[v] for v in countable) for f in base}
top10_counts = pd.DataFrame({"county": [name[f] for f in top10.fips], "selected_in_variants": [counts[f] for f in top10.fips],
                             "of": len(countable)})
top10_counts.to_csv(ROOT / "output/tables/fp_robustness_counts.csv", index=False)

# Portfolio view (not a robustness test): at most 2 counties per metro area. Walk down the ranking of average premiums
# (same eligibility, persistence and market-size rules) until 10 counties qualify, then score them as in the rule.
d22 = p[p.year == 2022].copy()
hh = p.groupby("fips")
d22["n_years"], d22["mean_prem"], d22["mean_nat"] = d22.fips.map(hh.size()), d22.fips.map(hh.prem_LLS_pct.mean()), d22.fips.map(hh.prem_LL_pct.mean())
d22["all_pos"] = d22.fips.map(hh.prem_LLS_pct.apply(lambda x: (x > 0).all()))
cc = d22[(d22.n_years >= 5) & (d22.mean_nat > 0) & d22.all_pos & (d22.kids_under6_allpar_lf >= d22.kids_under6_allpar_lf.median())]
cc = cc.sort_values("mean_prem", ascending=False)
pick, per = [], {}
for r in cc.itertuples():
    if per.get(r.metro_area, 0) < 2:
        pick.append(r.fips)
        per[r.metro_area] = per.get(r.metro_area, 0) + 1
    if len(pick) == 10:
        break
cap = cc[cc.fips.isin(pick)].copy()
dem = ["kids_under6_allpar_lf", "under6_careneed_share", "per_capita_income_real2022"]
cap["score"] = 0.5 * cap.mean_prem.rank(pct=True) + 0.5 * cap[dem].rank(pct=True).mean(axis=1)
cap = cap.sort_values("score", ascending=False)
cap["rank"] = range(1, 11)
cap["in_top10"] = cap.fips.isin(base)
cap[["rank", "fips", "county_name", "state_abbr", "metro_area", "mean_prem", "kids_under6_allpar_lf", "score", "in_top10"]].rename(
    columns={"mean_prem": "mean_premium_LLS_pct"}).to_csv(ROOT / "output/tables/fp_metro_cap_variant.csv", index=False)

pd.set_option("display.width", 260, "display.float_format", lambda v: f"{v:,.3f}", "display.max_colwidth", 90)
print(f"Market threshold (median children needing care): {thr:,.0f}")
print("Candidate pool (top 20 by average premium) that failed a filter:\n", cand_out.to_string(index=False))
print("\n", scored[["rank", "county_name", "state_abbr", "mean_prem", "prem_LLS_pct", "n_years", "kids_under6_allpar_lf",
                    "premium_strength", "demand_index", "score"]].to_string(index=False))
print("\nRobustness:\n", rob.to_string(index=False))
print(f"\nSelected in the {len(countable)} plausible variants (excl. previous design and rejected national design):")
print(top10_counts.to_string(index=False))
