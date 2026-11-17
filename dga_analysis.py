"""Derive all manuscript numbers. Run: python dga_analysis.py [rez|palmer|raw|synthetic]"""
import sys, json, math

import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True          # keep the folder flat: no __pycache__
sys.path.insert(0, HERE)
import dga_params as P
MODE = sys.argv[1] if len(sys.argv) > 1 else "rez"
R = json.load(open(os.path.join(HERE, f"dga_results_{MODE}.json")))
S = {(s["portfolio"], s["scenario"]): s for s in R["scenarios"]}
N = {}


def g(pf, sc):
    return S[(pf, sc)]

enl = g("enlarged", "central"); ref = g("reference", "central"); smr = g("enl_smr", "central")
adv = g("enlarged", "combined_adverse")
heat = R["heat"]; gas = R["gas"]
N["E_fac"] = R["fac_twh"]; N["E_core"] = R["E_core"]; N["E_ext"] = R["E_ext"]
N["boost"] = R["boost_twh"]; N["ras"] = R["ras_twh"]; N["sw_e"] = R["sw_e_twh"]; N["wat_e"] = R["wat_e_twh"]
N["hp_full"] = heat["full"]["hp_twh"]; N["ers"] = R["ers_twh"]; N["drone"] = R["drone_twh"]; N["ev"] = R["ev_twh"]
N["E_fac_boost"] = N["E_fac"] + N["boost"]

# ---------------- gas comparator tables
gt = []
for lab, E in [("facility", N["E_fac"]), ("facility_boost", N["E_fac_boost"]), ("core", N["E_core"]), ("ext", N["E_ext"])]:
    for c in ["0.0", "0.9", "0.95"]:
        x = gas[lab][c]
        gt.append(dict(basis=lab, E=E, capture=float(c), fuel_twh=x["fuel_twh"], co2=x["co2"], ch4=x["ch4"],
                       total=x["total"], nonelec=x["nonelec_twh"]))
N["gas_table"] = gt
G = {(r["basis"], r["capture"]): r for r in gt}

# ---------------- credits (symmetric)
cred_heat = heat["full"]["credit_mt"]
cred_ers = R["ers_credit_mt"]; cred_drone = R["drone_credit_mt"]
cred_core = cred_heat
cred_ext = cred_heat + cred_ers + cred_drone
N.update(cred_heat=cred_heat, cred_ers=cred_ers, cred_drone=cred_drone, cred_core=cred_core, cred_ext=cred_ext)

dg_gross_ext = enl["gross"]
core_run = g("enlarged", "heat_full_core_central")
dg_gross_core = core_run["gross"]
N["dg"] = {k: enl[k] for k in ["c_wind", "c_pv", "c_batt", "c_imp", "c_hvo", "c_smr", "gross"]}
N["dg_core"] = {k: core_run[k] for k in ["c_wind", "c_pv", "c_batt", "c_imp", "c_hvo", "c_smr", "gross"]}
N["dg_smr"] = {k: smr[k] for k in ["c_wind", "c_pv", "c_batt", "c_imp", "c_hvo", "c_smr", "gross"]}
sym = []
for lab, gross, credit, basis in [("DGA enlarged (extended)", dg_gross_ext, cred_ext, None),
                                  ("DGA enlarged + SMR (extended)", smr["gross"], cred_ext, None),
                                  ("Gas campus unabated (extended)", G[("ext", 0.0)]["total"], cred_ext, None),
                                  ("Gas campus 90% CCS (extended)", G[("ext", 0.9)]["total"], cred_ext, None),
                                  ("Gas campus 95% CCS (extended)", G[("ext", 0.95)]["total"], cred_ext, None)]:
    sym.append(dict(label=lab, gross=gross, credit=credit, net=gross - credit))
symc = []
for lab, gross in [("DGA enlarged (core)", dg_gross_core), ("Gas unabated (core)", G[("core", 0.0)]["total"]),
                   ("Gas 90% CCS (core)", G[("core", 0.9)]["total"]), ("Gas 95% CCS (core)", G[("core", 0.95)]["total"])]:
    symc.append(dict(label=lab, gross=gross, credit=cred_core, net=gross - cred_core))
N["sym_ext"] = sym; N["sym_core"] = symc
N["ratio_unabated_ext"] = sym[0]["net"] / sym[2]["net"]
N["ratio_95_ext"] = sym[0]["net"] / sym[4]["net"]
N["ratio_unabated_core"] = symc[0]["net"] / symc[1]["net"]
N["ratio_95_core"] = symc[0]["net"] / symc[3]["net"]
N["gap95_ext"] = sym[4]["net"] - sym[0]["net"]
N["gap95_core"] = symc[3]["net"] - symc[0]["net"]
N["gap90_ext"] = sym[3]["net"] - sym[0]["net"]

# methane leakage screen (95% capture, extended basis)
x95 = G[("ext", 0.95)]
d95 = x95["co2"]; m95 = x95["ch4"]
N["d95"] = d95; N["m95_1pct"] = m95
N["leak_cross_pct"] = (dg_gross_ext - d95) / m95 * 1.0
N["leak_rows"] = [dict(leak=l, gross=d95 + m95 * l / 1.0 * (1 - 0.01) / (1 - l / 100) if l < 100 else None,
                       net=d95 + m95 * l * (1 - 0.01) / (1 - l / 100) - cred_ext) for l in [0.0, 0.5, 1.0, 2.0]]
for r in N["leak_rows"]:
    r["gross"] = d95 + m95 * r["leak"] * (1 - 0.01) / (1 - r["leak"] / 100)
    r["net"] = r["gross"] - cred_ext
N["leak_cross_pct"] = None
lo, hi = 0.0, 5.0
for _ in range(80):
    mid = 0.5 * (lo + hi)
    v = d95 + m95 * mid * 0.99 / (1 - mid / 100)
    if v < dg_gross_ext:
        lo = mid
    else:
        hi = mid
N["leak_cross_pct"] = mid
# AR6 fossil methane GWP sensitivity
N["gas95_ar6"] = d95 + m95 * 29.8 / P.GWP_CH4
N["gas0_ar6"] = G[("ext", 0.0)]["co2"] + G[("ext", 0.0)]["ch4"] * 29.8 / P.GWP_CH4

# omitted-inventory table
gap = N["gap95_ext"]
N["omit_rows"] = [dict(dDG=a, dWV=b, gap=gap + b - a) for a, b in [(0, 0), (0.25, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)]]

# ---------------- carbon factor sensitivities (DGA enlarged central)
def dg_with(pv=None, imp_scale=None, hvo_g=None, imp_flat=None):
    c = dict(N["dg"])
    if pv is not None:
        c["c_pv"] = c["c_pv"] * pv / P.PV_G_KWH
    if imp_flat is not None:
        c["c_imp"] = enl["imp_twh"] * imp_flat
    if hvo_g is not None:
        c["c_hvo"] = c["c_hvo"] * hvo_g / P.HVO_G_PER_MJ
    return sum(v for k, v in c.items() if k.startswith("c_"))
N["sens_pv"] = {str(v): dg_with(pv=v) for v in [12, 37, 48]}
N["sens_hvo"] = {str(v): dg_with(hvo_g=v) for v in [17.48, 25, 50]}
N["sens_imp"] = {str(v): dg_with(imp_flat=v) for v in [0.10, 0.30, 0.80]}
N["imp_mean_factor"] = enl["c_imp"] / enl["imp_twh"] if enl["imp_twh"] else 0

# ---------------- thermal balances
hvo_nonelec = enl["hvo_twh"] / P.HVO_ELEC_EFF - enl["hvo_twh"]
smr_nonelec = smr["smr_twh"] / 0.33 - smr["smr_twh"]
smr_hvo_nonelec = smr["hvo_twh"] / P.HVO_ELEC_EFF - smr["hvo_twh"]
src_extract = heat["full"]["delivered_twh"] / (1 - P.HEAT_LOSS) - heat["full"]["hp_twh"]
N.update(hvo_nonelec=hvo_nonelec, smr_nonelec=smr_nonelec + smr_hvo_nonelec, src_extract=src_extract)
th = []
for lab, gen in [("DGA enlarged, HVO engines", hvo_nonelec), ("DGA enlarged + 2.4 GW SMR", smr_nonelec + smr_hvo_nonelec),
                 ("Gas campus CCGT, no CCS", G[("ext", 0.0)]["nonelec"]),
                 ("Gas campus CCGT + 90% CCS penalty", G[("ext", 0.9)]["nonelec"])]:
    th.append(dict(label=lab, facility=N["E_fac"], gen=gen, unextracted=N["E_fac"] + gen - src_extract))
N["thermal"] = th
N["heat_util_share"] = src_extract / N["E_fac"]

# heat cases
hcs = []
for k, lab in [("full", "Full network (100%, 3.0x)"), ("plant1x", "Plant 1.0x"), ("half", "50% connected"), ("none", "No network")]:
    load = "full_core" if k == "full" else k
    cen = g("enlarged", f"heat_{load}_central"); ad = g("enlarged", f"heat_{load}_combined_adverse")
    xx = g("enlarged", f"heat_{load}_central")
    E = heat[k]["core_service_twh"]
    gas95 = (E * 3.6e6 / P.CCGT_EFF_HHV * 1.15) * (P.GAS_KG_PER_GJ * 0.05 + P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4) / 1e9
    gas0 = (E * 3.6e6 / P.CCGT_EFF_HHV) * (P.GAS_KG_PER_GJ + P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4) / 1e9
    hcs.append(dict(case=k, label=lab, delivered=heat[k]["delivered_twh"], hp=heat[k]["hp_twh"], E_core=E,
                    credit=heat[k]["credit_mt"], dg_gross=xx["gross"], dg_net=xx["gross"] - heat[k]["credit_mt"],
                    gas0=gas0, gas95=gas95, gas95_net=gas95 - heat[k]["credit_mt"], gas0_net=gas0 - heat[k]["credit_mt"],
                    uns_central=cen["unserved_twh_16y"], uns_adverse=ad["unserved_twh_16y"], peak_adverse=ad["ep_peak_gw"]))
N["heat_cases"] = hcs
N["heat_parts"] = heat["full"]["parts"]
N["heat_demand"] = heat["full"]["demand_twh"]

# ---------------- adequacy tables
ad_rows = []
for sc in ["central", "wind_minus10", "pv_minus10", "half_access", "firm_restricted", "combined_adverse", "central_flat_load"]:
    if ("enlarged", sc) not in S:
        continue
    row = dict(scenario=sc)
    for pf in ["reference", "enlarged", "enl_smr"]:
        s = g(pf, sc)
        row[pf] = dict(uns=s["unserved_twh_16y"], peak=s["ep_peak_gw"], hours=s["ep_hours"], episodes=s["ep_episodes"],
                       longest=s["ep_longest"], h1gw=s["ep_h_ge1gw"], hvo_ML=s["hvo_ML"], imp=s["imp_twh"],
                       exp=s["exp_twh"], curt=s["curt_twh"], gross=s["gross"], share=s["unserved_share"],
                       hvo_ML_max=s["hvo_ML_max_year"], moved=s["moved_twh"])
    ad_rows.append(row)
N["adequacy"] = ad_rows

# ---------------- firm backup screen for combined adverse (enlarged)
Eb = adv["unserved_twh_16y"] / P.YEARS
N["backup_twh_y"] = Eb
fb = []
for eff in [0.57, 0.50, 0.38]:
    fuel_GJ = Eb * 3.6e6 / eff
    co2 = fuel_GJ * P.GAS_KG_PER_GJ / 1e9
    ch4 = fuel_GJ * P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4 / 1e9
    fb.append(dict(eff=eff, co2=co2, ch4=ch4, add=co2 + ch4,
                   net=adv["gross"] - cred_ext + co2 + ch4, fuel_PJ=fuel_GJ / 1e6,
                   fuel_cost_lo=fuel_GJ * P.GAS_AUD_GJ[0] / 1e6, fuel_cost_hi=fuel_GJ * P.GAS_AUD_GJ[1] / 1e6))
N["backup"] = fb
N["adv_gross"] = adv["gross"]; N["adv_net_unfirmed"] = adv["gross"] - cred_ext
pk = adv["ep_peak_gw"]
N["backup_capex_bn"] = [pk * 1e6 * c / 1e9 for c in P.FIRM_CAPEX_AUD_KW]
N["backup_capcharge_m"] = [pk * 1e6 * c * P.CAP_CHARGE / 1e6 for c in P.FIRM_CAPEX_AUD_KW]
N["backup_cf"] = Eb * 1e3 / (pk * 8.76) if pk else 0
N["adv_extra_cost_m"] = (adv["hvo_cost_m"] + adv["imp_cost_m"] - adv["exp_rev_m"]) - (enl["hvo_cost_m"] + enl["imp_cost_m"] - enl["exp_rev_m"])

# ---------------- SMR economics and water
smr_gw = 2.4
N["smr_capex_bn"] = smr_gw * 1e6 * P.SMR_CAPEX_AUD_KW / 1e9
N["smr_capcharge_bn"] = N["smr_capex_bn"] * P.CAP_CHARGE
N["smr_hvo_saving_m"] = (enl["hvo_ML"] - smr["hvo_ML"]) * P.HVO_AUD_PER_L
N["smr_twh"] = smr["smr_twh"]
N["smr_cf"] = smr["smr_twh"] / (smr_gw * 8.76)
N["smr_water_wet_Mm3"] = smr["smr_twh"] * 1e6 * P.NREL_GAL_MWH["nuclear_tower"] * P.GAL_TO_M3 / 1e6
N["smr_gross_drop"] = enl["gross"] - smr["gross"]
N["smr_adv_uns"] = g("enl_smr", "combined_adverse")["unserved_twh_16y"]
N["smr_adv_peak"] = g("enl_smr", "combined_adverse")["ep_peak_gw"]

# ---------------- water
IT = P.IT_TWH
E = N["E_ext"]
w = dict(wue02=0.2 * IT, wue05=0.5 * IT,
         ccgt_dry=E * 1e6 * 2 * P.GAL_TO_M3 / 1e6, ccgt_tower=E * 1e6 * 198 * P.GAL_TO_M3 / 1e6,
         ccs_tower=E * 1e6 * 378 * P.GAL_TO_M3 / 1e6)
w["combo_05_tower"] = w["wue05"] + w["ccgt_tower"]
w["combo_02_tower"] = w["wue02"] + w["ccgt_tower"]
w["combo_05_ccs"] = w["wue05"] + w["ccs_tower"]
w["desal_Mm3"] = P.DESAL_M3 / 1e6
w["hot_hours"] = R["hours_T_gt35"]
w["adiabatic_hot_Mm3"] = sum(R["hours_T_gt35"][i] * R["IT_mw"][i] for i in range(7)) * 1e3 * 0.1 / 1e6 * 1e-3 * 1e3 / 1e3
# adiabatic assist only above 35 C at 0.1 L/kWh_IT  ->  m3 = hours*MW*1000 kWh*0.1 L / 1000
w["adiabatic_hot_Mm3"] = sum(R["hours_T_gt35"][i] * R["IT_mw"][i] * 1e3 * 0.1 / 1e3 for i in range(7)) / 1e6
N["water"] = w

# ---------------- Weddell / Beetaloo gas-rate check
gw_fuel = 200e12 / 86400 / 1e9   # GW thermal per GW compute
N["beetaloo_fuel_gw_per_gw"] = gw_fuel
N["beetaloo_eff_pue110"] = 1.10 / gw_fuel
N["beetaloo_eff_fac"] = 1.0 / gw_fuel
N["beetaloo_2gw_PJ"] = 400e12 * 365 / 1e15
N["beetaloo_2gw_co2"] = 400e3 * 365 * P.GAS_KG_PER_GJ / 1e9  # 400 TJ/d -> GJ/d =4e5
N["beetaloo_2gw_ch4"] = 400e3 * 365 * P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4 / 1e9
N["beetaloo_scale_factor"] = P.CCGT_EFF_HHV / N["beetaloo_eff_pue110"]
N["beetaloo_ext_no_ccs"] = G[("ext", 0.0)]["total"] * N["beetaloo_scale_factor"]

# ---------------- community programme & jobs & economics
food_kt = R["produce_t"] / 1e3 + R["seafood_t"] / 1e3
jobs = dict(facility=P.FTE_PER_GW_IT * P.IT_GW, food=P.FOOD_FTE_PER_KT * food_kt, kelp=P.KELP_FTE_PER_HA * R["kelp_ha"],
            asparagopsis=P.ASP_FTE_PER_HA * R["asp_ha"], water=3.0 * P.DESAL_M3 / 1e6, ers=P.ERS_FTE_PER_KM * R["ers_km"],
            drones=P.DRONE_FTE_PER_DRONE * R["drones_total"])
jobs["total"] = sum(jobs.values())
jobs["smr_extra"] = P.SMR_FTE_PER_UNIT * 8
N["jobs"] = jobs
WATER_PRICE = (1.5, 2.5, 3.5)
econ = []
for i, lab in enumerate(["low", "central", "high"]):
    produce = R["produce_t"] * 1e3 * P.PRICE_PRODUCE[i] / 1e6
    seafood = R["seafood_t"] * 1e3 * P.PRICE_SEAFOOD[i] / 1e6
    hh = heat["full"]["parts"]["residential"] * 3.6e6 * P.PRICE_HH_HEAT[i] / 1e6
    water = P.DESAL_M3 * WATER_PRICE[i] / 1e6
    final = produce + seafood + hh + water
    elec = (N["hp_full"] + N["ras"] + N["sw_e"] + N["wat_e"] + N["boost"]) * 1e6 * P.ELEC_AUD_MWH * [0.8, 1.0, 1.25][2 - i] / 1e6
    labour = (jobs["food"] + jobs["kelp"] + jobs["asparagopsis"] + jobs["water"]) * P.WAGE_FTE * [0.9, 1.0, 1.15][2 - i] / 1e6
    feed = R["feed_t"] * 1e3 * P.FEED_AUD_KG * [0.85, 1.0, 1.2][2 - i] / 1e6
    opcost = elec + labour + feed
    # selected capital charges (8%): glasshouse A$1,200/m2, RAS A$15/kg-y, heat pumps A$800/kWth at 3x mean, MED A$2,500 per m3/d
    gh_capex = R["gh_ha"] * 1e4 * 1200 / 1e6
    ras_capex = R["seafood_t"] * 1e3 * 15 / 1e6
    hp_capex = heat["full"]["delivered_twh"] * 1e6 / 8760 * 3 * 1e3 * 800 / 1e6
    med_capex = P.DESAL_M3 / 365 * 2500 / 1e6
    capchg = (gh_capex + ras_capex + hp_capex + med_capex) * P.CAP_CHARGE * [0.85, 1.0, 1.2][2 - i]
    econ.append(dict(case=lab, produce=produce, seafood=seafood, hh_heat=hh, water=water, final=final, elec=elec,
                     labour=labour, feed=feed, opcost=opcost, op_diff=final - opcost, capchg=capchg,
                     diff_with_cap=final - opcost - capchg))
N["econ"] = econ
N["capex_items_m"] = dict(glasshouse=R["gh_ha"] * 1e4 * 1200 / 1e6, ras=R["seafood_t"] * 1e3 * 15 / 1e6,
                          heat_pumps=heat["full"]["delivered_twh"] * 1e6 / 8760 * 3 * 1e3 * 800 / 1e6,
                          med=P.DESAL_M3 / 365 * 2500 / 1e6)
N["intermediate_heat_value_m"] = (heat["full"]["delivered_twh"] - heat["full"]["parts"]["residential"]) * 3.6e6 * P.PRICE_HH_HEAT[1] / 1e6
# overlays (illustrative, A$)
ov_lo = dict(ev=1000 * 45000, charge=30e6 * 0.30, fuel=5e6 * 0.60, dry=100000 * 120)
ov_hi = dict(ev=5000 * 45000, charge=150e6 * 0.30, fuel=20e6 * 0.60, dry=200000 * 120)
N["overlay_lo_m"] = {k: v / 1e6 for k, v in ov_lo.items()}; N["overlay_hi_m"] = {k: v / 1e6 for k, v in ov_hi.items()}
N["overlay_lo_tot"] = sum(ov_lo.values()) / 1e6; N["overlay_hi_tot"] = sum(ov_hi.values()) / 1e6
# electricity-system cost ledger (enlarged central)
N["fuel_trade"] = dict(hvo_cost=enl["hvo_cost_m"], imp_cost=enl["imp_cost_m"], exp_rev=enl["exp_rev_m"],
                       net=enl["hvo_cost_m"] + enl["imp_cost_m"] - enl["exp_rev_m"])
N["fuel_trade_smr"] = dict(hvo_cost=smr["hvo_cost_m"], imp_cost=smr["imp_cost_m"], exp_rev=smr["exp_rev_m"],
                           net=smr["hvo_cost_m"] + smr["imp_cost_m"] - smr["exp_rev_m"])

# ERS economics
diesel_price = 1.90
N["ers_diesel_cost_m"] = R["ers_diesel_ML"] * diesel_price
N["ers_elec_cost_m"] = N["ers"] * 1e6 * 150 / 1e6
N["ers_saving_m"] = N["ers_diesel_cost_m"] - N["ers_elec_cost_m"]
N["ers_capex_bn"] = [R["ers_km"] * c / 1e3 for c in P.ERS_CAPEX_AUD_M_PER_KM]
N["ers_capcharge_m"] = [x * 1e3 * P.CAP_CHARGE for x in N["ers_capex_bn"]]
N["ers_credit_per_twh"] = cred_ers / N["ers"]

# Seaweed
N["seaweed"] = dict(asp_t=R["asp_t"], asp_ha=R["asp_ha"], asp_head=R["asp_head"], asp_abate=R["asp_ch4_abate_mt"],
                    asp_abate_lo=R["asp_ch4_abate_mt"] * 0.3 / 0.5, asp_abate_hi=R["asp_ch4_abate_mt"] * 0.8 / 0.5,
                    kelp_t=R["kelp_t"], kelp_ha=R["kelp_ha"], kelp_wet=R["kelp_wet_t"], kelp_co2_kt=R["kelp_co2_kt"],
                    kelp_N_t=R["kelp_N_t"], kelp_t_hi=R["kelp_ha"] * 6.2806, kelp_t_lo=R["kelp_ha"] * 3.1403,
                    dry_heat_twh=heat["full"]["parts"]["seaweed"], elec_gwh=N["sw_e"] * 1e3)

# Drones
N["drones"] = dict(parcels=R["parcels"], deliv=R["deliv_drones"], total=R["drones_total"], gwh=N["drone"] * 1e3,
                   credit_t=R["drone_credit_mt"] * 1e6, van_L=R["van_L"])

# fibre latency between hubs
def gc(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    d = 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    return d
pts = [(h["lat"], h["lon"]) for h in P.HUBS] + [(P.WEDDELL["lat"], P.WEDDELL["lon"])]
names = P.HUB_KEYS + ["WED"]
lat = {}
for i in range(len(pts)):
    for j in range(i + 1, len(pts)):
        d = gc(pts[i], pts[j])
        lat[f"{names[i]}-{names[j]}"] = dict(km=d, route_km=d * 1.3, rtt_ms=2 * d * 1.3 * 5e-3)
N["latency"] = lat
N["max_rtt_nem"] = max(v["rtt_ms"] for k, v in lat.items() if "COL" not in k and "WED" not in k)
N["rtt_col_mus"] = lat["MUS-COL"]["rtt_ms"]

# misc
N["pue_mean"] = R["pue_mean"]; N["pue_hub"] = R["pue_hub"]; N["pue_max"] = R["pue_max"]
N["wind_cf"] = R["wind_cf"]; N["pv_cf"] = R["pv_cf"]; N["wind_cf_year_min"] = R["wind_cf_year_min"]; N["wind_cf_year_max"] = R["wind_cf_year_max"]
N["pv_cf_year_min"] = R["pv_cf_year_min"]; N["pv_cf_year_max"] = R["pv_cf_year_max"]
N["portfolio_totals"] = {pf: {k: v * 7 for k, v in d.items() if k in ("wind", "solar", "batt", "hvo", "imp", "exp")} for pf, d in P.PORTFOLIOS.items()}
N["enl"] = {k: enl[k] for k in ["wind_twh", "pv_twh", "exp_twh", "curt_twh", "imp_twh", "hvo_twh", "hvo_ML", "batt_dis_twh", "moved_twh", "hvo_ML_max_year", "load_twh"]}
N["smr"] = {k: smr[k] for k in ["wind_twh", "pv_twh", "smr_twh", "exp_twh", "curt_twh", "imp_twh", "hvo_twh", "hvo_ML", "load_twh"]}
N["food"] = dict(produce_t=R["produce_t"], seafood_t=R["seafood_t"], gh_ha=R["gh_ha"], feed_t=R["feed_t"])
N["ers_rows"] = R["ers"]; N["ers_km"] = R["ers_km"]; N["ers_diesel_ML"] = R["ers_diesel_ML"]
N["T_mean"] = R["T_mean"]; N["T_max"] = R["T_max"]; N["hours_T_gt35"] = R["hours_T_gt35"]
N["smr_avail"] = R["smr_avail"]; N["price_mean"] = R["price_mean"]; N["wind_corr"] = R["wind_corr"]
# Weddell-climate comparator: equal IT service at Weddell PUE, ambient-derated CCGT
Wd = R.get("weddell")
if Wd is None:   # synthetic run: no Weddell weather
    Wd = dict(fac_twh_itequal=N["E_fac"], ccgt_eff_mean=P.CCGT_EFF_HHV)
N["weddell"] = Wd
E_itq = N["E_ext"] - N["E_fac"] + Wd["fac_twh_itequal"]
fuel = E_itq * 3.6e6 / Wd["ccgt_eff_mean"]
co2 = fuel * P.GAS_KG_PER_GJ / 1e9; ch4 = fuel * P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4 / 1e9
fuel95 = fuel * 1.15
N["wed_clim"] = dict(E=E_itq, eff=Wd["ccgt_eff_mean"], total0=co2 + ch4,
                     total95=fuel95 * (P.GAS_KG_PER_GJ * 0.05 + P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4) / 1e9,
                     total90=fuel95 * (P.GAS_KG_PER_GJ * 0.10 + P.CH4_KG_PER_GJ * P.LEAK / (1 - P.LEAK) * P.GWP_CH4) / 1e9)
N["wed_clim"]["net95"] = N["wed_clim"]["total95"] - cred_ext
N["wed_clim"]["net0"] = N["wed_clim"]["total0"] - cred_ext
N["wed_clim"]["net90"] = N["wed_clim"]["total90"] - cred_ext
N["wind_mode"] = R.get("wind_mode"); N["wind_cf_raw"] = R.get("wind_cf_raw"); N["wind_c"] = R.get("wind_c"); N["year0"] = R.get("year0")
json.dump(N, open(os.path.join(HERE, f"dga_numbers_{MODE}.json"), "w"), indent=1, default=float)

# print summary
pr = lambda *a: print(*a)
pr("E fac/core/ext", round(N["E_fac"], 3), round(N["E_core"], 3), round(N["E_ext"], 3))
for r in gt: pr(r["basis"], r["capture"], round(r["E"], 3), round(r["fuel_twh"], 3), round(r["co2"], 3), round(r["ch4"], 3), round(r["total"], 3))
pr("credits heat/ers/drone/ext", round(cred_heat, 4), round(cred_ers, 4), round(cred_drone, 5), round(cred_ext, 4))
for r in sym + symc: pr(r["label"], round(r["gross"], 3), round(r["credit"], 3), round(r["net"], 3))
pr("ratios", N["ratio_unabated_ext"], N["ratio_95_ext"], N["ratio_unabated_core"], N["ratio_95_core"], "gaps", N["gap95_ext"], N["gap95_core"], N["gap90_ext"])
pr("leak cross", N["leak_cross_pct"], N["leak_rows"])
pr("sens", N["sens_pv"], N["sens_hvo"], N["sens_imp"])
pr("thermal", th, "util", N["heat_util_share"], "src", src_extract)
for r in hcs: pr(r)
pr("backup", fb, N["backup_capex_bn"], N["backup_capcharge_m"], N["backup_cf"], N["adv_extra_cost_m"])
pr("smr", N["smr_capex_bn"], N["smr_capcharge_bn"], N["smr_hvo_saving_m"], N["smr_cf"], N["smr_water_wet_Mm3"], N["smr_gross_drop"], N["smr_adv_uns"])
pr("water", w)
pr("beetaloo", N["beetaloo_fuel_gw_per_gw"], N["beetaloo_eff_pue110"], N["beetaloo_eff_fac"], N["beetaloo_2gw_PJ"], N["beetaloo_2gw_co2"], N["beetaloo_2gw_ch4"], N["beetaloo_ext_no_ccs"])
pr("jobs", jobs)
for e in econ: pr({k: (round(v, 1) if isinstance(v, float) else v) for k, v in e.items()})
pr("capex", N["capex_items_m"], "interm heat", N["intermediate_heat_value_m"])
pr("fuel trade", N["fuel_trade"], N["fuel_trade_smr"])
pr("ers", N["ers_diesel_cost_m"], N["ers_elec_cost_m"], N["ers_saving_m"], N["ers_capex_bn"], N["ers_capcharge_m"])
pr("seaweed", N["seaweed"]); pr("drones", N["drones"])
pr("lat", N["max_rtt_nem"], N["rtt_col_mus"], lat["MUS-WED"])
pr("overlay", N["overlay_lo_tot"], N["overlay_hi_tot"])
