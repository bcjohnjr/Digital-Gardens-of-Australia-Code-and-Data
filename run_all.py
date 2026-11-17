"""Run the full Digital Gardens Australia analysis. Everything lives in this one folder.

    python run_all.py

Steps: input checksums -> weather conversion -> ERA5 dispatch for three wind treatments -> ledgers
-> community-benefit cost and GPU premium -> figures -> clean-reproduction check against the published
reference values. Outputs (dga_*.json, dga_*.npz, fig*.png, dga_reproduction_report.txt) are written
next to the scripts; no sub-folders are created.
"""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
MODES = ("rez", "palmer", "raw")
STEPS = [["dga_checksums.py", "--data-only"], ["dga_weather.py"]] + [["dga_model.py", m] for m in MODES] \
        + [["dga_analysis.py", m] for m in MODES] + [["dga_premium.py", m] for m in MODES] \
        + [["dga_figures.py"], ["dga_verify.py"]]
t0 = time.time()
for step in STEPS:
    print(">>", " ".join(step), flush=True)
    r = subprocess.run([sys.executable, "-B", os.path.join(HERE, step[0])] + step[1:], cwd=HERE,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = r.stdout.strip().splitlines()[-3:]
    print("   " + "\n   ".join(tail))
    if r.returncode:
        print(r.stdout); sys.exit(f"FAILED at {' '.join(step)}")
print(f"All steps complete in {time.time() - t0:.0f} s.")
