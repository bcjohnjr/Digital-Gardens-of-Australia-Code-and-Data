"""Run the complete Digital Gardens Sunraysia analysis from this single folder.

    python run_all.py

Steps: input checksums -> weather checks and conversion -> hourly dispatch for three wind treatments ->
ledgers -> community-benefit cost and GPU premium -> figures and maps -> clean-reproduction check against
the published reference values. Everything is written next to the scripts; no sub-folders are created.
If dgs_era5_hourly.csv.gz is missing, run  python dgs_download_era5.py  first (about 15-30 minutes).
"""
import os, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
MODES = ("rez", "palmer", "raw")
real = os.path.exists(os.path.join(HERE, "dgs_era5_hourly.csv.gz"))
has_ck = os.path.exists(os.path.join(HERE, "dgs_checksums.sha256"))
STEPS = ([["dgs_checksums.py", "--data-only"]] if real and has_ck else []) + [["dgs_weather.py"]] \
        + [["dgs_model.py", m] for m in MODES] + [["dgs_analysis.py", m] for m in MODES] \
        + [["dgs_premium.py", m] for m in MODES] + [["dgs_figures.py"]] \
        + ([["dgs_verify.py"]] if real and os.path.exists(os.path.join(HERE, "dgs_reference_values.json")) else [])
if not real:
    print("NOTE: dgs_era5_hourly.csv.gz not found - results will be PROVISIONAL (proxy weather) and are not verified.")
t0 = time.time()
for st in STEPS:
    print(f"\n=== python {' '.join(st)}", flush=True)
    r = subprocess.run([sys.executable, "-B", st[0]] + st[1:], cwd=HERE, capture_output=True, text=True)
    lines = (r.stdout or "").strip().splitlines()
    print("\n".join(("   " + x) for x in lines[-4:]))
    if r.returncode != 0:
        print(r.stderr[-3000:]); sys.exit(f"step failed: {' '.join(st)}")
print(f"\nAll steps complete in {time.time() - t0:.0f} s.")
