"""Digital Gardens Australia: ERA5 (2010-2025) hourly dispatch and ledgers.

Run: python dga_model.py [rez|palmer|raw]   (all files in this one folder)
"""
import sys, json, math, time
import numpy as np

import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True          # keep the folder flat: no __pycache__
sys.path.insert(0, HERE)
import dga_params as P
WIND_MODE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WIND_MODE", "rez")   # rez | palmer | raw
assert WIND_MODE in ("rez", "palmer", "raw"), WIND_MODE
rng = np.random.default_rng(P.SEED)


WFILE = os.path.join(HERE, "dga_era5_weather.npz")
if not os.path.exists(WFILE):
    sys.exit("dga_era5_weather.npz not found: run  python dga_weather.py  first")
EW = np.load(WFILE)
NH, H = P.NH, P.NHUB
assert EW["T"].shape[1] == NH
h = np.arange(NH)
yr = h // P.HPY
month = EW["month0"]                 # 0-based calendar month (UTC date)
doy = EW["doy"] - 1
hour_utc = EW["hour_utc"].astype(float)
YEAR0 = int(EW["year"][0])
shares = np.array([x["share"] for x in P.HUBS])
assert abs(shares.sum() - 1) < 1e-9
UTC_OFF = np.array([{"WA": 8.0, "SA": 9.5}.get(x["state"], 10.0) for x in P.HUBS])
HRL = (hour_utc[None, :] + UTC_OFF[:, None]) % 24.0          # local standard time, start of hour
hr = HRL                                                        # (H, NH) used by load profiles

# ------------------------------------------------------------------ temperature (ERA5 2 m)
T = EW["T"][:H].astype(float)

# ------------------------------------------------------------------ solar: ERA5 GHI/DNI/DHI -> single-axis tracker
PV = np.zeros((H, NH)); pv_ratio = []
B = 2 * np.pi * (doy - 81) / 364.0
eot = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)            # minutes
dec = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy + 1) / 365.0)
for i, hb in enumerate(P.HUBS):
    phi = math.radians(hb["lat"])
    solar_time = hour_utc - 0.5 + hb["lon"] / 15.0 + eot / 60.0              # mid-point of preceding hour
    om = np.radians(15.0 * (solar_time - 12.0))
    sz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(om)   # up
    sx = -np.cos(dec) * np.sin(om)                                            # east
    sy = np.cos(phi) * np.sin(dec) - np.sin(phi) * np.cos(dec) * np.cos(om)   # north
    up = sz > 0.01
    rot = np.clip(np.arctan2(sx, np.maximum(sz, 1e-6)), -np.radians(60), np.radians(60))
    cos_inc = np.clip(np.sin(rot) * sx + np.cos(rot) * sz, 0, None)
    ghi, dni, dhi = (EW[k][i].astype(float) for k in ("ghi", "dni", "dhi"))
    poa = np.where(up, dni * cos_inc + dhi * (1 + np.cos(rot)) / 2 + 0.2 * ghi * (1 - np.cos(rot)) / 2, 0.0)
    tcell = T[i] + poa * 0.03
    dc = np.clip(poa / 1000.0 * (1 - 0.0035 * (tcell - 25.0)), 0, None) * P.PV_DC_AC * (1 - P.PV_LOSS)
    PV[i] = np.minimum(dc, 1.0) * 0.99                                     # inverter efficiency/availability
    pv_ratio.append(P.PV_DC_AC)

# ------------------------------------------------------------------ wind: ERA5 100 m -> hub height -> 8-MW curve
def curve(v):
    p = np.where(v < 3.0, 0.0, np.where(v < 11.5, (v ** 3 - 27.0) / (11.5 ** 3 - 27.0), 1.0))
    return np.where(v >= 25.0, 0.0, p) * 0.90

W = np.zeros((H, NH)); wind_c = []; wind_cf_raw = []
for i, hb in enumerate(P.HUBS):
    rho = EW["ps"][i].astype(float) * 100.0 / (287.05 * (T[i] + 273.15))
    v = EW["ws100"][i].astype(float) * (P.HUB_HEIGHT_M / 100.0) ** P.SHEAR_ALPHA * (rho / 1.225) ** (1 / 3)
    cf_raw = curve(v).mean(); wind_cf_raw.append(float(cf_raw))
    if WIND_MODE == "raw":
        c = 1.0
    else:
        target = hb["wcf"] if WIND_MODE == "rez" else min(cf_raw / (1 - P.ERA5_CF_BIAS), 0.60)
        lo, hi = 0.5, 4.0
        for _ in range(60):
            c = 0.5 * (lo + hi)
            if curve(c * v).mean() < target:
                lo = c
            else:
                hi = c
    W[i] = curve(c * v)
    wind_c.append(float(c))

# ------------------------------------------------------------------ prices & grid availability
states = sorted(set(x["state"] for x in P.HUBS))
price = np.zeros((H, NH))
for st in states:
    idx = [i for i, x in enumerate(P.HUBS) if x["state"] == st]
    sol = PV[idx].mean(0)
    wnd = W[idx].mean(0)
    base = 85.0 if st == "WA" else 95.0
    peak = 45.0 * np.exp(-0.5 * ((hr[idx[0]] - 18.5) / 1.6) ** 2)
    p = base + peak - 80.0 * sol - 45.0 * (wnd - wnd.mean()) + 14.0 * rng.standard_normal(NH)
    spike = (rng.random(NH) < 0.0025) & (wnd < np.quantile(wnd, 0.3))
    p = p + spike * rng.pareto(1.6, NH) * 400.0
    p = np.clip(p, -40.0, 5000.0)
    for i in idx:
        price[i] = p
aimp = np.ones((H, NH))
aexp = np.ones((H, NH))
for i, hb in enumerate(P.HUBS):
    n_ev = rng.poisson(5 * P.YEARS)
    for _ in range(n_ev):
        s = rng.integers(0, NH)
        d = rng.integers(6, 49)
        aimp[i, s:s + d] = 0.25
        aexp[i, s:s + d] = 0.25
    aexp[i] = np.minimum(aexp[i], 1.0 - 0.45 * PV[i])

# ------------------------------------------------------------------ SMR availability
SMRav = np.zeros((H, NH))
for i, hb in enumerate(P.HUBS):
    if not hb["smr"]:
        continue
    units = []
    for u_ in range(P.SMR_UNITS_PER_CANDIDATE):
        a = np.ones(NH)
        cyc = int(P.SMR_CYCLE_MONTHS / 12 * P.HPY)
        off = int(rng.integers(0, cyc)) + u_ * cyc // 2
        for s in range(-cyc, NH, cyc):
            st_ = s + off
            a[max(st_, 0):max(min(st_ + P.SMR_REFUEL_DAYS * 24, NH), 0)] = 0.0
        # forced outages: mean 72 h, FOR ~3%
        n_f = rng.poisson(P.SMR_FOR * NH / 72.0)
        for _ in range(n_f):
            s = rng.integers(0, NH)
            a[s:s + int(rng.exponential(72)) + 1] = 0.0
        units.append(a)
    SMRav[i] = np.mean(units, axis=0)

# ------------------------------------------------------------------ loads
IT = P.IT_GW * 1e3 * shares                       # MW per hub
pue = P.PUE_BASE + P.PUE_COOL_A + P.PUE_COOL_SLOPE * np.clip(T - 18.0, 0, None) \
      + P.PUE_TRIM_SLOPE * np.clip(T - 32.0, 0, None)
FAC = IT[:, None] * pue                           # MW

N_h = P.ENROLLED * shares
produce_kg = N_h * P.PRODUCE_KG
seafood_kg = N_h * P.SEAFOOD_KG
gh_area = produce_kg / P.GH_YIELD
hdd = np.clip(18.0 - T, 0, None) / 24.0           # K-day per hour
D_gh = gh_area[:, None] * P.GH_HEAT_KWH_M2_PER_HDD * hdd / 1e3                     # MWh_th/h
D_ras = seafood_kg[:, None] * P.RAS_HEAT_KWH_PER_KG_PER_K * np.clip(P.RAS_SET_T - T, 0, None) / P.HPY / 1e3
hh = N_h / P.HH_SIZE * P.HH_CONNECT
D_res = (hh[:, None] * (P.DHW_MWH_HH / P.HPY + P.SPACE_KWH_HH_PER_HDD * hdd / 1e3))
dry_t = P.COMMUNITY_DRYING_T * shares
D_dry_total = dry_t[:, None] * P.COMMUNITY_DRYING_MWH_T / P.HPY * np.ones(NH)
D_dry = D_dry_total * (1 - P.DRYER_BOOSTER_SHARE)
BOOST = D_dry_total * P.DRYER_BOOSTER_SHARE        # electric booster MW
D_dig = (P.DIGESTER_TWH * 1e6 * shares / P.HPY)[:, None] * np.ones(NH)

# seaweed
asp_t = P.FEEDLOT_CAPACITY * P.ASP_COVER_SHARE * P.ASP_G_PER_HEAD_DAY * 365 / 1e6   # t DW/y
asp_ha = asp_t / P.ASP_YIELD_T_HA
asp_alloc = {"TAR": 0.35, "CAL": 0.40, "PTA": 0.25}
kelp_hubs = ["MUS", "LAT", "PTA", "COL"]
kelp_t = P.KELP_HA_PER_SITE * len(kelp_hubs) * P.KELP_DRIED_T_HA
kelp_ha = P.KELP_HA_PER_SITE * len(kelp_hubs)
kelp_wet = kelp_t / P.KELP_DRIED_SHARE_WET
kelp_season = np.where(np.isin(month, [8, 9, 10, 11]), 1.0, 0.25)
kelp_season = kelp_season / kelp_season.mean()
D_sw = np.zeros((H, NH)); E_sw = np.zeros((H, NH))
for i, hb in enumerate(P.HUBS):
    a = asp_alloc.get(hb["key"], 0.0) * asp_t * 1e3      # kg/y
    k = (kelp_t * 1e3 / len(kelp_hubs)) if hb["key"] in kelp_hubs else 0.0
    dry = (a + k) * P.DRY_KWH_TH_PER_KG / 1e3 / P.HPY        # MWh/h average
    tank = a * P.ASP_HEAT_KWH_PER_KG / 1e3 / P.HPY if hb["key"] == "PTA" else 0.0
    kd = k * P.DRY_KWH_TH_PER_KG / 1e3 / P.HPY
    ad = a * P.DRY_KWH_TH_PER_KG / 1e3 / P.HPY
    D_sw[i] = ad + kd * kelp_season + tank
    E_sw[i] = (a * P.ASP_KWH_PER_KG + k * P.KELP_KWH_PER_KG_DRIED) / 1e3 / P.HPY
D_wat = (P.DESAL_M3 * P.DESAL_KWH_TH_M3 / 1e3 * shares / P.HPY)[:, None] * np.ones(NH)
E_wat = (P.DESAL_M3 * P.DESAL_KWH_E_M3 / 1e3 * shares / P.HPY)[:, None] * np.ones(NH)
RAS_E = (seafood_kg * P.RAS_KWH_PER_KG / 1e3 / P.HPY)[:, None] * np.ones(NH)

# heat demand stacks (MWh_th/h)
D_parts = {"residential": D_res, "greenhouse": D_gh, "aquaculture": D_ras, "drying": D_dry,
           "seaweed": D_sw, "water_treatment": D_wat, "digester": D_dig}
D_tot = sum(D_parts.values())

# mobility loads
ers_hub = np.zeros(H)
ers_rows = []
for name, km, aadt, alloc, path in P.ERS_CORRIDORS:
    e_mwh = aadt * 365 * km * P.ERS_SHARE * P.ERS_KWH_PER_KM / (1 - P.ERS_LOSS) / 1e3
    diesel_l = aadt * 365 * km * P.ERS_SHARE * P.TRUCK_L_PER_KM
    ers_rows.append(dict(corridor=name, km=km, aadt=aadt, gwh=e_mwh / 1e3, diesel_ML=diesel_l / 1e6,
                         co2_kt=diesel_l * P.DIESEL_KG_PER_L / 1e6))
    for k_, s_ in alloc.items():
        ers_hub[P.HUB_KEYS.index(k_)] += e_mwh * s_
truck_prof = 0.6 + 0.8 * np.exp(-0.5 * ((hr - 13) / 4.5) ** 2)
truck_prof = truck_prof / truck_prof.mean(1, keepdims=True)
ERS = (ers_hub / P.HPY)[:, None] * truck_prof
parcels = P.ENROLLED * (P.PRODUCE_KG + P.SEAFOOD_KG) / P.DRONE_PARCEL_KG * P.DRONE_PARCEL_SHARE
deliv_drones = math.ceil(parcels / (P.DRONE_DELIV_PER_DAY * P.DRONE_DAYS))
drone_mwh = (parcels * P.DRONE_KWH_PER_DELIVERY + H * P.DRONE_INSPECT_PER_HUB * P.DRONE_INSPECT_KWH_YR
             + H * P.DRONE_AG_PER_HUB * P.DRONE_AG_KWH_YR) / 1e3
day_prof = np.where((hr >= 7) & (hr < 18), 1.0, 0.05); day_prof /= day_prof.mean(1, keepdims=True)
DRONE = (drone_mwh * shares / P.HPY)[:, None] * day_prof
ev_prof = 0.4 + np.exp(-0.5 * ((hr - 12) / 3) ** 2) * 1.6; ev_prof /= ev_prof.mean(1, keepdims=True)
n_hh = P.ENROLLED / P.HH_SIZE
n_veh = n_hh * P.VEH_PER_HH
ev_gwh = n_veh * P.VEH_KM_Y * (P.VEH_EV_SHARE * P.EV_KWH_KM + (1 - P.VEH_EV_SHARE) * P.PHEV_E_SHARE * P.PHEV_KWH_KM) / (1 - P.CHARGE_LOSS) / 1e6
phev_fuel_ML = n_veh * (1 - P.VEH_EV_SHARE) * P.VEH_KM_Y * (1 - P.PHEV_E_SHARE) * P.PHEV_L_100KM / 100 / 1e6
EV = (ev_gwh * 1e3 * shares / P.HPY)[:, None] * ev_prof
MOB = ERS + DRONE + EV

# ---------------------------------------------------------------- digester biogas (fuel MWh per hour, per hub)
asp_head = P.FEEDLOT_CAPACITY * P.ASP_COVER_SHARE
bg_src = {}
_m3 = asp_head * P.FEEDLOT_VS_KG_HEAD_DAY * 365 * P.FEEDLOT_MANURE_CAPTURE * P.FEEDLOT_B0
bg_src["feedlot_manure"] = np.array([asp_alloc.get(hb["key"], 0.0) for hb in P.HUBS]) * _m3
bg_src["food_garden_organics"] = N_h * P.FOGO_T_PER_RESIDENT * 1e3 * P.FOGO_VS * P.FOGO_B0
bg_src["glasshouse_residue"] = produce_kg * P.GH_RESIDUE_T_PER_T * P.GH_RESIDUE_VS * P.GH_RESIDUE_B0
bg_src["ras_sludge"] = seafood_kg * P.FCR * P.RAS_SLUDGE_DM_PER_FEED * P.RAS_SLUDGE_VS * P.RAS_SLUDGE_B0
bg_src["fish_offal"] = seafood_kg * P.FISH_OFFAL_SHARE * P.FISH_OFFAL_VS * P.FISH_OFFAL_B0
bg_src_pj = {k: float(v.sum() * P.CH4_MJ_PER_M3 / 1e9) for k, v in bg_src.items()}
BG_HUB_MWH_H = sum(bg_src.values()) * P.CH4_MJ_PER_M3 / 3600.0 / P.HPY      # MWh fuel per hour, per hub
BIOGAS_PJ = sum(bg_src_pj.values())
# Asparagopsis algae-scrubber nitrogen balance (raceways fed with RAS effluent)
asp_N_t = asp_t * P.ASP_N_DW
ras_N_excreted_t = float(seafood_kg.sum() / 1e3 * P.FCR * P.FEED_N * (1 - P.FISH_N_RETAIN))


def heat_case(c, k):
    cap = k * D_tot.mean(1, keepdims=True)
    deliv = np.minimum(c * D_tot, cap)
    frac = np.divide(deliv, D_tot, out=np.zeros_like(deliv), where=D_tot > 0)
    parts = {n: v * frac for n, v in D_parts.items()}
    hp_e = deliv / ((1 - P.HEAT_LOSS) * P.HP_COP)
    return deliv, parts, hp_e


HEATCASES = {"full": (1.0, 3.0), "plant1x": (1.0, 1.0), "half": (0.5, 2.0), "none": (0.0, 2.0)}
hc = {n: heat_case(*v) for n, v in HEATCASES.items()}

def load_for(case, mobility=True, flat=False):
    deliv, parts, hp_e = hc[case]
    L = FAC + BOOST + RAS_E + E_sw + E_wat + hp_e + (MOB if mobility else 0.0)
    if flat:
        L = L.mean(1, keepdims=True) * np.ones(NH)
    return L

LOADS = {"full_ext": load_for("full"), "flat_ext": load_for("full", flat=True),
         "full_core": load_for("full", mobility=False),
         "plant1x": load_for("plant1x", mobility=False), "half": load_for("half", mobility=False), "none": load_for("none", mobility=False)}
LKEYS = list(LOADS)
LSTACK = np.stack([LOADS[k] for k in LKEYS])     # (K,H,NH)

# ------------------------------------------------------------------ dispatch
def run(scen):
    """scen: list of dicts with portfolio, wind_scale, access, firm_cap_mw (or None), load key."""
    S = len(scen)
    hub_scale = shares * H
    def cap(key):
        return np.array([[P.PORTFOLIOS[s["portfolio"]][key] for _ in range(H)] for s in scen]) * hub_scale
    wcap = cap("wind") * 1e3; pcap = cap("solar") * 1e3; bE = cap("batt") * 1e3
    bP = bE / 4.0
    hvo = cap("hvo"); impc = cap("imp"); expc = cap("exp")
    smr_on = np.array([P.PORTFOLIOS[s["portfolio"]]["smr"] for s in scen])
    smr_mw = np.array([[P.SMR_UNIT_MW * P.SMR_UNITS_PER_CANDIDATE if hb["smr"] else 0.0 for hb in P.HUBS]] * S) * smr_on[:, None]
    for j, s in enumerate(scen):
        if s.get("firm_cap") is not None:
            hvo[j] = np.minimum(hvo[j], s["firm_cap"])
    wsc = np.array([s.get("wind_scale", 1.0) for s in scen])[:, None]
    psc = np.array([s.get("pv_scale", 1.0) for s in scen])[:, None]
    acc = np.array([s.get("access", 1.0) for s in scen])[:, None]
    kidx = np.array([LKEYS.index(s["load"]) for s in scen])
    flex = (P.FLEX_SHARE * IT)[None, :] * np.ones((S, 1))
    sq = math.sqrt(P.BATT_RTE)
    budget_y = P.HVO_ANNUAL_ML * 1e6 * P.HVO_MJ_PER_L / 3600.0   # biodiesel fuel energy, MWh
    eff = P.HVO_ELEC_EFF
    bg_in = BG_HUB_MWH_H[None, :] * np.ones((S, 1))
    bg_cap = bg_in * 24.0 * P.BIOGAS_STORE_DAYS
    bstore = 0.5 * bg_cap
    gmax = (1.0 - P.BD_PILOT_MIN) / P.BD_PILOT_MIN          # biogas : biodiesel energy ratio ceiling (67:33)
    soc = 0.5 * bE.copy()
    acc_ = {k: np.zeros((S, H)) for k in ["uns", "imp", "exp", "hvo", "curt", "wgen", "pgen", "sgen",
                                           "load", "impcost", "exprev", "moved", "bdis", "bd_fuel", "bg_fuel", "bg_over"]}
    uns_t = np.zeros((S, NH), dtype=np.float32)
    tj = [j for j, s in enumerate(scen) if s.get("trace")]
    TR = {k: np.zeros((len(tj), NH), dtype=np.float32) for k in ["wind", "pv", "smr", "bdis", "bch", "hvo", "imp", "exp", "curt", "load", "uns", "moved"]}
    hvo_y = np.zeros((S, P.YEARS))
    budget = np.full(S, budget_y)
    for t in range(NH):
        if t % P.HPY == 0:
            budget[:] = budget_y
        wg = wcap * W[:, t] * wsc
        pg = pcap * PV[:, t] * psc
        sg = smr_mw * SMRav[:, t]
        L = LSTACK[kidx, :, t]
        net = wg + pg + sg - L
        # workload migration between hubs (flexible inference share)
        shed = np.minimum(np.clip(-net, 0, None), flex)
        absb = np.minimum(np.clip(net, 0, None), flex)
        X = shed.sum(1); Y = absb.sum(1); M = np.minimum(X, Y)
        fs = np.divide(M, X, out=np.zeros(S), where=X > 0)
        fa = np.divide(M, Y, out=np.zeros(S), where=Y > 0)
        net = net + shed * fs[:, None] - absb * fa[:, None]
        # battery
        ch = np.where(net > 0, np.minimum(np.minimum(net, bP), (bE - soc) / sq), 0.0)
        soc += ch * sq; net -= ch
        dis = np.where(net < 0, np.minimum(np.minimum(-net, bP), soc * sq), 0.0)
        soc -= dis / sq; net += dis
        # export / curtail
        surplus = np.clip(net, 0, None)
        ex = np.minimum(surplus, expc * aexp[:, t] * acc)
        cu = surplus - ex
        # deficit: renewable fuel engines, then imports
        need = np.clip(-net, 0, None)
        # budget pacing: if renewable-fuel use is ahead of the annual schedule, import first
        frac_t = 1.0 - (t % P.HPY) / P.HPY
        imfirst = (budget / budget_y) < 0.9 * frac_t
        impav = impc * aimp[:, t] * acc
        im1 = np.where(imfirst[:, None], np.minimum(need, impav), 0.0)
        need -= im1
        # dual-fuel engines: biogas from the hub gas holder up to 67% of fuel energy, biodiesel >= 33% pilot
        bstore += bg_in
        over = np.clip(bstore - bg_cap, 0, None); bstore -= over
        Fq = np.minimum(need, hvo) / eff                     # fuel energy wanted, MWh
        Gq = np.minimum((1.0 - P.BD_PILOT_MIN) * Fq, bstore)
        Dq = Fq - Gq
        tot = Dq.sum(1)
        scale = np.where(tot > budget, np.divide(budget, tot, out=np.zeros(S), where=tot > 0), 1.0)
        Dq = Dq * scale[:, None]
        Gq = np.minimum(Gq, Dq * gmax)
        hv = (Dq + Gq) * eff
        budget -= Dq.sum(1); bstore -= Gq
        acc_["bd_fuel"] += Dq; acc_["bg_fuel"] += Gq; acc_["bg_over"] += over
        need -= hv
        im = np.minimum(need, impav - im1) + im1
        need -= (im - im1)
        pr = price[:, t]
        acc_["uns"] += need; acc_["imp"] += im; acc_["exp"] += ex; acc_["hvo"] += hv
        acc_["curt"] += cu; acc_["wgen"] += wg; acc_["pgen"] += pg; acc_["sgen"] += sg
        acc_["load"] += L; acc_["impcost"] += im * (pr + P.NET_CHARGE_AUD_MWH); acc_["exprev"] += ex * pr
        acc_["moved"] += (shed * fs[:, None]); acc_["bdis"] += dis
        uns_t[:, t] = need.sum(1)
        if tj:
            for kk, vv in (("wind", wg), ("pv", pg), ("smr", sg), ("bdis", dis), ("bch", ch), ("hvo", hv), ("imp", im),
                           ("exp", ex), ("curt", cu), ("load", L), ("uns", need), ("moved", shed * fs[:, None])):
                TR[kk][:, t] = vv[tj].sum(1)
        hvo_y[:, t // P.HPY] += Dq.sum(1)
    run.trace = TR
    return acc_, uns_t, hvo_y


def episodes(series, thr=1e-6):
    d = series > thr
    hours = int(d.sum())
    if hours == 0:
        return dict(hours=0, episodes=0, longest=0, peak_gw=0.0, h_ge1gw=0)
    dd = np.diff(np.concatenate([[0], d.astype(int), [0]]))
    starts = np.where(dd == 1)[0]; ends = np.where(dd == -1)[0]
    return dict(hours=hours, episodes=int(len(starts)), longest=int((ends - starts).max()),
                peak_gw=float(series.max() / 1e3), h_ge1gw=int((series >= 1000).sum()))


SUPPLY = [("central", {}), ("wind_minus10", {"wind_scale": 0.9}), ("pv_minus10", {"pv_scale": 0.9}), ("half_access", {"access": 0.5}),
          ("firm_restricted", {"firm_cap": P.FIRM_RESTRICT_MW}),
          ("combined_adverse", {"wind_scale": 0.9, "access": 0.5, "firm_cap": P.FIRM_RESTRICT_MW}),
          ("central_flat_load", {})]
scen = []
for pf in ["reference", "enlarged", "enl_smr"]:
    for nm, kw in SUPPLY:
        d = dict(portfolio=pf, name=nm, load="flat_ext" if nm == "central_flat_load" else "full_ext",
                 trace=(pf in ("enlarged", "enl_smr") and nm in ("central", "combined_adverse")))
        d.update(kw); scen.append(d)
for case in ["full_core", "plant1x", "half", "none"]:
    for nm in ["central", "combined_adverse"]:
        d = dict(portfolio="enlarged", name=f"heat_{case}_{nm}", load=case)
        if nm == "combined_adverse":
            d.update({"wind_scale": 0.9, "access": 0.5, "firm_cap": P.FIRM_RESTRICT_MW})
        scen.append(d)

t0 = time.time()
ACC, UNS, HVOY = run(scen)
runtime = time.time() - t0

# ------------------------------------------------------------------ ledgers
Y = P.YEARS
def mt(x):
    return float(x)

grid_f = np.array([P.GRID_T_PER_MWH[hb["state"]] for hb in P.HUBS])
results = []
for j, s in enumerate(scen):
    a = {k: v[j] for k, v in ACC.items()}
    load_twh = a["load"].sum() / 1e6 / Y
    hvo_mwh = a["hvo"].sum() / Y                               # engine electricity, MWh_e/y
    bd_MJ = a["bd_fuel"].sum() / Y * 3600.0                     # biodiesel fuel, MJ/y
    bg_MJ = a["bg_fuel"].sum() / Y * 3600.0                     # biogas burnt in engines, MJ/y
    bg_over_MJ = a["bg_over"].sum() / Y * 3600.0                # surplus biogas -> biomethane farm fuel
    hvo_L = bd_MJ / P.HVO_MJ_PER_L                              # biodiesel litres
    uco_L = min(hvo_L, P.UCO_ML * 1e6 * P.UCO_YIELD)
    tal_L = hvo_L - uco_L
    pf = P.PORTFOLIOS[s["portfolio"]]
    batt_gwh = pf["batt"] * H
    c_wind = a["wgen"].sum() / Y * P.WIND_G_KWH / 1e6        # MWh * g/kWh = kg ... -> t: MWh*1e3 kWh*g/1e6 = t
    # tonnes: MWh * 1000 kWh/MWh * g/kWh / 1e6 g/t = MWh*g/1e3 ; Mt = /1e6
    c_wind = a["wgen"].sum() / Y * P.WIND_G_KWH / 1e3 / 1e6
    c_pv = a["pgen"].sum() / Y * P.PV_G_KWH / 1e3 / 1e6
    c_smr = a["sgen"].sum() / Y * P.NUC_G_KWH / 1e3 / 1e6
    c_batt = batt_gwh * 1e6 * P.BATT_KG_PER_KWH / P.BATT_LIFE / 1e9
    c_imp = float((a["imp"] / Y * grid_f).sum()) / 1e6
    c_hvo = (uco_L * P.HVO_MJ_PER_L * P.UCO_G_PER_MJ + tal_L * P.HVO_MJ_PER_L * P.TALLOW_G_PER_MJ
             + bg_MJ * P.BIOGAS_G_PER_MJ) / 1e12
    uns = UNS[j].astype(np.float64)
    ep = episodes(uns)
    results.append(dict(
        portfolio=s["portfolio"], scenario=s["name"], load=s["load"],
        load_twh=load_twh, unserved_twh_16y=a["uns"].sum() / 1e6, unserved_share=a["uns"].sum() / a["load"].sum(),
        **{f"ep_{k}": v for k, v in ep.items()},
        wind_twh=a["wgen"].sum() / 1e6 / Y, pv_twh=a["pgen"].sum() / 1e6 / Y, smr_twh=a["sgen"].sum() / 1e6 / Y,
        curt_twh=a["curt"].sum() / 1e6 / Y, exp_twh=a["exp"].sum() / 1e6 / Y, imp_twh=a["imp"].sum() / 1e6 / Y,
        hvo_twh=hvo_mwh / 1e6, hvo_ML=hvo_L / 1e6, hvo_ML_max_year=float(HVOY[j].max() * 3600.0 / P.HVO_MJ_PER_L / 1e6),
        uco_ML=uco_L / 1e6, tallow_ML=tal_L / 1e6, bg_engine_PJ=bg_MJ / 1e9, bg_surplus_PJ=bg_over_MJ / 1e9,
        bg_share_engine=bg_MJ / (bg_MJ + bd_MJ) if (bg_MJ + bd_MJ) > 0 else 0.0,
        biogas_cost_m=(bg_MJ * P.BIOGAS_AUD_GJ + bg_over_MJ * (P.BIOGAS_AUD_GJ + P.BIOMETHANE_UPGRADE_AUD_GJ)) / 1e3 / 1e6,
        moved_twh=a["moved"].sum() / 1e6 / Y, batt_dis_twh=a["bdis"].sum() / 1e6 / Y,
        c_wind=c_wind, c_pv=c_pv, c_smr=c_smr, c_batt=c_batt, c_imp=c_imp, c_hvo=c_hvo,
        gross=c_wind + c_pv + c_smr + c_batt + c_imp + c_hvo,
        imp_cost_m=a["impcost"].sum() / Y / 1e6, exp_rev_m=a["exprev"].sum() / Y / 1e6,
        hvo_cost_m=(uco_L * (P.UCO_AUD_L / P.UCO_YIELD + P.UCO_CONV_AUD_L) + tal_L * P.TALLOW_BD_AUD_L
                    + bg_MJ * P.BIOGAS_AUD_GJ / 1e3) / 1e6,
        imp_by_hub=(a["imp"].sum(1) / Y / 1e6 if a["imp"].ndim > 1 else (a["imp"] / Y / 1e6)).tolist(),
    ))

# matched electricity services and heat credits
def twh(x):
    return float(x.sum() / 1e6 / Y)

fac_twh = twh(FAC)
boost_twh = twh(BOOST)
ras_twh = twh(RAS_E)
sw_e_twh = twh(E_sw)
wat_e_twh = twh(E_wat)
ers_twh = twh(ERS); drone_twh = twh(DRONE); ev_twh = twh(EV)
heat_tab = {}
gas_share = np.array([hb["gas_heat_share"] for hb in P.HUBS])
for n, (deliv, parts, hp_e) in hc.items():
    res = parts["residential"].sum(1) / Y        # MWh_th/y per hub
    dry = parts["drying"].sum(1) / Y
    gas_GJ = (res * gas_share / P.RES_HEAT_GAS_BOILER_EFF + dry / P.DRY_GAS_EFF) * 3.6
    credit_gas = gas_GJ * P.GAS_KG_PER_GJ / 1e9                       # Mt
    credit_el = (res * (1 - gas_share) * grid_f).sum() / 1e6          # resistive heating displaced, Mt
    heat_tab[n] = dict(
        delivered_twh=twh(deliv), demand_twh=twh(D_tot), hp_twh=twh(hp_e),
        parts={k: twh(v) for k, v in parts.items()},
        credit_mt=float(credit_gas.sum() + credit_el),
        credit_gas_mt=float(credit_gas.sum()), credit_el_mt=float(credit_el),
        res_twh=float(res.sum() / 1e6), dry_twh=float(dry.sum() / 1e6),
        core_service_twh=fac_twh + boost_twh + ras_twh + sw_e_twh + wat_e_twh + twh(hp_e),
        ext_service_twh=fac_twh + boost_twh + ras_twh + sw_e_twh + wat_e_twh + twh(hp_e) + ers_twh + drone_twh + ev_twh)

ers_diesel_L = sum(r["diesel_ML"] for r in ers_rows) * 1e6
ers_credit = ers_diesel_L * P.DIESEL_KG_PER_L / 1e9
van_L = parcels * P.VAN_KM_PER_DELIVERY * P.VAN_L_PER_KM
drone_credit = van_L * P.DIESEL_KG_PER_L / 1e9


def gas_case(E_twh, capture=0.0, leak=P.LEAK, penalty=None, eff=P.CCGT_EFF_HHV):
    pen = P.CCS_PENALTY if (capture > 0 and penalty is None) else (penalty or 0.0)
    fuel_GJ = E_twh * 3.6e6 / eff * (1 + pen)
    co2 = fuel_GJ * P.GAS_KG_PER_GJ * (1 - capture) / 1e9
    ch4 = fuel_GJ * P.CH4_KG_PER_GJ * leak / (1 - leak) * P.GWP_CH4 / 1e9
    return dict(fuel_twh=fuel_GJ / 3.6e6, co2=co2, ch4=ch4, total=co2 + ch4,
                nonelec_twh=fuel_GJ / 3.6e6 - E_twh)

E_core = heat_tab["full"]["core_service_twh"]
E_ext = heat_tab["full"]["ext_service_twh"]
gas = {}
for lab, E in [("facility", fac_twh), ("facility_boost", fac_twh + boost_twh), ("core", E_core), ("ext", E_ext)]:
    gas[lab] = {c: gas_case(E, capture=c) for c in [0.0, 0.90, 0.95]}

Tw = EW["T"][7].astype(float)
pue_w = P.PUE_BASE + P.PUE_COOL_A + P.PUE_COOL_SLOPE * np.clip(Tw - 18.0, 0, None) + P.PUE_TRIM_SLOPE * np.clip(Tw - 32.0, 0, None)
weddell = dict(T_mean=float(Tw.mean()), T_max=float(Tw.max()), hours_gt35=int((Tw > 35).sum() / Y), pue_mean=float(pue_w.mean()),
               rh_mean=float(EW["rh"][7].mean()), fac_twh_itequal=float(P.IT_TWH * pue_w.mean()),
               ccgt_eff_mean=float(np.mean(P.CCGT_EFF_HHV - 0.001 * np.clip(Tw - 15.0, 0, None))))
out = dict(runtime_s=runtime, weddell=weddell, scenarios=results, heat=heat_tab, gas=gas,
           fac_twh=fac_twh, boost_twh=boost_twh, ras_twh=ras_twh, sw_e_twh=sw_e_twh, wat_e_twh=wat_e_twh,
           ers_twh=ers_twh, drone_twh=drone_twh, ev_twh=ev_twh, E_core=E_core, E_ext=E_ext,
           pue_mean=float((FAC.sum()) / (IT.sum() * NH)), pue_hub=(FAC.mean(1) / IT).tolist(),
           pue_max=float(pue.max()), hours_T_gt35=[int((T[i] > 35).sum() / Y) for i in range(H)],
           T_mean=T.mean(1).tolist(), T_max=T.max(1).tolist(), T_min=T.min(1).tolist(),
           wind_cf=W.mean(1).tolist(), pv_cf=PV.mean(1).tolist(), wind_c=wind_c, pv_ratio=pv_ratio, wind_mode=WIND_MODE, wind_cf_raw=wind_cf_raw, year0=YEAR0,
           wind_cf_year_min=[float(W[i].reshape(Y, -1).mean(1).min()) for i in range(H)],
           wind_cf_year_max=[float(W[i].reshape(Y, -1).mean(1).max()) for i in range(H)],
           pv_cf_year_min=[float(PV[i].reshape(Y, -1).mean(1).min()) for i in range(H)],
           pv_cf_year_max=[float(PV[i].reshape(Y, -1).mean(1).max()) for i in range(H)],
           wind_corr=np.corrcoef(W).tolist(), price_mean=price.mean(1).tolist(),
           smr_avail=[float(SMRav[i].mean()) for i in range(H)],
           IT_mw=IT.tolist(), enrolled=P.ENROLLED, N_h=N_h.tolist(),
           produce_t=float(produce_kg.sum() / 1e3), seafood_t=float(seafood_kg.sum() / 1e3),
           gh_ha=float(gh_area.sum() / 1e4), feed_t=float(seafood_kg.sum() / 1e3 * P.FCR),
           asp_t=asp_t, asp_ha=asp_ha, kelp_t=kelp_t, kelp_ha=kelp_ha, kelp_wet_t=kelp_wet,
           asp_ch4_abate_mt=P.FEEDLOT_CAPACITY * P.ASP_COVER_SHARE * P.CH4_KG_HEAD_YR * P.ASP_CH4_CUT * P.GWP_CH4 / 1e9,
           asp_head=P.FEEDLOT_CAPACITY * P.ASP_COVER_SHARE,
           kelp_co2_kt=kelp_wet * P.KELP_KG_CO2E_PER_T_FRESH / 1e6, kelp_N_t=kelp_t * (1 - P.KELP_DRIED_MOISTURE) * P.KELP_N_KG_PER_T_DW / 1e3,
           ers=ers_rows, ers_credit_mt=ers_credit, ers_diesel_ML=ers_diesel_L / 1e6,
           ers_km=sum(r["km"] for r in ers_rows),
           parcels=parcels, deliv_drones=deliv_drones,
           drones_total=deliv_drones + H * (P.DRONE_INSPECT_PER_HUB + P.DRONE_AG_PER_HUB),
           drone_credit_mt=drone_credit, van_L=van_L,
           ers_hub_gwh=(ers_hub / 1e3).tolist(),
           biogas_pj=BIOGAS_PJ, biogas_src_pj=bg_src_pj, asp_N_t=asp_N_t, ras_N_excreted_t=ras_N_excreted_t,
           n_hh=n_hh, n_veh=n_veh, ev_gwh=ev_gwh, phev_fuel_ML=phev_fuel_ML,
           hh_connected=float((N_h / P.HH_SIZE * P.HH_CONNECT).sum()))
with open(os.path.join(HERE, f"dga_results_{WIND_MODE}.json"), "w") as f:
    json.dump(out, f, indent=1, default=float)
np.savez_compressed(os.path.join(HERE, f"dga_trace_{WIND_MODE}.npz"), **{k: v for k, v in run.trace.items()},
                    names=np.array([f"{s['portfolio']}|{s['name']}" for s in scen if s.get("trace")]))
np.savez_compressed(os.path.join(HERE, f"dga_hourly_{WIND_MODE}.npz"), UNS=UNS, W=W.astype(np.float32), PV=PV.astype(np.float32),
                    T=T.astype(np.float32), D_tot=D_tot.astype(np.float32), FAC=FAC.astype(np.float32),
                    LOAD=LOADS["full_ext"].astype(np.float32), SMRav=SMRav.astype(np.float32),
                    price=price.astype(np.float32))
print("runtime", runtime)
for r in results:
    print(f"{r['portfolio']:9s} {r['scenario']:28s} load {r['load_twh']:6.2f} uns16 {r['unserved_twh_16y']:8.3f} "
          f"peak {r['ep_peak_gw']:5.2f} hrs {r['ep_hours']:6d} imp {r['imp_twh']:5.2f} hvoML {r['hvo_ML']:6.0f} "
          f"exp {r['exp_twh']:5.2f} curt {r['curt_twh']:5.2f} gross {r['gross']:5.3f} moved {r['moved_twh']:4.2f}")
