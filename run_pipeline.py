"""Rebuild every result of the MGT 403 data project, in order.

    python run_pipeline.py            # quick: from the included data (no downloads, no keys)
    python run_pipeline.py --full     # also re-download CPI, BLS OEWS and Census ACS raw data first
    python run_pipeline.py --homework # also rerun the Problem Set 4/5 homework-only scripts

--full needs the environment variable BLS_CONTACT_EMAIL (your own e-mail; BLS requires a contact in the User-Agent)
and a Census API key (environment variable CENSUS_API_KEY or a file census_api_key.txt in this folder).
The deck PDF export (scripts/export_deck.ps1) needs Microsoft PowerPoint on Windows; the PDF documents need Microsoft Edge.
Both are optional: all tables, figures and the PowerPoint file are produced by Python alone.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOAD = ["01_get_cpi", "02_get_oews", "03_get_acs"]
DATA = ["04_prepare_ndcp", "05_build_metro_sample", "08_ps4_q3_real_trends", "12_build_acs_derived", "13_build_cost_panel",
        "15_ps5_q5_real_trends"]
HOMEWORK = ["06_ps4_q2_distribution_2022", "07_ps4_q2_factsheet", "09_ps4_q4_voucher_test", "10_ps4_q4_robustness",
            "14_ps5_q4_descriptives_2022", "16_ps5_q6_wage_test", "17_ps5_q7_regression"]
PRE = ["18_pre_merge_prices_costs", "19_pre_analysis_dataset", "20_pre_t2_descriptives_2022", "21_pre_t3_scatter",
       "22_pre_t4_regressions", "23_pre_t4_coef_plot"]
FINAL = ["25_fp_premium_models", "26_fp_persistence_demand", "27_fp_select_top10", "28_fp_math_checks", "29_fp_stability",
         "30_fp_missing_factors", "31_fp_improvements", "32_fp_analysis_register", "33_fp_figures", "34_build_deck",
         "35_fp_check_deck_numbers", "36_fp_appendix_analysis", "37_build_appendix"]

steps = (DOWNLOAD if "--full" in sys.argv else []) + DATA + (HOMEWORK if "--homework" in sys.argv else []) + PRE + FINAL
for s in steps:
    print(f"--- {s}", flush=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / f"{s}.py")], cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"{s} failed (exit code {r.returncode})")
print("\nAll steps finished. Deck: project/deck/MGT403_FinalProject_Deck.pptx; document: "
      "project/submission/MGT403_PreAnalysis_and_Appendix.pdf; number check: output/project/deck_number_check.md")
