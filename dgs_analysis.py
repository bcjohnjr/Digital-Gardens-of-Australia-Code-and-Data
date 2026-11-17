"""Derive every manuscript number for Digital Gardens Sunraysia. Run: python dgs_analysis.py [rez|palmer|raw]"""
import os, sys, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dgs_params as P

MODE = sys.argv[1] if len(sys.argv) > 1 else "rez"
R = json.load(open(os.path.join(HERE, f"dgs_results_{MODE}.json")))
S = {(s["it_mw"], s["portfolio"], s["scenario"]): s for s in R["scenarios"]}
IT = P.IT_MW
cen = S[(IT, "balanced", "central")]
adv = S[(IT, "balanced", "combined_adverse")]
N = dict(mode=MODE, proxy=R["proxy"], weather_source=R["weather_source"], it_mw=IT, pop=P.POP)

# ---------------------------------------------------------------- energy services
N["E_it"] = R["it_twh"]; N["E_fac"] = R["fac_twh"]
N["E_core"] = R["fac_twh"] + R["comm_core_twh"]; N["E_ext"] = R["fac_twh"] + R["comm_ext_twh"]
N["comm"] = dict(led=R["led_twh"], ras=R["ras_twh"], boost=R["boost_twh"], hp=R["hp_twh"], ev=R["ev_twh"],
                 core=R["comm_core_twh"], ext=R["comm_ext_twh"])
cred = R["heat_credit_mt"]
N["credit"] = cred


# ---------------------------------------------------------------- gas campus near Mildura (equal service)
def gas(E, capture=0.0, leak=P.LEAK, gwp=P.GWP_CH4):
    pen = P.CCS_PENALTY if capture > 0 else 0.0
    fuel = E * 3.6e6 / P.CCGT_EFF_HHV * (1 + pen)
    co2 = fuel * P.GAS_KG_PER_GJ * (1 - capture) / 1e9
    ch4 = fuel * P.CH4_KG_PER_GJ * leak / (1 - leak) * gwp / 1e9
    return dict(fuel_PJ=fuel / 1e6, co2=co2, ch4=ch4, total=co2 + ch4)


N["gas"] = {lab: {str(c): gas(E, c) for c in (0.0, 0.9, 0.95)} for lab, E in (("fac", N["E_fac"]), ("ext", N["E_ext"]))}

# ---------------------------------------------------------------- metropolitan grid-supplied campuses (equal IT)
metro = {}
for m in P.METRO:
    k = m["key"]; f = P.GRID_T_PER_MWH[m["state"]]
    E_fac_m = N["E_it"] * R["metro"][k]["pue_mean"]
    metro[k] = dict(name=m["name"], state=m["state"], factor=f, pue=R["metro"][k]["pue_mean"], E_fac=E_fac_m,
                    fac_mt=E_fac_m * f, ext_mt=E_fac_m * f + R["comm_ext_twh"] * P.GRID_T_PER_MWH["VIC"],
                    T_max=R["metro"][k]["T_max"], hours_gt35=R["metro"][k]["hours_gt35"])
N["metro"] = metro

# ---------------------------------------------------------------- symmetric ledger (extended service, equal heat credit)
itonly = S[(IT, "balanced", "load_it_only")]
rows = [("DGS balanced portfolio", cen["gross"]),
        ("DGS solar + grid portfolio", S[(IT, "solar_grid", "central")]["gross"]),
        ("DGS high-renewable portfolio", S[(IT, "high_re", "central")]["gross"]),
        ("Metropolitan campus, western Sydney (NSW grid)", metro["EAC"]["ext_mt"]),
        ("Metropolitan campus, western Melbourne (VIC grid)", metro["LAV"]["ext_mt"]),
        ("Gas campus near Mildura, no capture", N["gas"]["ext"]["0.0"]["total"]),
        ("Gas campus near Mildura, 90% capture", N["gas"]["ext"]["0.9"]["total"]),
        ("Gas campus near Mildura, 95% capture", N["gas"]["ext"]["0.95"]["total"])]
N["ledger"] = [dict(label=l, gross=g, credit=cred, net=g - cred) for l, g in rows]
L = {r["label"]: r for r in N["ledger"]}
dg = L["DGS balanced portfolio"]["net"]
N["ratio_vs"] = {r["label"]: dg / r["net"] for r in N["ledger"] if r["net"] > 0}
N["fac_basis"] = dict(dgs=itonly["gross"], eac=metro["EAC"]["fac_mt"], lav=metro["LAV"]["fac_mt"],
                      gas0=N["gas"]["fac"]["0.0"]["total"], gas95=N["gas"]["fac"]["0.95"]["total"])
N["intensity_g_kwh"] = dict(dgs=cen["gross"] * 1e12 / (cen["load_twh"] * 1e9),
                            dgs_fac=itonly["gross"] * 1e9 / (itonly["load_twh"] * 1e9) * 1e3)

# leakage at which 95% capture gas equals DGS (extended)
g95 = N["gas"]["ext"]["0.95"]
lo, hi = 0.0, 20.0
for _ in range(80):
    mid = 0.5 * (lo + hi)
    if gas(N["E_ext"], 0.95, leak=mid / 100)["total"] < cen["gross"]:
        lo = mid
    else:
        hi = mid
N["leak_cross_pct"] = mid

# ---------------------------------------------------------------- sensitivities (balanced central)
def dg_with(grid=None, pv=None, eng_g=None):
    c = {k: cen[k] for k in ("c_wind", "c_pv", "c_batt", "c_imp", "c_eng")}
    if grid is not None:
        c["c_imp"] = cen["imp_twh"] * grid
    if pv is not None:
        c["c_pv"] = cen["c_pv"] * pv / P.PV_G_KWH
    if eng_g is not None:
        c["c_eng"] = (cen["bd_ML"] * 1e6 * P.BD_MJ_PER_L + cen["bg_engine_PJ"] * 1e9) * eng_g / 1e12
    return sum(c.values())


N["sens_grid"] = {str(v): dict(dgs=dg_with(grid=v), dgs_net=dg_with(grid=v) - cred,
                               eac=metro["EAC"]["E_fac"] * v + R["comm_ext_twh"] * v - cred) for v in P.GRID_SENS}
N["sens_pv"] = {str(v): dg_with(pv=v) for v in (12, 37, 48)}
N["sens_eng"] = {str(v): dg_with(eng_g=v) for v in (10, 20, 74)}
N["dg_parts"] = {k: cen[k] for k in ("c_wind", "c_pv", "c_batt", "c_imp", "c_eng", "gross")}

# ---------------------------------------------------------------- portfolios, stresses, IT scale
N["portfolio_rows"] = []
for pf in P.PORTFOLIOS:
    for sc in ("central", "wind_minus10", "pv_minus10", "import_half", "outages_x2", "combined_adverse"):
        s = S[(IT, pf, sc)]
        N["portfolio_rows"].append({k: s[k] for k in ("portfolio", "scenario", "solar_mw", "wind_mw", "batt_mw", "batt_mwh", "load_twh", "imp_twh", "exp_twh",
                                                       "curt_twh", "eng_gwh", "bd_ML", "bd_ML_max_year", "unserved_mwh_16y", "ep_peak_mw", "ep_hours",
                                                       "gross", "renewable_share", "engine_mw", "imp_cost_m", "exp_rev_m", "eng_fuel_cost_m", "unserved_share")})
N["nodal_rows"] = []
for s_ in R["scenarios"]:
    if "_campus" in s_["scenario"]:
        base = S[(IT, s_["portfolio"], s_["scenario"].split("_campus")[0])]
        N["nodal_rows"].append(dict(portfolio=s_["portfolio"], scenario=s_["scenario"], base=base["scenario"],
                                    limit_pct=int(s_["scenario"].split("_campus")[1]), imp=s_["imp_twh"], exp=s_["exp_twh"], curt=s_["curt_twh"],
                                    eng=s_["eng_gwh"], bd=s_["bd_ML"], uns=s_["unserved_mwh_16y"], uns_share=s_["unserved_share"],
                                    re=s_["renewable_share"], gross=s_["gross"], net=s_["gross"] - cred, base_gross=base["gross"],
                                    base_imp=base["imp_twh"], lim_hours=s_["campus_limit_hours_y"], moved=s_["moved_gwh"]))
N["it_rows"] = []
for it in P.IT_SCENARIOS:
    for sc in ("central", "combined_adverse"):
        s = S[(it, "balanced", sc)]
        N["it_rows"].append(dict(it=it, scenario=sc, kw_per_res=it * 1e3 / P.POP, load=s["load_twh"], imp=s["imp_twh"], exp=s["exp_twh"],
                                 re=s["renewable_share"], uns=s["unserved_mwh_16y"], uns_share=s["unserved_share"], peak=s["ep_peak_mw"],
                                 eng=s["eng_gwh"], bd=s["bd_ML"], gross=s["gross"], solar=s["solar_mw"], wind=s["wind_mw"],
                                 batt=s["batt_mw"], g_kwh=s["gross"] * 1e3 / s["load_twh"]))
N["cen"] = {k: v for k, v in cen.items() if not isinstance(v, (list, dict))}
N["adv"] = {k: v for k, v in adv.items() if not isinstance(v, (list, dict))}

# ---------------------------------------------------------------- named Australian projects: location-based screen
named = []
for name, op, loc, st, mw, basis, status, src in P.NAMED_PROJECTS:
    E = mw * P.PUE_WEBSITE * P.HPY / 1e6
    named.append(dict(name=name, operator=op, location=loc, state=st, mw=mw, basis=basis, status=status, src=src,
                      twh=E, mt_loc=E * P.GRID_T_PER_MWH[st], x_dgs=mw / IT,
                      mt_at_dgs_intensity=E * N["intensity_g_kwh"]["dgs_fac"] / 1e3))
N["named"] = named
N["named_total_mw"] = sum(x["mw"] for x in named)
N["named_total_mt"] = sum(x["mt_loc"] for x in named)
N["dgs_web_twh"] = IT * P.PUE_WEBSITE * P.HPY / 1e6

# ---------------------------------------------------------------- heat
N["heat"] = dict(demand=R["heat_demand_twh"], delivered=R["heat"]["full"]["delivered_twh"], hp=R["heat"]["full"]["hp_twh"],
                 parts=R["heat_parts"], reject=N["E_fac"], share=R["heat"]["full"]["delivered_twh"] / N["E_fac"],
                 credit=cred, credit_gas=R["heat_credit_gas_mt"], credit_el=R["heat_credit_el_mt"], hdd=R["hdd"])

# ---------------------------------------------------------------- water (m3/y)
hot_h = R["hours_gt35"]
dgs_adiab = sum(hot_h[i] * IT * P.CAMPUSES[i]["share"] * 1e3 * P.ADIABATIC_L_PER_KWH_IT / 1e3 for i in range(P.NC))
N["water"] = dict(dgs_adiabatic_m3=dgs_adiab, hours_gt35=hot_h,
                  metro_lo_m3=N["E_it"] * 1e9 * P.METRO_WUE_L_PER_KWH[0] / 1e3, metro_hi_m3=N["E_it"] * 1e9 * P.METRO_WUE_L_PER_KWH[1] / 1e3,
                  ccgt_tower_m3=N["E_ext"] * 1e6 * 198 * 0.003785411784, ccgt_dry_m3=N["E_ext"] * 1e6 * 2 * 0.003785411784)

# ---------------------------------------------------------------- food, biogas, vehicles, jobs, economics
N["food"] = dict(produce_t=R["produce_t"], seafood_t=R["seafood_t"], gh_ha=R["gh_ha"], feed_t=R["feed_t"],
                 species={k: R["seafood_t"] * v for k, v in P.SEAFOOD_MIX.items()}, led_on_hours=R["led_on_hours"],
                 ras_N_t=R["ras_N_excreted_t"], drying_t=P.DRYING_T)
N["biogas"] = dict(pj=R["biogas_pj"], src=R["biogas_src_pj"], marc_t=R["marc_t"], engine_pj=cen["bg_engine_PJ"],
                   surplus_pj=cen["bg_surplus_PJ"], share_engine=cen["bg_share_engine"],
                   surplus_diesel_eq_ML=cen["bg_surplus_PJ"] * 1e9 / 38.6e6)
N["vehicles"] = dict(n_hh=R["n_hh"], n_veh=R["n_veh"], ev_gwh=R["ev_gwh"], phev_fuel_ML=R["phev_fuel_ML"], hh_connected=R["hh_connected"])
pet_L = R["n_veh"] * P.VEH_KM_Y * (P.VEH_EV_SHARE * P.PETROL_L_100KM_DISPLACED / 100
                                   + (1 - P.VEH_EV_SHARE) * (P.PETROL_L_100KM_DISPLACED - P.PHEV_E_SHARE * P.PHEV_L_100KM) / 100)
N["vehicles"].update(petrol_avoided_ML=pet_L / 1e6, petrol_avoided_mt=pet_L * P.PETROL_KG_PER_L / 1e9)
food_kt = (R["produce_t"] + R["seafood_t"]) / 1e3
jobs = dict(campuses=P.FTE_PER_MW_IT * IT, food=P.FOOD_FTE_PER_KT * food_kt, drying=P.DRY_FTE)
jobs["total"] = sum(jobs.values())
N["jobs"] = jobs
econ = []
for i, lab in enumerate(("low", "central", "high")):
    produce = R["produce_t"] * 1e3 * P.PRICE_PRODUCE[i] / 1e6
    seafood = R["seafood_t"] * 1e3 * P.PRICE_SEAFOOD[i] / 1e6
    hh = R["heat_parts"]["residential"] * 3.6e6 * P.PRICE_HH_HEAT[i] / 1e6
    final = produce + seafood + hh
    m = [0.8, 1.0, 1.25][2 - i]
    elec = (R["hp_twh"] + R["ras_twh"] + R["led_twh"] + R["boost_twh"]) * 1e6 * P.ELEC_AUD_MWH * m / 1e6
    labour = (jobs["food"] + jobs["drying"]) * P.WAGE_FTE * [0.9, 1.0, 1.15][2 - i] / 1e6
    feed = R["feed_t"] * 1e3 * P.FEED_AUD_KG * [0.85, 1.0, 1.2][2 - i] / 1e6
    gh_capex = R["gh_ha"] * 1e4 * 1200 / 1e6
    ras_capex = R["seafood_t"] * 1e3 * 15 / 1e6
    hp_capex = R["heat"]["full"]["delivered_twh"] * 1e6 / 8760 * 3 * 1e3 * 800 / 1e6
    led_capex = R["gh_ha"] * 1e4 * P.LED_W_M2 * 1.5 / 1e6
    capchg = (gh_capex + ras_capex + hp_capex + led_capex) * P.CAP_CHARGE * [0.85, 1.0, 1.2][2 - i]
    opcost = elec + labour + feed
    econ.append(dict(case=lab, produce=produce, seafood=seafood, hh_heat=hh, final=final, elec=elec, labour=labour, feed=feed,
                     opcost=opcost, capchg=capchg, net=final - opcost - capchg))
N["econ"] = econ
N["capex_m"] = dict(glasshouse=R["gh_ha"] * 1e4 * 1200 / 1e6, ras=R["seafood_t"] * 1e3 * 15 / 1e6,
                    heat_pumps=R["heat"]["full"]["delivered_twh"] * 1e6 / 8760 * 3 * 1e3 * 800 / 1e6, led=R["gh_ha"] * 1e4 * P.LED_W_M2 * 1.5 / 1e6)
N["elec_ledger"] = dict(imp_cost=cen["imp_cost_m"], exp_rev=cen["exp_rev_m"], eng_fuel=cen["eng_fuel_cost_m"],
                        net=cen["imp_cost_m"] + cen["eng_fuel_cost_m"] - cen["exp_rev_m"])


# ---------------------------------------------------------------- fibre latency between campuses
def gc(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


lat = {}
for i in range(P.NC):
    for j in range(i + 1, P.NC):
        d = gc(P.CAMPUSES[i], P.CAMPUSES[j])
        lat[f"{P.CKEYS[i]}-{P.CKEYS[j]}"] = dict(km=d, route_km=d * P.ROUTE_FACTOR, rtt_ms=2 * d * P.ROUTE_FACTOR * P.FIBRE_US_PER_KM / 1e3)
N["latency"] = lat
N["max_rtt_ms"] = max(v["rtt_ms"] for v in lat.values())
N["max_route_km"] = max(v["route_km"] for v in lat.values())
N["eac_rtt_ms"] = 2 * gc(P.CAMPUSES[0], P.METRO[0]) * P.ROUTE_FACTOR * P.FIBRE_US_PER_KM / 1e3

# ---------------------------------------------------------------- weather summary
for k in ("pue_mean", "pue_campus", "pue_max", "T_mean", "T_max", "hours_gt35", "pv_cf", "pv_cf_campus", "wind_cf", "wind_cf_zone",
          "wind_cf_raw", "wind_c", "wind_pv_corr", "wind_cf_year", "pv_cf_year", "regional_events", "import_avail_mean", "year0"):
    N[k] = R[k]
N["campus"] = R["campus"]
json.dump(N, open(os.path.join(HERE, f"dgs_numbers_{MODE}.json"), "w"), indent=1, default=float)

print(f"[{MODE}] E it/fac/core/ext {N['E_it']:.3f} {N['E_fac']:.3f} {N['E_core']:.3f} {N['E_ext']:.3f}  credit {cred:.4f}")
for r in N["ledger"]:
    print(f"  {r['label']:52s} gross {r['gross']:.3f} net {r['net']:.3f}")
print("  facility basis", {k: round(v, 3) for k, v in N["fac_basis"].items()}, "intensity", N["intensity_g_kwh"])
print("  leak cross %", round(N["leak_cross_pct"], 2), "grid sens", {k: round(v["dgs_net"], 3) for k, v in N["sens_grid"].items()})
print("  named total MW", N["named_total_mw"], "Mt", round(N["named_total_mt"], 2))
print("  heat", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in N["heat"].items() if k != "parts"}, N["heat"]["parts"])
print("  water", {k: v for k, v in N["water"].items() if k != "hours_gt35"})
print("  biogas", N["biogas"]); print("  vehicles", N["vehicles"]); print("  jobs", jobs)
for e in econ:
    print("  econ", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in e.items()})
print("  latency max rtt ms", round(N["max_rtt_ms"], 3), "Mildura-Eastern Creek rtt", round(N["eac_rtt_ms"], 2))
