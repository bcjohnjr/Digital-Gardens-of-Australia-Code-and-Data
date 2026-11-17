"""Community-benefit cost ledger and the GPU-rental premium needed to fund it.

Run: python dgs_premium.py [rez|palmer|raw]
Reads dgs_results_{mode}.json and dgs_numbers_{mode}.json (written by dgs_model.py and dgs_analysis.py)
and writes dgs_premium_{mode}.json. All money is A$ (2026) per year unless stated; capital items are
annualised with a capital-recovery factor at 8% real over the asset life given below.

The premium answers one question: if every community benefit were paid for by a surcharge on GPU
rental hours sold from the six Sunraysia campuses, how large would that surcharge be? Electricity-supply costs
(wind, solar, batteries, engines, fuel, imports) are NOT in this ledger; they are the cost of the
computing service itself and are compared separately in the carbon and adequacy sections.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dgs_params as P

MODE = sys.argv[1] if len(sys.argv) > 1 else "rez"
R = json.load(open(os.path.join(HERE, f"dgs_results_{MODE}.json")))
N = json.load(open(os.path.join(HERE, f"dgs_numbers_{MODE}.json")))
S = {(s["it_mw"], s["portfolio"], s["scenario"]): s for s in R["scenarios"]}
enl = S[(P.IT_MW, "balanced", "central")]
RATE = 0.08


def crf(n, r=RATE):
    return r / (1 - (1 + r) ** -n)


econ = {e["case"]: e for e in N["econ"]}
items = []   # (key, label, low, central, high, note)


def add(key, label, lo, ce, hi, note):
    items.append(dict(key=key, label=label, low=lo, central=ce, high=hi, note=note))


# 1. food, hot water, heat cascade, LED glasshouses, RAS
op = {k: econ[k]["opcost"] for k in econ}
cc = {k: econ[k]["capchg"] for k in econ}
add("cascade_op", "Purple-LED glasshouses, freshwater RAS, heat pumps: operating cost",
    op["high"], op["central"], op["low"], "electricity at A$100/MWh, labour, fish feed")
add("cascade_cap", "Glasshouses, RAS, heat pumps, LEDs: capital charge",
    cc["high"], cc["central"], cc["low"], "8% capital charge")
hh_c = R["hh_connected"]
hn = hh_c * P.HEAT_CONNECT_AUD * crf(40) / 1e6
add("heat_connect", "Hot-water loop connections to homes", 0.7 * hn, hn, 1.4 * hn,
    f"{hh_c:,.0f} dwellings x A${P.HEAT_CONNECT_AUD:,.0f}, 40-y life")
dry_cap = P.DRYING_T * 400.0 * crf(15) / 1e6
add("drying", "Warm-water drying service for local growers: dryers and handling", 0.7 * dry_cap, dry_cap, 1.4 * dry_cap,
    f"{P.DRYING_T:,.0f} t/y at A$400 per t/y capacity, 15-y life; heat from the cascade")
bg_all = N["biogas"]["pj"] * 1e6 * P.BIOGAS_AUD_GJ / 1e6
bm = enl["bg_surplus_PJ"] * 1e6 * P.BIOMETHANE_UPGRADE_AUD_GJ / 1e6
add("biogas", "Biogas digesters (all residues) and biomethane upgrading of surplus", 0.7 * (bg_all + bm), bg_all + bm, 1.4 * (bg_all + bm),
    f"{N['biogas']['pj']:.3f} PJ/y at A${P.BIOGAS_AUD_GJ:.0f}/GJ; {enl['bg_surplus_PJ']:.3f} PJ upgraded at A${P.BIOMETHANE_UPGRADE_AUD_GJ:.0f}/GJ")
nv = R["n_veh"]
veh_unit = P.VEH_EV_SHARE * P.VEH_EV_AUD + (1 - P.VEH_EV_SHARE) * P.VEH_PHEV_AUD
veh = nv * veh_unit * crf(P.VEH_LIFE_Y) / 1e6
add("vehicles", "Free EV or plug-in hybrid, one per household", 0.75 * veh, veh, 1.15 * veh,
    f"{nv:,.0f} vehicles x A${veh_unit:,.0f}, {P.VEH_LIFE_Y:.0f}-y life; low = 25% cheaper EVs by 2030")
chg_e = R["ev_gwh"] * 1e3 * P.ELEC_AUD_MWH / 1e6
chg_c = nv * P.CHARGER_AUD * crf(10) / 1e6
add("charging", "Free charging: electricity and home chargers", 0.8 * (chg_e + chg_c), chg_e + chg_c, 1.25 * (chg_e + chg_c),
    f"{R['ev_gwh']:.0f} GWh/y at A${P.ELEC_AUD_MWH:.0f}/MWh + {nv:,.0f} chargers at A${P.CHARGER_AUD:,.0f}")
bm_L = enl["bg_surplus_PJ"] * 1e9 / 38.6e6 * 1e6
par_vol = max(P.FARM_FUEL_ML * 1e6 - bm_L, 0.0) + R["phev_fuel_ML"] * 1e6
par = [par_vol * g / 1e6 for g in P.PARITY_GAP_AUD_L]
add("parity", "Renewable-fuel price parity for farms and hybrids", par[0], par[1], par[2],
    f"{par_vol / 1e6:.1f} ML/y x A${P.PARITY_GAP_AUD_L[0]:.2f}-{P.PARITY_GAP_AUD_L[2]:.2f}/L")
uco_admin = P.UCO_ML * 1e6 * 0.05 / 1e6
add("uco", "Used-cooking-oil purchase programme: collection and administration",
    0.5 * uco_admin, uco_admin, 2.0 * uco_admin, f"{P.UCO_ML:.0f} ML/y at A$0.05/L on top of the A${P.UCO_AUD_L:.2f}/L price")

tot = {c: sum(i[c] for i in items) for c in ("low", "central", "high")}

addon = [0.0, 0.0, 0.0]

# value delivered (market value of what residents receive)
value = dict(food=econ["central"]["produce"] + econ["central"]["seafood"], hot_water_heat=econ["central"]["hh_heat"],
             vehicles=veh, charging=R["ev_gwh"] * 1e3 * 300 / 1e6, fuel_parity=par[1],
             drying=P.DRYING_T * 150.0 / 1e6)
value["total"] = sum(value.values())

# GPU basis
n_gpu = P.IT_MW * 1e3 / P.GPU_KW
gpu_h = n_gpu * P.HPY * P.GPU_UTIL
it_mwh = P.IT_MW * P.HPY
prem = {}
for c in ("low", "central", "high"):
    for lab, extra in (("community", 0.0),):
        a = (tot[c] + extra) * 1e6
        aud_h = a / gpu_h
        usd_h = aud_h * P.USD_PER_AUD
        prem[f"{lab}_{c}"] = dict(aud_m=a / 1e6, aud_per_gpu_h=aud_h, usd_per_gpu_h=usd_h,
                                  aud_per_mwh_it=a / it_mwh,
                                  pct={g: usd_h / p for g, p in P.GPU_PRICE_USD_H.items()},
                                  per_resident=a / P.POP)
# break-even utilisation sensitivity
util_sens = {str(u): tot["central"] * 1e6 / (n_gpu * P.HPY * u) * P.USD_PER_AUD for u in (0.5, 0.7, 0.9)}
# headroom to the 9.7% average willingness-to-pay premium
headroom = {g: P.WTP_PREMIUM * p for g, p in P.GPU_PRICE_USD_H.items()}

out = dict(mode=MODE, items=items, total=tot,
           value=value, n_gpu=n_gpu, gpu_h=gpu_h, gpu_kw=P.GPU_KW, util=P.GPU_UTIL, usd_per_aud=P.USD_PER_AUD,
           gpu_price_usd_h=P.GPU_PRICE_USD_H, premium=prem, util_sens_usd=util_sens, wtp=P.WTP_PREMIUM,
           wtp_headroom_usd_h=headroom, crf_vehicle=crf(P.VEH_LIFE_Y), rate=RATE)
json.dump(out, open(os.path.join(HERE, f"dgs_premium_{MODE}.json"), "w"), indent=1, default=float)

print(f"community ledger ({MODE}), A$ million/year")
for i in items:
    print(f"  {i['label'][:70]:70s} {i['low']:8.1f} {i['central']:8.1f} {i['high']:8.1f}")
print(f"  {'TOTAL':70s} {tot['low']:8.1f} {tot['central']:8.1f} {tot['high']:8.1f}")
print(f"GPUs {n_gpu:,.0f}; GPU-h sold {gpu_h / 1e9:.2f} bn/y")
for k, v in prem.items():
    print(f"  {k:26s} A${v['aud_per_gpu_h']:.3f}/GPU-h = US${v['usd_per_gpu_h']:.3f}; "
          + " ".join(f"{g} {x * 100:.1f}%" for g, x in v["pct"].items()))
print("value delivered", {k: round(v, 1) for k, v in value.items()})
