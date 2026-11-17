"""Clean-reproduction check: compare freshly computed results with the published reference values.

    python dga_verify.py                    # compare current outputs with dga_reference_values.json
    python dga_verify.py --make-reference   # (maintainer) freeze current outputs as the reference

Reads dga_numbers_{mode}.json, dga_premium_{mode}.json and dga_results_{mode}.json for the three
wind treatments and writes dga_reproduction_report.txt. A value passes when
|new - ref| <= ATOL + RTOL * |ref| (defaults: RTOL 1e-6, ATOL 1e-9). Exit code 0 = all pass.
"""
import os, sys, json, platform, argparse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
REF = os.path.join(HERE, "dga_reference_values.json")
REPORT = os.path.join(HERE, "dga_reproduction_report.txt")
MODES = ("rez", "palmer", "raw")
RTOL, ATOL = 1e-6, 1e-9


def load(mode):
    N = json.load(open(os.path.join(HERE, f"dga_numbers_{mode}.json")))
    R = json.load(open(os.path.join(HERE, f"dga_results_{mode}.json")))
    Q = json.load(open(os.path.join(HERE, f"dga_premium_{mode}.json")))
    S = {(s["portfolio"], s["scenario"]): s for s in R["scenarios"]}
    return N, R, Q, S


def headline(mode):
    """The quantities reported in the article, abstract, highlights and supplement tables."""
    N, R, Q, S = load(mode)
    e, a, m = S[("enlarged", "central")], S[("enlarged", "combined_adverse")], S[("enl_smr", "central")]
    sym = {r["label"]: r for r in N["sym_ext"]}
    v = {
        "E_ext_TWh": N["E_ext"], "E_core_TWh": N["E_core"], "E_fac_TWh": N["E_fac"],
        "pue_mean": N["pue_mean"],
        "dga_gross_Mt": e["gross"], "dga_net_Mt": sym["DGA enlarged (extended)"]["net"],
        "gas_unabated_net_Mt": sym["Gas campus unabated (extended)"]["net"],
        "gas_ccs90_net_Mt": sym["Gas campus 90% CCS (extended)"]["net"],
        "gas_ccs95_net_Mt": sym["Gas campus 95% CCS (extended)"]["net"],
        "smr_net_Mt": sym["DGA enlarged + SMR (extended)"]["net"],
        "credit_ext_Mt": N["cred_ext"], "heat_delivered_TWh": R["heat"]["full"]["delivered_twh"],
        "leak_crossover_pct": N["leak_cross_pct"],
        "central_unserved_TWh_16y": e["unserved_twh_16y"],
        "adverse_unserved_TWh_16y": a["unserved_twh_16y"], "adverse_peak_GW": a["ep_peak_gw"],
        "biodiesel_ML_y": e["hvo_ML"], "biodiesel_ML_max_year": e["hvo_ML_max_year"],
        "uco_ML_y": e["uco_ML"], "biogas_engine_PJ": e["bg_engine_PJ"], "biogas_surplus_PJ": e["bg_surplus_PJ"],
        "biogas_total_PJ": R["biogas_pj"], "engine_fuel_cost_AUDm": e["hvo_cost_m"],
        "export_TWh": e["exp_twh"], "curtail_TWh": e["curt_twh"], "import_TWh": e["imp_twh"],
        "smr_biodiesel_ML_y": m["hvo_ML"], "smr_capex_AUDbn": N["smr_capex_bn"],
        "ev_charging_GWh": R["ev_gwh"], "asp_t_DW": R["asp_t"], "asp_N_removed_t": R["asp_N_t"],
        "community_cost_AUDm_central": Q["total"]["central"],
        "community_cost_AUDm_low": Q["total"]["low"], "community_cost_AUDm_high": Q["total"]["high"],
        "premium_USD_per_GPU_h_central": Q["premium"]["community_central"]["usd_per_gpu_h"],
        "premium_pct_H100_central": Q["premium"]["community_central"]["pct"]["H100"],
        "premium_pct_B200_central": Q["premium"]["community_central"]["pct"]["B200"],
        "premium_USD_per_GPU_h_with_ers_high": Q["premium"]["with_ers_drones_high"]["usd_per_gpu_h"],
        "gpu_count": Q["n_gpu"],
    }
    for i, nm in enumerate(["MUS", "LIT", "TAR", "CAL", "LAT", "PTA", "COL"]):
        v[f"wind_cf_{nm}"] = R["wind_cf"][i]; v[f"pv_cf_{nm}"] = R["pv_cf"][i]
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
    lines = [f"Digital Gardens Australia - reproduction report ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
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
            lines.append(f"  {'PASS' if ok else 'FAIL'}  {k:38s} ref {r:16.6f}  new {x if x is None else round(x, 6)!s:>16}")
        lines.append("")
    lines.append(f"RESULT: {n - fails} of {n} values reproduced" + (" - CLEAN REPRODUCTION" if fails == 0 else f" - {fails} FAILED"))
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[-1:])); print("report:", os.path.basename(REPORT))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
