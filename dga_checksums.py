"""SHA-256 checksums for the input data and code of the Digital Gardens Australia model.

    python dga_checksums.py                      # verify every file listed in dga_checksums.sha256
    python dga_checksums.py --write              # (maintainer) rewrite dga_checksums.sha256
    python dga_checksums.py --compare-csv FILE   # compare a regenerated weather CSV with the supplied one

dga_checksums.sha256 uses the standard `sha256sum` format, so on Linux/macOS the same check is
`sha256sum -c dga_checksums.sha256` (or `shasum -a 256 -c dga_checksums.sha256`).

Model OUTPUTS are not listed: floating-point results can differ in the last digits between numpy
builds, so outputs are checked numerically against reference values by dga_verify.py instead.
"""
import os, sys, hashlib, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
LIST = os.path.join(HERE, "dga_checksums.sha256")
DATA = ["dispatch_hourly_wide.csv.gz", "provenance_manifest.json"]
CODE = ["dga_params.py", "dga_weather.py", "dga_model.py", "dga_analysis.py", "dga_premium.py", "dga_figures.py",
        "dga_verify.py", "dga_download_era5.py", "dga_checksums.py", "run_all.py", "dga_reference_values.json",
        "dga_aus_outline.json", "requirements.txt"]


def sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def write():
    lines = []
    for f in DATA + CODE:
        if f == "dga_checksums.py":
            continue          # a file cannot contain its own checksum reliably once edited; listed in README
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            print("  skipped (not present):", f)
            continue
        lines.append(f"{sha256(p)}  {f}")
    with open(LIST, "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {os.path.basename(LIST)} with {len(lines)} entries")


def verify(data_only=False):
    if not os.path.exists(LIST):
        print("dga_checksums.sha256 not found"); return 2
    bad = 0; n = 0
    for line in open(LIST):
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        name = name.lstrip("*")
        if data_only and name not in DATA:
            continue
        n += 1
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            print(f"  MISSING  {name}"); bad += 1; continue
        ok = sha256(p) == digest
        print(f"  {'OK      ' if ok else 'MISMATCH'} {name}")
        bad += 0 if ok else 1
    print(f"{n - bad} of {n} files verified" + ("" if bad == 0 else f"; {bad} problem(s)"))
    return 0 if bad == 0 else 1


def compare_csv(other, tol=1e-9):
    import numpy as np, pandas as pd
    a = pd.read_csv(os.path.join(HERE, "dispatch_hourly_wide.csv.gz"))
    b = pd.read_csv(other if os.path.isabs(other) else os.path.join(HERE, other))
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        print("shape or column mismatch", a.shape, b.shape); return 1
    if not (a["timestamp_utc"] == b["timestamp_utc"]).all():
        print("timestamp mismatch"); return 1
    num = a.columns[1:]
    na = a[num].isna().values != b[num].isna().values
    d = np.nanmax(np.abs(a[num].values - b[num].values))
    print(f"rows {len(a):,}; columns {a.shape[1]}; max abs difference {d:.3g}; NaN pattern mismatches {int(na.sum())}")
    ok = d <= tol and not na.any()
    print("IDENTICAL within tolerance" if ok else "DIFFERENT"); return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--data-only", action="store_true", help="verify the two input-data files only")
    ap.add_argument("--compare-csv")
    a = ap.parse_args()
    if a.write:
        write(); sys.exit(0)
    if a.compare_csv:
        sys.exit(compare_csv(a.compare_csv))
    sys.exit(verify(a.data_only))
