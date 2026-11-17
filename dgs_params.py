"""Parameters for Digital Gardens Sunraysia (DGS): a population-weighted, distributed AI data-centre
network for 16 Sunraysia and Murray-corridor towns. Every value is a scenario assumption unless a source
is given here or in the manuscript.
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = 16
HPY = 8760
NH = YEARS * HPY                       # 140,160 hours (2010-2025, 29 February removed)
SEED = 20261117

# ---------------------------------------------------------------- towns (ABS 2021 Census locality counts)
TOWNS = []
with open(os.path.join(HERE, "dgs_towns_2021.csv"), newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        TOWNS.append(dict(town=r["town"], state=r["state"], pop=int(r["2021_census_locality_population"]),
                          phase=r["phase"], campus=r["shared_campus"], source=r["source_url"]))
POP = sum(t["pop"] for t in TOWNS)                                   # 75,833
KW_IT_PER_RESIDENT = 4.6                                            # website reference sizing
IT_MW = round(POP * KW_IT_PER_RESIDENT / 1e3, 1)                     # 348.8 MW central
IT_SCENARIOS = [100.0, 300.0, IT_MW, 500.0, 1000.0]

# ---------------------------------------------------------------- six shared campuses (anchor coordinates)
CAMPUS_DEF = [
    ("MIL", "Mildura + Buronga + Gol Gol", "Mildura", -34.185, 142.159, "VIC", "Core"),
    ("IRC", "Irymple + Red Cliffs + Koorlong + Cardross", "Irymple", -34.232, 142.165, "VIC", "Core"),
    ("MWD", "Merbein + Wentworth + Dareton", "Merbein", -34.167, 142.057, "VIC", "Core"),
    ("ROB", "Robinvale + Euston", "Robinvale", -34.584, 142.768, "VIC", "Expansion"),
    ("SWH", "Swan Hill + Nyah", "Swan Hill", -35.339, 143.559, "VIC", "Expansion"),
    ("KER", "Kerang + Koondrook", "Kerang", -35.734, 143.919, "VIC", "Expansion"),
]
CAMPUSES = []
for key, group, anchor, lat, lon, st, ph in CAMPUS_DEF:
    pop = sum(t["pop"] for t in TOWNS if t["campus"] == group)
    CAMPUSES.append(dict(key=key, group=group, anchor=anchor, lat=lat, lon=lon, state=st, phase=ph, pop=pop, share=pop / POP))
NC = len(CAMPUSES)
CKEYS = [c["key"] for c in CAMPUSES]

# ---------------------------------------------------------------- weather sites (ERA5 via Open-Meteo)
# 6 campuses + 2 South West REZ wind zones (approximate locations of contracted wind) + 2 metropolitan comparators
WIND_ZONES = [
    dict(key="POT", name="Pottinger area, near Hay (NSW South West REZ)", lat=-34.43, lon=145.25),
    dict(key="YAN", name="Yanco Delta area, near Jerilderie (NSW South West REZ)", lat=-35.29, lon=145.66),
]
METRO = [
    dict(key="EAC", name="Eastern Creek, western Sydney (NSW)", lat=-33.80, lon=150.85, state="NSW"),
    dict(key="LAV", name="Laverton North, western Melbourne (VIC)", lat=-37.82, lon=144.78, state="VIC"),
]
SITE_KEYS = CKEYS + [w["key"] for w in WIND_ZONES] + [m["key"] for m in METRO]
WIND_TARGET_CF = 0.35                  # assumed long-run CF of contracted South West REZ wind (rez treatment)
ERA5_CF_BIAS = 0.30                    # median ERA5 CF under-prediction at Australian wind farms (Palmer et al.)
PV_DC_AC = 1.30
PV_LOSS = 0.14
HUB_HEIGHT_M = 130.0
SHEAR_ALPHA = 0.14

# ---------------------------------------------------------------- IT, cooling, flexibility
FLEX_SHARE = 0.15                      # share of IT load migratable between campuses over the Spectrum-XGS fabric
PUE_BASE = 1.065                       # direct liquid cooling with dry coolers
PUE_COOL_A = 0.020
PUE_COOL_SLOPE = 0.0045                # per K above 18 C
PUE_TRIM_SLOPE = 0.012                 # per K above 32 C (mechanical trim)
PUE_WEBSITE = 1.25                     # website planning baseline, used for the named-project screen
ADIABATIC_L_PER_KWH_IT = 0.10          # adiabatic assist above 35 C only
METRO_WUE_L_PER_KWH = (0.2, 0.5)       # evaporatively assisted metropolitan comparator, range

# ---------------------------------------------------------------- supply portfolios (MW per 348.8 MW IT; scaled with IT)
PORTFOLIOS = {
    "solar_grid": dict(solar=700.0, wind=0.0, batt_mw=250.0),
    "balanced":   dict(solar=650.0, wind=550.0, batt_mw=300.0),
    "high_re":    dict(solar=850.0, wind=850.0, batt_mw=500.0),
}
BATT_HOURS = 4.0
BATT_RTE = 0.85
IMPORT_CAP_MW = 600.0                  # firm import right of the network (fixed; does not scale with IT)
EXPORT_CAP_MW = 600.0
ENGINE_COVER = 1.10                    # standby engines sized at 110% of each campus's peak facility load
# grid availability events (synthetic, fixed seed)
CAMPUS_OUTAGES_PER_Y = 1.5             # complete loss of supply to one campus, 1-12 h
REGIONAL_EVENTS_PER_Y = 0.5            # network contingency, 12-72 h, imports limited to 30%
REGIONAL_IMPORT_AVAIL = 0.30

# ---------------------------------------------------------------- emission factors
GRID_T_PER_MWH = {"NSW": 0.64, "VIC": 0.78}   # NGA location-based scope 2, 2025-26 (CER amendments)
GRID_SENS = [0.39, 0.64, 0.78, 1.00]           # 2030 illustrative (half), NSW, VIC, night-marginal brown coal
WIND_G_KWH = 12.0
PV_G_KWH = 37.0
BATT_KG_PER_KWH = 75.0
BATT_LIFE = 15.0
GAS_KG_PER_GJ = 51.53
CCGT_EFF_HHV = 0.57
CH4_KG_PER_GJ = 18.02
LEAK = 0.01
GWP_CH4 = 28.0
CCS_PENALTY = 0.15
DIESEL_KG_PER_L = 2.71
PETROL_KG_PER_L = 2.305

# ---------------------------------------------------------------- standby engines: biodiesel pilot + biogas
ENG_ELEC_EFF = 0.42                    # standby reciprocating gensets, electrical efficiency
BD_MJ_PER_L = 34.6
BD_PILOT_MIN = 0.33                    # biodiesel never below 33% of fuel energy when co-firing biogas
BD_ANNUAL_ML = 20.0                    # annual biodiesel ceiling (on-site storage refills)
UCO_ML = 2.0                           # regional used-cooking-oil purchase programme, ML/y
UCO_AUD_L = 1.25
UCO_CONV_AUD_L = 0.40
UCO_YIELD = 0.95
UCO_G_PER_MJ = 14.0
MARKET_BD_G_PER_MJ = 20.0              # purchased tallow/waste-oil biodiesel, conservative
MARKET_BD_AUD_L = 2.00
BIOGAS_STORE_DAYS = 5.0
BIOGAS_G_PER_MJ = 12.0
BIOGAS_AUD_GJ = 25.0
BIOMETHANE_UPGRADE_AUD_GJ = 12.0
CH4_MJ_PER_M3 = 35.8
# digester feedstocks (assumptions)
CRUSH_T = 185_195 + 134_950            # Murray Darling-Swan Hill winegrape crush, VIC + NSW, 2024 (Wine Australia)
MARC_SHARE = 0.15; MARC_CAPTURE = 0.30; MARC_VS = 0.30; MARC_B0 = 0.25
REJECT_T = 10_000.0; REJECT_VS = 0.10; REJECT_B0 = 0.35   # rejected fruit and vegetables, packing sheds
FOGO_T_PER_RESIDENT = 0.15; FOGO_VS = 0.25; FOGO_B0 = 0.40
GH_RESIDUE_T_PER_T = 0.25; GH_RESIDUE_VS = 0.10; GH_RESIDUE_B0 = 0.25
RAS_SLUDGE_DM_PER_FEED = 0.25; RAS_SLUDGE_VS = 0.80; RAS_SLUDGE_B0 = 0.30
FISH_OFFAL_SHARE = 0.40; FISH_OFFAL_VS = 0.30; FISH_OFFAL_B0 = 0.50
DIGESTER_KWH_TH_PER_M3_CH4 = 1.2       # digester heating, kWh_th per m3 CH4 produced

# ---------------------------------------------------------------- community covenant
PRODUCE_KG = 146.0                     # per resident-year, free (design ceiling)
SEAFOOD_KG = 46.0                      # per resident-year, free: barramundi, Murray cod, freshwater prawns
SEAFOOD_MIX = {"barramundi": 0.40, "Murray cod": 0.40, "freshwater prawns": 0.20}
GH_YIELD = 50.0                        # kg/m2-year
GH_HEAT_KWH_M2_PER_HDD = 0.25
LED_W_M2 = 50.0                        # supplemental horticultural LED (purple/red-blue), May-Aug
LED_GHI_THRESHOLD = 300.0              # lights on 06-18 local when GHI below this (dull winter hours)
RAS_KWH_PER_KG = 9.59
RAS_SET_T = 26.0
RAS_HEAT_KWH_PER_KG_PER_K = 0.30
FCR = 1.6
FEED_N = 0.072
FISH_N_RETAIN = 0.30
HH_SIZE = 2.5
HH_CONNECT = 0.20                      # share of households on low-temperature hot-water loops
DHW_MWH_HH = 2.4
SPACE_KWH_HH_PER_HDD = 3.0
DRYING_T = 20_000.0                    # t/y fresh produce dried for local growers (grapes, tomatoes, citrus peel, herbs)
DRYING_MWH_T = 1.5
DRYING_SEASON = (1, 2, 3, 4)           # Jan-Apr harvest window (months, 1-based)
DRYER_BOOSTER_SHARE = 0.10
HP_COP = 3.5
HEAT_LOSS = 0.10
RES_HEAT_GAS_BOILER_EFF = 0.85
DRY_GAS_EFF = 0.80
GAS_HEAT_SHARE = 0.60                  # share of displaced household/drying heat that would be gas

# vehicles, charging and fuel parity
VEH_PER_HH = 1.0
VEH_EV_SHARE = 0.70
VEH_EV_AUD = 40_000.0; VEH_PHEV_AUD = 35_000.0
VEH_LIFE_Y = 10.0
VEH_KM_Y = 12_000.0
EV_KWH_KM = 0.18; PHEV_KWH_KM = 0.20; PHEV_E_SHARE = 0.50; PHEV_L_100KM = 5.5
PETROL_L_100KM_DISPLACED = 9.0
CHARGER_AUD = 2_000.0
CHARGE_LOSS = 0.10
FARM_FUEL_ML = 15.0                    # enrolled Sunraysia farms' diesel switched to renewable fuel
PARITY_GAP_AUD_L = (0.25, 0.45, 0.80)
HEAT_CONNECT_AUD = 15_000.0

# ---------------------------------------------------------------- economics
PRICE_PRODUCE = (2.5, 3.5, 4.5)
PRICE_SEAFOOD = (12.0, 18.0, 24.0)     # freshwater species incl. Murray cod and prawns
PRICE_HH_HEAT = (25.0, 35.0, 45.0)     # A$/GJ
WAGE_FTE = 104_000.0
FEED_AUD_KG = 1.8
ELEC_AUD_MWH = 100.0
NET_CHARGE_AUD_MWH = 20.0
CAP_CHARGE = 0.08
FTE_PER_MW_IT = 0.25
FOOD_FTE_PER_KT = 7.44
DRY_FTE = 20.0
GAS_AUD_GJ = 13.5

# ---------------------------------------------------------------- GPU rental premium
GPU_KW = 14.3 / 8                      # DGX B200 maximum system power per GPU (NVIDIA)
GPU_UTIL = 0.70
GPU_PRICE_USD_H = {"H100": 2.88, "H200": 3.48, "B200": 6.45, "B300": 7.53}   # Silicon Data indices, 24 Oct 2026
USD_PER_AUD = 0.65
WTP_PREMIUM = 0.097                    # PwC 2024 Voice of the Consumer

# ---------------------------------------------------------------- fibre (Spectrum-XGS scale-across over dark fibre)
ROUTE_FACTOR = 1.3
FIBRE_US_PER_KM = 5.0

# ---------------------------------------------------------------- named Australian mega data-centre projects (as reported)
# (name, operator, location, state, MW as reported, MW basis, status, source key)
NAMED_PROJECTS = [
    ("Mamre Road / Kemps Creek campus (SYD4)", "AirTrunk", "Kemps Creek, western Sydney", "NSW", 1200, "1 GW, 1.2 GW peak (amended)", "Planning (amended SSD)", "aiscale"),
    ("S7 hyperscale AI campus", "NEXTDC with OpenAI", "Eastern Creek, western Sydney", "NSW", 550, "550 MW (NEXTDC); 612 MW (planning)", "MoU Dec 2025; first phase 2H 2027", "itnews_s7"),
    ("Marsden Park campus", "CDC Data Centres", "Marsden Park, north-west Sydney", "NSW", 504, "504 MW planned", "Approved Nov 2025", "rlb"),
    ("Project Atlas", "Goodman", "Eastern Creek, western Sydney", "NSW", 500, "500 MW", "Plans lodged Jan 2026", "cpm"),
    ("Laverton campus", "CDC Data Centres", "Laverton North, western Melbourne", "VIC", 400, "400 MW+ master plan", "Under construction", "aiscale_mel"),
    ("S4", "NEXTDC", "Horsley Park, western Sydney", "NSW", 365, "365 MW", "Planning and development", "aiscale"),
    ("MEL2", "AirTrunk", "north-west Melbourne", "VIC", 354, "354 MW+", "Announced Dec 2025", "aiscale_mel"),
    ("M4", "NEXTDC", "Fishermans Bend, Melbourne", "VIC", 162, "162 MW", "Approved Jan 2026", "rlb"),
    ("Southgate Melbourne", "Firmus (with CDC until Oct 2026)", "Melbourne", "VIC", 150, "150 MW planned; ~42 MW deployed", "Partnership ended Oct 2026", "dcd_firmus"),
]
