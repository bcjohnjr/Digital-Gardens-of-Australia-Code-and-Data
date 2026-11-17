"""SHA-256 checksums for the input data and code of the Digital Gardens Sunraysia model.

    python dgs_checksums.py                      # verify every file listed in dgs_checksums.sha256
    python dgs_checksums.py --write              # (maintainer) rewrite dgs_checksums.sha256
    python dgs_checksums.py --compare-csv FILE   # compare a regenerated weather CSV with the supplied one

dgs_checksums.sha256 uses the standard `sha256sum` format, so on Linux/macOS the same check is
`sha256sum -c dgs_checksums.sha256` (or `shasum -a 256 -c dgs_checksums.sha256`).

Model OUTPUTS are not listed: floating-point results can differ in the last digits between numpy
builds, so outputs are checked numerically against reference values by dgs_verify.py instead.
"""
import os, sys, hashlib, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
LIST = os.path.join(HERE, "dgs_checksums.sha256")
DATA = ["dgs_era5_hourly.csv.gz", "dgs_provenance_manifest.json", "dgs_towns_2021.csv"]
CODE = ["dgs_params.py", "dgs_weather.py", "dgs_model.py", "dgs_analysis.py", "dgs_premium.py", "dgs_figures.py",
        "dgs_verify.py", "dgs_download_era5.py", "dgs_checksums.py", "run_all.py", "dgs_reference_values.json",
        "dgs_aus_outline.json", "requirements.txt"]


def sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def write():
    lines = []
    for f in DATA + CODE:
        if f == "dgs_checksums.py":
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
        print("dgs_checksums.sha256 not found"); return 2
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
    a = pd.read_csv(os.path.join(HERE, "dgs_era5_hourly.csv.gz"))
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
