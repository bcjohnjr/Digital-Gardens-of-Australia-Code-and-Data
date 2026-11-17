"""Run the full Digital Gardens Australia analysis. Everything lives in this one folder.

    python run_all.py

Steps: weather conversion -> ERA5 dispatch for three wind treatments -> synthetic comparison
-> ledgers -> figures. Outputs (dga_*.json, dga_*.npz, fig*.png) are written next to the scripts.
"""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [["dga_weather.py"]] + [["dga_model.py", m] for m in ("rez", "palmer", "raw")] + [["dga_model_synthetic.py"]] \
        + [["dga_analysis.py", m] for m in ("rez", "palmer", "raw", "synthetic")] + [["dga_figures.py"]]
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
