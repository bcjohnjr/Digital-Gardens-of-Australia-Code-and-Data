"""Community-benefit cost ledger and the GPU-rental premium needed to fund it.

Run: python dga_premium.py [rez|palmer|raw]
Reads dga_results_{mode}.json and dga_numbers_{mode}.json (written by dga_model.py and dga_analysis.py)
and writes dga_premium_{mode}.json. All money is A$ (2026) per year unless stated; capital items are
annualised with a capital-recovery factor at 8% real over the asset life given below.

The premium answers one question: if every community benefit were paid for by a surcharge on GPU
rental hours sold from the seven hubs, how large would that surcharge be? Electricity-supply costs
(wind, solar, batteries, engines, fuel, imports) are NOT in this ledger; they are the cost of the
computing service itself and are compared separately in the carbon and adequacy sections.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dga_params as P

MODE = sys.argv[1] if len(sys.argv) > 1 else "rez"
R = json.load(open(os.path.join(HERE, f"dga_results_{MODE}.json")))
N = json.load(open(os.path.join(HERE, f"dga_numbers_{MODE}.json")))
S = {(s["portfolio"], s["scenario"]): s for s in R["scenarios"]}
enl = S[("enlarged", "central")]
RATE = 0.08


def crf(n, r=RATE):
    return r / (1 - (1 + r) ** -n)


econ = {e["case"]: e for e in N["econ"]}
items = []   # (key, label, low, central, high, note)


def add(key, label, lo, ce, hi, note):
    items.append(dict(key=key, label=label, low=lo, central=ce, high=hi, note=note))


# 1. food, hot water, heat cascade, drying, desalinated water, kelp and Asparagopsis operation
for k in ("low", "central", "high"):
    pass
op = {k: econ[k]["opcost"] for k in econ}
cc = {k: econ[k]["capchg"] for k in econ}
add("cascade_op", "Glasshouses, RAS seafood, heat pumps, MED water, seaweed: operating cost",
    op["high"], op["central"], op["low"],   # econ 'high' case uses the lowest cost multipliers
    "electricity at A$100/MWh, labour, fish feed (dga_analysis econ block)")
add("cascade_cap", "Glasshouses, RAS, heat pumps, MED plant: capital charge",
    cc["high"], cc["central"], cc["low"], "8% capital charge on A$1.80 bn installed")
# heat network branches to dwellings (hot water and space heat for connected homes)
hh_c = R["hh_connected"]
hn = hh_c * P.HEAT_CONNECT_AUD * crf(40) / 1e6
add("heat_connect", "Hot-water network connections to homes", 0.7 * hn, hn, 1.4 * hn,
    f"{hh_c:,.0f} dwellings x A${P.HEAT_CONNECT_AUD:,.0f}, 40-y life")
# Asparagopsis algae-scrubber raceways, drying, distribution to farmers
asp_cap = R["asp_ha"] * 1.0e6 * crf(20) / 1e6
asp_dist = R["asp_t"] * 150.0 / 1e6
add("asparagopsis", "Asparagopsis algae-scrubber raceways, drying line and farm distribution",
    0.6 * (asp_cap + asp_dist), asp_cap + asp_dist, 1.6 * (asp_cap + asp_dist),
    f"{R['asp_ha']:.0f} ha at A$1.0 M/ha (20-y), A$150/t delivery; labour already in operating cost")
# community drying service equipment
dry_cap = P.COMMUNITY_DRYING_T * 400.0 * crf(15) / 1e6
add("drying", "Farm-produce drying service: dryers and handling", 0.7 * dry_cap, dry_cap, 1.4 * dry_cap,
    f"{P.COMMUNITY_DRYING_T:,} t/y at A$400 per t/y capacity, 15-y life; heat from the cascade")
# digesters: the biogas burnt in engines is paid for in the electricity fuel bill; only the surplus
# upgraded to biomethane for farm vehicles is a community cost
bm = enl["bg_surplus_PJ"] * 1e6 * (P.BIOGAS_AUD_GJ + P.BIOMETHANE_UPGRADE_AUD_GJ) / 1e6
add("biomethane", "Surplus biogas upgraded to biomethane farm fuel", 0.7 * bm, bm, 1.4 * bm,
    f"{enl['bg_surplus_PJ']:.2f} PJ/y at A${P.BIOGAS_AUD_GJ + P.BIOMETHANE_UPGRADE_AUD_GJ:.0f}/GJ")
# free vehicle per household
nv = R["n_veh"]
veh_unit = P.VEH_EV_SHARE * P.VEH_EV_AUD + (1 - P.VEH_EV_SHARE) * P.VEH_PHEV_AUD
veh = nv * veh_unit * crf(P.VEH_LIFE_Y) / 1e6
add("vehicles", "Free EV or plug-in hybrid, one per enrolled household", 0.75 * veh, veh, 1.15 * veh,
    f"{nv:,.0f} vehicles x A${veh_unit:,.0f}, {P.VEH_LIFE_Y:.0f}-y life; low = 25% cheaper EVs by 2030")
# free charging: energy at the DGA supply cost plus home chargers
chg_e = R["ev_gwh"] * 1e3 * P.ELEC_AUD_MWH / 1e6
chg_c = nv * P.CHARGER_AUD * crf(10) / 1e6
add("charging", "Free charging: electricity and home chargers", 0.8 * (chg_e + chg_c), chg_e + chg_c, 1.25 * (chg_e + chg_c),
    f"{R['ev_gwh']:.0f} GWh/y at A${P.ELEC_AUD_MWH:.0f}/MWh + {nv:,.0f} chargers at A${P.CHARGER_AUD:,.0f}")
# renewable-fuel parity for farmers and hybrid drivers (biomethane covers part of the farm volume)
bm_L = enl["bg_surplus_PJ"] * 1e9 / 38.6e6 * 1e6
par_vol = max(P.FARM_FUEL_ML * 1e6 - bm_L, 0.0) + R["phev_fuel_ML"] * 1e6
par = [par_vol * g / 1e6 for g in P.PARITY_GAP_AUD_L]
add("parity", "Renewable-fuel price parity for farms and hybrids", par[0], par[1], par[2],
    f"{par_vol / 1e6:.1f} ML/y x A${P.PARITY_GAP_AUD_L[0]:.2f}-{P.PARITY_GAP_AUD_L[2]:.2f}/L")
# used-cooking-oil programme administration (the oil itself is engine fuel, paid for in the fuel bill)
uco_admin = P.UCO_ML * 1e6 * 0.05 / 1e6
add("uco", "Used-cooking-oil purchase programme: collection and administration",
    0.5 * uco_admin, uco_admin, 2.0 * uco_admin, f"{P.UCO_ML:.0f} ML/y at A$0.05/L on top of the A${P.UCO_AUD_L:.2f}/L price")

tot = {c: sum(i[c] for i in items) for c in ("low", "central", "high")}

# optional regional add-ons: electrified highways (net of diesel savings) and delivery drones
ers_cc = N["ers_capcharge_m"]                     # [low, high] A$M/y
ers_net = [ers_cc[0] - N["ers_saving_m"], 0.5 * sum(ers_cc) - N["ers_saving_m"], ers_cc[1] - N["ers_saving_m"]]
drones = R["drones_total"] * 60_000 * crf(5) / 1e6 + N["drone"] * 1e6 * P.ELEC_AUD_MWH / 1e6
addon = [max(ers_net[0], 0) + 0.7 * drones, max(ers_net[1], 0) + drones, max(ers_net[2], 0) + 1.4 * drones]

# value delivered (market value of what residents receive)
value = dict(food=econ["central"]["produce"] + econ["central"]["seafood"], hot_water_heat=econ["central"]["hh_heat"],
             water=econ["central"]["water"],
             vehicles=veh, charging=R["ev_gwh"] * 1e3 * 300 / 1e6,
             fuel_parity=par[1], asparagopsis=R["asp_t"] * 1e3 * 30 / 1e6)
value["total"] = sum(value.values())

# GPU basis
n_gpu = P.IT_GW * 1e6 / P.GPU_KW
gpu_h = n_gpu * P.HPY * P.GPU_UTIL
it_mwh = P.IT_TWH * 1e6
prem = {}
for c in ("low", "central", "high"):
    for lab, extra in (("community", 0.0), ("with_ers_drones", addon[("low", "central", "high").index(c)])):
        a = (tot[c] + extra) * 1e6
        aud_h = a / gpu_h
        usd_h = aud_h * P.USD_PER_AUD
        prem[f"{lab}_{c}"] = dict(aud_m=a / 1e6, aud_per_gpu_h=aud_h, usd_per_gpu_h=usd_h,
                                  aud_per_mwh_it=a / it_mwh,
                                  pct={g: usd_h / p for g, p in P.GPU_PRICE_USD_H.items()},
                                  per_resident=a / P.ENROLLED)
# break-even utilisation sensitivity
util_sens = {str(u): tot["central"] * 1e6 / (n_gpu * P.HPY * u) * P.USD_PER_AUD for u in (0.5, 0.7, 0.9)}
# headroom to the 9.7% average willingness-to-pay premium
headroom = {g: P.WTP_PREMIUM * p for g, p in P.GPU_PRICE_USD_H.items()}

out = dict(mode=MODE, items=items, total=tot, addon_ers_drones=addon, ers_net=ers_net, drones=drones,
           value=value, n_gpu=n_gpu, gpu_h=gpu_h, gpu_kw=P.GPU_KW, util=P.GPU_UTIL, usd_per_aud=P.USD_PER_AUD,
           gpu_price_usd_h=P.GPU_PRICE_USD_H, premium=prem, util_sens_usd=util_sens, wtp=P.WTP_PREMIUM,
           wtp_headroom_usd_h=headroom, crf_vehicle=crf(P.VEH_LIFE_Y), rate=RATE)
json.dump(out, open(os.path.join(HERE, f"dga_premium_{MODE}.json"), "w"), indent=1, default=float)

print(f"community ledger ({MODE}), A$ million/year")
for i in items:
    print(f"  {i['label'][:70]:70s} {i['low']:8.1f} {i['central']:8.1f} {i['high']:8.1f}")
print(f"  {'TOTAL':70s} {tot['low']:8.1f} {tot['central']:8.1f} {tot['high']:8.1f}")
print(f"  add-on ERS+drones {addon}")
print(f"GPUs {n_gpu:,.0f}; GPU-h sold {gpu_h / 1e9:.2f} bn/y")
for k, v in prem.items():
    print(f"  {k:26s} A${v['aud_per_gpu_h']:.3f}/GPU-h = US${v['usd_per_gpu_h']:.3f}; "
          + " ".join(f"{g} {x * 100:.1f}%" for g, x in v["pct"].items()))
print("value delivered", {k: round(v, 1) for k, v in value.items()})
