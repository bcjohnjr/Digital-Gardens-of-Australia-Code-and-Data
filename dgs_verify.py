"""Clean-reproduction check: compare freshly computed results with the published reference values.

    python dgs_verify.py                    # compare current outputs with dgs_reference_values.json
    python dgs_verify.py --make-reference   # (maintainer) freeze current outputs as the reference

Reads dgs_numbers_{mode}.json, dgs_premium_{mode}.json and dgs_results_{mode}.json for the three
wind treatments and writes dgs_reproduction_report.txt. A value passes when
|new - ref| <= ATOL + RTOL * |ref| (defaults: RTOL 1e-6, ATOL 1e-9). Exit code 0 = all pass.
"""
import os, sys, json, platform, argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
REF = os.path.join(HERE, "dgs_reference_values.json")
REPORT = os.path.join(HERE, "dgs_reproduction_report.txt")
MODES = ("rez", "palmer", "raw")
RTOL, ATOL = 1e-6, 1e-9


def load(mode):
    N = json.load(open(os.path.join(HERE, f"dgs_numbers_{mode}.json")))
    R = json.load(open(os.path.join(HERE, f"dgs_results_{mode}.json")))
    Q = json.load(open(os.path.join(HERE, f"dgs_premium_{mode}.json")))
    S = None
    return N, R, Q, S


def headline(mode):
    """The quantities reported in the article, abstract, highlights and supplement tables."""
    N, R, Q, S = load(mode)
    v = {"E_fac_TWh": N["E_fac"], "E_ext_TWh": N["E_ext"], "pue_mean": N["pue_mean"], "heat_credit_Mt": N["credit"],
         "heat_delivered_TWh": N["heat"]["delivered"], "biogas_PJ": N["biogas"]["pj"], "ev_GWh": N["vehicles"]["ev_gwh"],
         "leak_cross_pct": N["leak_cross_pct"], "named_total_Mt": N["named_total_mt"],
         "community_cost_central_AUDm": Q["total"]["central"], "community_cost_low_AUDm": Q["total"]["low"],
         "community_cost_high_AUDm": Q["total"]["high"],
         "premium_USD_per_GPU_h": Q["premium"]["community_central"]["usd_per_gpu_h"],
         "premium_pct_H100": Q["premium"]["community_central"]["pct"]["H100"], "gpu_count": Q["n_gpu"],
         "pv_cf": N["pv_cf"], "wind_cf": N["wind_cf"]}
    for r in N["ledger"]:
        v["net_" + r["label"]] = r["net"]
    for r in N["portfolio_rows"]:
        k = f"{r['portfolio']}_{r['scenario']}"
        v[f"{k}_gross"] = r["gross"]; v[f"{k}_imp_TWh"] = r["imp_twh"]; v[f"{k}_unserved_MWh"] = r["unserved_mwh_16y"]
        v[f"{k}_biodiesel_ML"] = r["bd_ML"]
    for r in N["nodal_rows"]:
        k = f"{r['portfolio']}_{r['scenario']}"
        v[f"{k}_gross"] = r["gross"]; v[f"{k}_unserved_MWh"] = r["uns"]; v[f"{k}_imp_TWh"] = r["imp"]
    for r in N["it_rows"]:
        k = f"it{r['it']:.0f}_{r['scenario']}"
        v[f"{k}_gross"] = r["gross"]; v[f"{k}_unserved_share"] = r["uns_share"]; v[f"{k}_re_share"] = r["re"]
    return {k: float(x) for k, x in v.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-reference", action="store_true")
    ap.add_argument("--rtol", type=float, default=RTOL)
    a = ap.parse_args()
    cur = {m: headline(m) for m in MODES}
    if a.make_reference:
        json.dump(dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                       note="Values published in the manuscript; regenerate only when the model changes.",
                       values=cur), open(REF, "w"), indent=1)
        print("wrote", os.path.basename(REF)); return 0
    ref = json.load(open(REF))["values"]
    import numpy, pandas, scipy, matplotlib
    lines = [f"Digital Gardens Sunraysia - reproduction report ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
             f"python {platform.python_version()} | numpy {numpy.__version__} | pandas {pandas.__version__} | "
             f"scipy {scipy.__version__} | matplotlib {matplotlib.__version__} | {platform.platform()}",
             f"tolerance: |new-ref| <= {ATOL:g} + {a.rtol:g}*|ref|", ""]
    fails = 0; n = 0
    for m in MODES:
        lines.append(f"[{m}]")
        for k, r in ref[m].items():
            n += 1
            x = cur[m].get(k)
            ok = x is not None and abs(x - r) <= ATOL + a.rtol * abs(r)
            fails += 0 if ok else 1
            lines.append(f"  {'PASS' if ok else 'FAIL'}  {k:58s} ref {r:16.6f}  new {x if x is None else round(x, 6)!s:>16}")
        lines.append("")
    lines.append(f"RESULT: {n - fails} of {n} values reproduced" + (" - CLEAN REPRODUCTION" if fails == 0 else f" - {fails} FAILED"))
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[-1:])); print("report:", os.path.basename(REPORT))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
