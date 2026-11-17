"""Digital Gardens Sunraysia: hourly dispatch (ERA5, 2010-2025) and ledgers for the six-campus network.

Run: python dgs_model.py [rez|palmer|raw]      (all files in this one folder)

The network is balanced as one node behind a fixed firm import right: wind (South West REZ contracts),
solar (at the campuses), four-hour batteries, grid imports and exports. Standby dual-fuel engines run only
when imports cannot cover a deficit (regional network contingencies) or when a campus loses its supply
(campus outages); 15% of IT load can migrate between campuses over the scale-across fabric.
"""
import os, sys, json, math, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dgs_params as P

MODE = sys.argv[1] if len(sys.argv) > 1 else "rez"
assert MODE in ("rez", "palmer", "raw"), MODE
rng = np.random.default_rng(P.SEED)
WF = os.path.join(HERE, "dgs_weather.npz")
if not os.path.exists(WF):
    sys.exit("dgs_weather.npz not found: run  python dgs_weather.py  first")
EW = np.load(WF)
PROXY = bool(EW["proxy"])
NH, C, Y = P.NH, P.NC, P.YEARS
SI = {k: i for i, k in enumerate(P.SITE_KEYS)}
cidx = [SI[k] for k in P.CKEYS]
month0 = EW["month0"]; doy = EW["doy"] - 1; hour_utc = EW["hour_utc"].astype(float)
HRL = (hour_utc + 10.0) % 24.0                        # Victorian local standard time (start of hour)
shares = np.array([c["share"] for c in P.CAMPUSES])
T = EW["T"][cidx].astype(float)                       # (C, NH)

# ------------------------------------------------------------------ solar PV: single-axis tracker at each campus
B = 2 * np.pi * (doy - 81) / 364.0
eot = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)
dec = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy + 1) / 365.0)


def pv_series(i, lat, lon):
    phi = math.radians(lat)
    st = hour_utc - 0.5 + lon / 15.0 + eot / 60.0
    om = np.radians(15.0 * (st - 12.0))
    sz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(om)
    sx = -np.cos(dec) * np.sin(om)
    up = sz > 0.01
    rot = np.clip(np.arctan2(sx, np.maximum(sz, 1e-6)), -np.radians(60), np.radians(60))
    cos_inc = np.clip(np.sin(rot) * sx + np.cos(rot) * sz, 0, None)
    ghi, dni, dhi = (EW[k][i].astype(float) for k in ("ghi", "dni", "dhi"))
    poa = np.where(up, dni * cos_inc + dhi * (1 + np.cos(rot)) / 2 + 0.2 * ghi * (1 - np.cos(rot)) / 2, 0.0)
    tcell = EW["T"][i].astype(float) + poa * 0.03
    dc = np.clip(poa / 1000.0 * (1 - 0.0035 * (tcell - 25.0)), 0, None) * P.PV_DC_AC * (1 - P.PV_LOSS)
    return np.minimum(dc, 1.0) * 0.99


PVc = np.stack([pv_series(SI[c["key"]], c["lat"], c["lon"]) for c in P.CAMPUSES])   # (C, NH) per MW_ac
PV = (PVc * shares[:, None]).sum(0)                                                 # network-average profile


# ------------------------------------------------------------------ wind: South West REZ zones, 100 m -> 130 m
def curve(v):
    p = np.where(v < 3.0, 0.0, np.where(v < 11.5, (v ** 3 - 27.0) / (11.5 ** 3 - 27.0), 1.0))
    return np.where(v >= 25.0, 0.0, p) * 0.90


Wz, wind_c, wind_cf_raw = [], [], []
for wz in P.WIND_ZONES:
    i = SI[wz["key"]]
    rho = EW["ps"][i].astype(float) * 100.0 / (287.05 * (EW["T"][i].astype(float) + 273.15))
    v = EW["ws100"][i].astype(float) * (P.HUB_HEIGHT_M / 100.0) ** P.SHEAR_ALPHA * (rho / 1.225) ** (1 / 3)
    raw = float(curve(v).mean()); wind_cf_raw.append(raw)
    if MODE == "raw":
        c = 1.0
    else:
        target = P.WIND_TARGET_CF if MODE == "rez" else min(raw / (1 - P.ERA5_CF_BIAS), 0.60)
        lo, hi = 0.5, 4.0
        for _ in range(60):
            c = 0.5 * (lo + hi)
            lo, hi = (c, hi) if curve(c * v).mean() < target else (lo, c)
    Wz.append(curve(c * v)); wind_c.append(float(c))
W = np.mean(Wz, axis=0)                                                              # 50:50 contract split

# ------------------------------------------------------------------ grid availability and prices (synthetic, seeded)
aimp = np.ones(NH); aexp = np.ones(NH)
n_reg = rng.poisson(P.REGIONAL_EVENTS_PER_Y * Y)
for _ in range(n_reg):
    s = rng.integers(0, NH); d = rng.integers(12, 73)
    aimp[s:s + d] = P.REGIONAL_IMPORT_AVAIL; aexp[s:s + d] = P.REGIONAL_IMPORT_AVAIL
aexp = np.minimum(aexp, 1.0 - 0.45 * PV)                                            # midday export congestion
OUT = np.zeros((C, NH), dtype=bool)                                                  # campus islanded
OUT2 = np.zeros((C, NH), dtype=bool)                                                 # extra events for 'outages x2'
for k in range(C):
    for arr in (OUT, OUT2):
        for _ in range(rng.poisson(P.CAMPUS_OUTAGES_PER_Y * Y)):
            s = rng.integers(0, NH); arr[k, s:s + rng.integers(1, 13)] = True
OUT2 = OUT | OUT2
peak = 45.0 * np.exp(-0.5 * ((HRL - 18.5) / 1.6) ** 2)
price = np.clip(95.0 + peak - 80.0 * PV - 45.0 * (W - W.mean()) + 14.0 * rng.standard_normal(NH)
                + ((rng.random(NH) < 0.0025) & (W < np.quantile(W, 0.3))) * rng.pareto(1.6, NH) * 400.0, -40.0, 5000.0)

# ------------------------------------------------------------------ IT and cooling
pue = P.PUE_BASE + P.PUE_COOL_A + P.PUE_COOL_SLOPE * np.clip(T - 18.0, 0, None) + P.PUE_TRIM_SLOPE * np.clip(T - 32.0, 0, None)

# ------------------------------------------------------------------ community programme (population-based, independent of IT size)
N_c = P.POP * shares
produce_kg = N_c * P.PRODUCE_KG
seafood_kg = N_c * P.SEAFOOD_KG
gh_m2 = produce_kg / P.GH_YIELD
hdd = np.clip(18.0 - T, 0, None) / 24.0
D_gh = gh_m2[:, None] * P.GH_HEAT_KWH_M2_PER_HDD * hdd / 1e3
D_ras = seafood_kg[:, None] * P.RAS_HEAT_KWH_PER_KG_PER_K * np.clip(P.RAS_SET_T - T, 0, None) / P.HPY / 1e3
hh_c = N_c / P.HH_SIZE * P.HH_CONNECT
D_res = hh_c[:, None] * (P.DHW_MWH_HH / P.HPY + P.SPACE_KWH_HH_PER_HDD * hdd / 1e3)
season = np.isin(month0 + 1, P.DRYING_SEASON).astype(float); season /= season.mean()
dry_c = P.DRYING_T * shares
D_dry_tot = dry_c[:, None] * P.DRYING_MWH_T / P.HPY * season[None, :]
D_dry = D_dry_tot * (1 - P.DRYER_BOOSTER_SHARE)
BOOST = D_dry_tot * P.DRYER_BOOSTER_SHARE
# LED supplementary lighting, May-Aug, 06-18 local, dull hours
ghi_c = EW["ghi"][cidx].astype(float)
led_on = np.isin(month0 + 1, (5, 6, 7, 8))[None, :] & (HRL[None, :] >= 6) & (HRL[None, :] < 18) & (ghi_c < P.LED_GHI_THRESHOLD)
LED = gh_m2[:, None] * P.LED_W_M2 / 1e6 * led_on
RAS_E = (seafood_kg * P.RAS_KWH_PER_KG / 1e3 / P.HPY)[:, None] * np.ones(NH)

# digesters (m3 CH4 per year, network) and their heat
marc_t = P.CRUSH_T * P.MARC_SHARE * P.MARC_CAPTURE
bg_src = {"grape_marc": marc_t * 1e3 * P.MARC_VS * P.MARC_B0,
          "rejected_produce": P.REJECT_T * 1e3 * P.REJECT_VS * P.REJECT_B0,
          "food_garden_organics": P.POP * P.FOGO_T_PER_RESIDENT * 1e3 * P.FOGO_VS * P.FOGO_B0,
          "glasshouse_residue": produce_kg.sum() * P.GH_RESIDUE_T_PER_T * P.GH_RESIDUE_VS * P.GH_RESIDUE_B0,
          "ras_sludge": seafood_kg.sum() * P.FCR * P.RAS_SLUDGE_DM_PER_FEED * P.RAS_SLUDGE_VS * P.RAS_SLUDGE_B0,
          "fish_offal": seafood_kg.sum() * P.FISH_OFFAL_SHARE * P.FISH_OFFAL_VS * P.FISH_OFFAL_B0}
bg_m3 = sum(bg_src.values())
BIOGAS_PJ = bg_m3 * P.CH4_MJ_PER_M3 / 1e9
BG_MWH_H = bg_m3 * P.CH4_MJ_PER_M3 / 3600.0 / P.HPY                                 # fuel MWh per hour, network
D_dig = (bg_m3 * P.DIGESTER_KWH_TH_PER_M3_CH4 / 1e3 / P.HPY * shares)[:, None] * np.ones(NH)

D_parts = {"residential": D_res, "greenhouse": D_gh, "aquaculture": D_ras, "drying": D_dry, "digester": D_dig}
D_tot = sum(D_parts.values())

# vehicles and charging
n_hh = P.POP / P.HH_SIZE
n_veh = n_hh * P.VEH_PER_HH
ev_gwh = n_veh * P.VEH_KM_Y * (P.VEH_EV_SHARE * P.EV_KWH_KM + (1 - P.VEH_EV_SHARE) * P.PHEV_E_SHARE * P.PHEV_KWH_KM) / (1 - P.CHARGE_LOSS) / 1e6
phev_fuel_ML = n_veh * (1 - P.VEH_EV_SHARE) * P.VEH_KM_Y * (1 - P.PHEV_E_SHARE) * P.PHEV_L_100KM / 100 / 1e6
ev_prof = 0.4 + np.exp(-0.5 * ((HRL - 12) / 3) ** 2) * 1.6; ev_prof /= ev_prof.mean()
EV = (ev_gwh * 1e3 * shares / P.HPY)[:, None] * ev_prof[None, :]


def heat_case(frac):
    deliv = frac * D_tot
    return deliv, deliv / ((1 - P.HEAT_LOSS) * P.HP_COP)


HC = {"full": heat_case(1.0), "half": heat_case(0.5), "none": heat_case(0.0)}
COMM = {"full_ext": BOOST + LED + RAS_E + HC["full"][1] + EV,
        "core": BOOST + LED + RAS_E + HC["full"][1],
        "half_heat": BOOST + LED + RAS_E + HC["half"][1] + EV,
        "it_only": np.zeros((C, NH))}

# ------------------------------------------------------------------ scenarios
STRESS = {"central": {}, "wind_minus10": {"wind_scale": 0.9}, "pv_minus10": {"pv_scale": 0.9},
          "import_half": {"imp_scale": 0.5}, "outages_x2": {"outages": 2},
          "combined_adverse": {"wind_scale": 0.9, "imp_scale": 0.5, "outages": 2}}
scen = []
for pf in P.PORTFOLIOS:
    for nm, kw in STRESS.items():
        scen.append(dict(it=P.IT_MW, pf=pf, name=nm, load="full_ext", trace=(pf == "balanced" and nm in ("central", "combined_adverse")), **kw))
for it in P.IT_SCENARIOS:
    if it == P.IT_MW:
        continue
    for nm in ("central", "combined_adverse"):
        scen.append(dict(it=it, pf="balanced", name=nm, load="full_ext", **STRESS[nm]))
for ld in ("core", "half_heat", "it_only"):
    scen.append(dict(it=P.IT_MW, pf="balanced", name=f"load_{ld}", load=ld))
S = len(scen)

ITs = np.array([s["it"] for s in scen])
scale = ITs / P.IT_MW
cap = {k: np.array([P.PORTFOLIOS[s["pf"]][k] for s in scen]) * scale for k in ("solar", "wind", "batt_mw")}
wsc = np.array([s.get("wind_scale", 1.0) for s in scen]); psc = np.array([s.get("pv_scale", 1.0) for s in scen])
impcap = P.IMPORT_CAP_MW * np.array([s.get("imp_scale", 1.0) for s in scen])
outsel = np.array([s.get("outages", 1) for s in scen])
FACs = (ITs[:, None, None] * shares[None, :, None]) * pue[None, :, :]                 # (S, C, NH) -> memory ok
LK = sorted(set(s["load"] for s in scen))
COMMs = np.stack([COMM[s["load"]] for s in scen])                                      # (S, C, NH)
Lc = FACs + COMMs
ITc = ITs[:, None] * shares[None, :]                                                   # (S, C)
eng_cap_c = P.ENGINE_COVER * Lc.max(axis=2)                                            # (S, C) standby MW
eng_cap = eng_cap_c.sum(1)
bE = cap["batt_mw"] * P.BATT_HOURS; bP = cap["batt_mw"]
sq = math.sqrt(P.BATT_RTE)
budget_y = P.BD_ANNUAL_ML * 1e6 * P.BD_MJ_PER_L / 3600.0
gmax = (1 - P.BD_PILOT_MIN) / P.BD_PILOT_MIN
bg_cap = BG_MWH_H * 24 * P.BIOGAS_STORE_DAYS


def run():
    soc = 0.5 * bE.copy(); bstore = np.full(S, 0.5 * bg_cap); budget = np.full(S, budget_y)
    acc = {k: np.zeros(S) for k in ["load", "uns", "uns_isl", "imp", "exp", "curt", "wgen", "pgen", "eng", "bd", "bg", "bg_over",
                                     "bdis", "impcost", "exprev", "moved", "isl_hours"]}
    uns_t = np.zeros((S, NH), dtype=np.float32)
    eng_y = np.zeros((S, Y))
    tj = [j for j, s in enumerate(scen) if s.get("trace")]
    TR = {k: np.zeros((len(tj), NH), dtype=np.float32) for k in ["wind", "pv", "bdis", "bch", "imp", "exp", "curt", "eng", "load", "uns"]}
    for t in range(NH):
        if t % P.HPY == 0:
            budget[:] = budget_y
        isl = np.where(outsel[:, None] == 2, OUT2[None, :, t], OUT[None, :, t])        # (S, C)
        Lt = Lc[:, :, t]
        # islanded campuses: migrate flexible IT to the rest of the network, rest on campus engines
        mig = np.where(isl, P.FLEX_SHARE * ITc, 0.0)
        need_isl = np.where(isl, Lt - mig, 0.0)
        net_load = (np.where(isl, 0.0, Lt)).sum(1) + mig.sum(1)
        pv_av = (np.where(isl, 0.0, PVc[None, :, t] * shares[None, :])).sum(1) * cap["solar"] * psc
        wg = cap["wind"] * W[t] * wsc
        net = wg + pv_av - net_load
        ch = np.where(net > 0, np.minimum(np.minimum(net, bP), (bE - soc) / sq), 0.0); soc += ch * sq; net -= ch
        dis = np.where(net < 0, np.minimum(np.minimum(-net, bP), soc * sq), 0.0); soc -= dis / sq; net += dis
        sur = np.clip(net, 0, None)
        ex = np.minimum(sur, P.EXPORT_CAP_MW * aexp[t]); cu = sur - ex
        need = np.clip(-net, 0, None)
        im = np.minimum(need, impcap * aimp[t]); need = need - im
        # engines: network deficit (pooled standby on non-islanded campuses) + islanded campuses
        eng_avail = (np.where(isl, 0.0, eng_cap_c)).sum(1)
        e_net = np.minimum(need, eng_avail)
        e_isl = np.minimum(need_isl, eng_cap_c)
        e_req = e_net + e_isl.sum(1)
        bstore += BG_MWH_H
        over = np.clip(bstore - bg_cap, 0, None); bstore -= over
        F = e_req / P.ENG_ELEC_EFF
        G = np.minimum((1 - P.BD_PILOT_MIN) * F, bstore)
        D = F - G
        sc_ = np.where(D > budget, np.divide(budget, D, out=np.zeros(S), where=D > 0), 1.0)
        D = D * sc_; G = np.minimum(G, D * gmax)
        eng = (D + G) * P.ENG_ELEC_EFF
        frac = np.divide(eng, e_req, out=np.ones(S), where=e_req > 0)
        budget -= D; bstore -= G
        u_isl = (need_isl - e_isl * frac[:, None]).sum(1)
        u_net = need - e_net * frac
        uns = u_net + u_isl
        p = price[t]
        acc["load"] += net_load + need_isl.sum(1) + mig.sum(1) * 0
        acc["uns"] += uns; acc["uns_isl"] += u_isl; acc["imp"] += im; acc["exp"] += ex; acc["curt"] += cu
        acc["wgen"] += wg; acc["pgen"] += pv_av; acc["eng"] += eng; acc["bd"] += D; acc["bg"] += G; acc["bg_over"] += over
        acc["bdis"] += dis; acc["impcost"] += im * (p + P.NET_CHARGE_AUD_MWH); acc["exprev"] += ex * p
        acc["moved"] += mig.sum(1); acc["isl_hours"] += isl.sum(1)
        uns_t[:, t] = uns
        eng_y[:, t // P.HPY] += D
        if tj:
            for kk, vv in (("wind", wg), ("pv", pv_av), ("bdis", dis), ("bch", ch), ("imp", im), ("exp", ex), ("curt", cu),
                           ("eng", eng), ("load", net_load + need_isl.sum(1)), ("uns", uns)):
                TR[kk][:, t] = vv[tj]
    return acc, uns_t, eng_y, TR


def episodes(x, thr=1e-6):
    d = x > thr
    if not d.any():
        return dict(hours=0, episodes=0, longest=0, peak_mw=0.0)
    dd = np.diff(np.concatenate([[0], d.astype(int), [0]]))
    st = np.where(dd == 1)[0]; en = np.where(dd == -1)[0]
    return dict(hours=int(d.sum()), episodes=int(len(st)), longest=int((en - st).max()), peak_mw=float(x.max()))


t0 = time.time()
ACC, UNS, ENGY, TR = run()
runtime = time.time() - t0

grid_f = P.GRID_T_PER_MWH["VIC"]
results = []
for j, s in enumerate(scen):
    a = {k: float(v[j]) for k, v in ACC.items()}
    bd_MJ = a["bd"] / Y * 3600.0; bg_MJ = a["bg"] / Y * 3600.0; over_MJ = a["bg_over"] / Y * 3600.0
    bd_L = bd_MJ / P.BD_MJ_PER_L
    uco_L = min(bd_L, P.UCO_ML * 1e6 * P.UCO_YIELD); mkt_L = bd_L - uco_L
    c_wind = a["wgen"] / Y * P.WIND_G_KWH / 1e9
    c_pv = a["pgen"] / Y * P.PV_G_KWH / 1e9
    c_batt = float(bE[j]) * 1e3 * P.BATT_KG_PER_KWH / P.BATT_LIFE / 1e9
    c_imp = a["imp"] / Y * grid_f / 1e6
    c_eng = (uco_L * P.BD_MJ_PER_L * P.UCO_G_PER_MJ + mkt_L * P.BD_MJ_PER_L * P.MARKET_BD_G_PER_MJ + bg_MJ * P.BIOGAS_G_PER_MJ) / 1e12
    ep = episodes(UNS[j].astype(np.float64))
    results.append(dict(
        it_mw=s["it"], portfolio=s["pf"], scenario=s["name"], load=s["load"],
        solar_mw=float(cap["solar"][j]), wind_mw=float(cap["wind"][j]), batt_mw=float(bP[j]), batt_mwh=float(bE[j]),
        import_cap_mw=float(impcap[j]), engine_mw=float(eng_cap[j]),
        load_twh=a["load"] / 1e6 / Y, unserved_mwh_16y=a["uns"], unserved_isl_mwh_16y=a["uns_isl"],
        unserved_share=a["uns"] / a["load"], **{f"ep_{k}": v for k, v in ep.items()},
        wind_twh=a["wgen"] / 1e6 / Y, pv_twh=a["pgen"] / 1e6 / Y, imp_twh=a["imp"] / 1e6 / Y, exp_twh=a["exp"] / 1e6 / Y,
        curt_twh=a["curt"] / 1e6 / Y, batt_dis_twh=a["bdis"] / 1e6 / Y, eng_gwh=a["eng"] / 1e3 / Y,
        eng_hours_equiv=a["eng"] / Y / max(float(eng_cap[j]), 1e-9),
        bd_ML=bd_L / 1e6, bd_ML_max_year=float(ENGY[j].max() * 3600.0 / P.BD_MJ_PER_L / 1e6), uco_ML=uco_L / 1e6, market_bd_ML=mkt_L / 1e6,
        bg_engine_PJ=bg_MJ / 1e9, bg_surplus_PJ=over_MJ / 1e9,
        bg_share_engine=bg_MJ / (bg_MJ + bd_MJ) if (bg_MJ + bd_MJ) > 0 else 0.0,
        island_campus_hours_y=a["isl_hours"] / Y,
        c_wind=c_wind, c_pv=c_pv, c_batt=c_batt, c_imp=c_imp, c_eng=c_eng, gross=c_wind + c_pv + c_batt + c_imp + c_eng,
        imp_cost_m=a["impcost"] / Y / 1e6, exp_rev_m=a["exprev"] / Y / 1e6,
        eng_fuel_cost_m=(uco_L * (P.UCO_AUD_L / P.UCO_YIELD + P.UCO_CONV_AUD_L) + mkt_L * P.MARKET_BD_AUD_L + bg_MJ * P.BIOGAS_AUD_GJ / 1e3) / 1e6,
        renewable_share=(a["wgen"] + a["pgen"] - a["exp"] - a["curt"]) / a["load"],
    ))


def twh(x):
    return float(np.asarray(x).sum() / 1e6 / Y)


FAC_c = P.IT_MW * shares[:, None] * pue
heat = {}
for n, (deliv, hp) in HC.items():
    heat[n] = dict(delivered_twh=twh(deliv), hp_twh=twh(hp))
parts_twh = {k: twh(v) for k, v in D_parts.items()}
res_mwh = D_res.sum() / Y; dry_mwh = D_dry.sum() / Y
credit_gas = (res_mwh * P.GAS_HEAT_SHARE / P.RES_HEAT_GAS_BOILER_EFF + dry_mwh * P.GAS_HEAT_SHARE / P.DRY_GAS_EFF) * 3.6 * P.GAS_KG_PER_GJ / 1e9
credit_el = (res_mwh + dry_mwh) * (1 - P.GAS_HEAT_SHARE) * grid_f / 1e6
# metropolitan comparator climate
metro = {}
for m in P.METRO:
    Tm = EW["T"][SI[m["key"]]].astype(float)
    pm = P.PUE_BASE + P.PUE_COOL_A + P.PUE_COOL_SLOPE * np.clip(Tm - 18.0, 0, None) + P.PUE_TRIM_SLOPE * np.clip(Tm - 32.0, 0, None)
    metro[m["key"]] = dict(pue_mean=float(pm.mean()), T_mean=float(Tm.mean()), T_max=float(Tm.max()), hours_gt35=int((Tm > 35).sum() / Y))
out = dict(
    mode=MODE, proxy=PROXY, weather_source=str(EW["source"]), runtime_s=runtime, scenarios=results,
    it_mw=P.IT_MW, pop=P.POP, campus=[dict(c, it_mw=P.IT_MW * c["share"]) for c in P.CAMPUSES],
    fac_twh=twh(FAC_c), it_twh=P.IT_MW * P.HPY / 1e6, pue_mean=float(FAC_c.sum() / (P.IT_MW * NH)),
    pue_campus=(FAC_c.mean(1) / (P.IT_MW * shares)).tolist(), pue_max=float(pue.max()),
    led_twh=twh(LED), ras_twh=twh(RAS_E), boost_twh=twh(BOOST), ev_twh=twh(EV), hp_twh=heat["full"]["hp_twh"],
    comm_core_twh=twh(COMM["core"]), comm_ext_twh=twh(COMM["full_ext"]),
    heat=heat, heat_parts=parts_twh, heat_demand_twh=twh(D_tot), heat_credit_mt=float(credit_gas + credit_el),
    heat_credit_gas_mt=float(credit_gas), heat_credit_el_mt=float(credit_el),
    T_mean=T.mean(1).tolist(), T_max=T.max(1).tolist(), T_min=T.min(1).tolist(), hours_gt35=[int((T[i] > 35).sum() / Y) for i in range(C)],
    hdd=float(hdd[0].sum() / Y),
    pv_cf=float(PV.mean()), pv_cf_campus=PVc.mean(1).tolist(), wind_cf=float(W.mean()), wind_cf_zone=[float(w.mean()) for w in Wz],
    wind_cf_raw=wind_cf_raw, wind_c=wind_c, wind_pv_corr=float(np.corrcoef(W, PV)[0, 1]),
    wind_cf_year=[float(x) for x in W.reshape(Y, -1).mean(1)], pv_cf_year=[float(x) for x in PV.reshape(Y, -1).mean(1)],
    price_mean=float(price.mean()), regional_events=int(n_reg), import_avail_mean=float(aimp.mean()),
    produce_t=float(produce_kg.sum() / 1e3), seafood_t=float(seafood_kg.sum() / 1e3), gh_ha=float(gh_m2.sum() / 1e4),
    feed_t=float(seafood_kg.sum() / 1e3 * P.FCR), led_on_hours=float(led_on[0].sum() / Y),
    ras_N_excreted_t=float(seafood_kg.sum() / 1e3 * P.FCR * P.FEED_N * (1 - P.FISH_N_RETAIN)),
    biogas_pj=BIOGAS_PJ, biogas_src_pj={k: v * P.CH4_MJ_PER_M3 / 1e9 for k, v in bg_src.items()}, marc_t=marc_t,
    n_hh=n_hh, n_veh=n_veh, ev_gwh=ev_gwh, phev_fuel_ML=phev_fuel_ML, hh_connected=float(hh_c.sum()),
    metro=metro, year0=int(EW["year"][0]),
    heat_monthly={k: [float(v.sum(0)[month0 == m].sum() / Y / 1e3) for m in range(12)] for k, v in D_parts.items()},
    pv_monthly=[float(PV[month0 == m].mean()) for m in range(12)], wind_monthly=[float(W[month0 == m].mean()) for m in range(12)],
    led_monthly=[float(LED.sum(0)[month0 == m].sum() / Y / 1e3) for m in range(12)])
json.dump(out, open(os.path.join(HERE, f"dgs_results_{MODE}.json"), "w"), indent=1, default=float)
np.savez_compressed(os.path.join(HERE, f"dgs_trace_{MODE}.npz"), **TR,
                    names=np.array([f"{s['pf']}|{s['name']}" for s in scen if s.get("trace")]))
np.savez_compressed(os.path.join(HERE, f"dgs_hourly_{MODE}.npz"), W=W.astype(np.float32), PV=PV.astype(np.float32),
                    T=T.astype(np.float32), D_tot=D_tot.sum(0).astype(np.float32), price=price.astype(np.float32),
                    UNS=UNS[[0, 5, 6, 11]] if S > 11 else UNS)
print(f"{MODE}: {S} scenarios in {runtime:.1f} s{' [PROVISIONAL PROXY WEATHER]' if PROXY else ''}")
for r in results:
    print(f"  {r['it_mw']:7.1f} {r['portfolio']:10s} {r['scenario']:18s} load {r['load_twh']:.3f} imp {r['imp_twh']:.3f} exp {r['exp_twh']:.3f} "
          f"eng {r['eng_gwh']:.2f} GWh bd {r['bd_ML']:.3f} ML uns {r['unserved_mwh_16y']:.0f} MWh gross {r['gross']:.4f} RE {r['renewable_share']:.2f}")
