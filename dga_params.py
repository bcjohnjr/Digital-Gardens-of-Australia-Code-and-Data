"""Parameters for Digital Gardens Australia (DGA) prospective comparison.
All values are scenario assumptions unless a source is noted in the manuscript.
"""
import numpy as np

YEARS = 16
HPY = 8760
NH = YEARS * HPY  # 140,160 hours
SEED = 20261115

# ---------------------------------------------------------------- hubs
# name, state, grid, lat, lon, IT share, wind CF target (net), PV AC CF target,
# monthly mean temperature climatology (Jan..Dec, deg C), diurnal half-amplitude,
# coastal seaweed partner (name, lat, lon) or None, nuclear SMR candidate (bool)
HUBS = [
    dict(key="MUS", name="Muswellbrook (Liddell)", state="NSW", grid="NEM", lat=-32.3716, lon=150.978421,
         share=0.17, wcf=0.34, pcf=0.25, amp=7.0, wind_region="east",
         tm=[24.5, 24.0, 22.0, 18.0, 14.0, 11.0, 10.0, 11.5, 15.0, 18.5, 21.0, 23.5],
         partner=("Port Stephens kelp lease", -32.72, 152.10), smr=True, gas_heat_share=0.40),
    dict(key="LIT", name="Lithgow (Mount Piper)", state="NSW", grid="NEM", lat=-33.358087, lon=150.032036,
         share=0.12, wcf=0.33, pcf=0.23, amp=6.5, wind_region="east",
         tm=[19.5, 19.0, 17.0, 13.0, 9.5, 6.5, 5.5, 6.5, 9.5, 12.5, 15.5, 18.0],
         partner=None, smr=False, gas_heat_share=0.55),
    dict(key="TAR", name="Nanango (Tarong)", state="QLD", grid="NEM", lat=-26.783688, lon=151.915274,
         share=0.15, wcf=0.38, pcf=0.26, amp=7.0, wind_region="east",
         tm=[24.5, 24.0, 22.5, 19.5, 15.5, 12.5, 11.5, 13.0, 16.5, 19.5, 22.0, 23.5],
         partner=("Hervey Bay Asparagopsis tanks", -25.29, 152.85), smr=False, gas_heat_share=0.10),
    dict(key="CAL", name="Biloela (Callide)", state="QLD", grid="NEM", lat=-24.347222, lon=150.617115,
         share=0.13, wcf=0.37, pcf=0.27, amp=7.5, wind_region="east",
         tm=[27.5, 27.0, 25.5, 22.5, 18.5, 15.5, 14.5, 16.0, 19.5, 23.0, 25.5, 27.0],
         partner=("Gladstone Asparagopsis tanks", -23.85, 151.26), smr=False, gas_heat_share=0.10),
    dict(key="LAT", name="Latrobe Valley (Loy Yang)", state="VIC", grid="NEM", lat=-38.252414, lon=146.575334,
         share=0.16, wcf=0.35, pcf=0.20, amp=5.0, wind_region="south",
         tm=[18.5, 18.5, 16.5, 13.5, 11.0, 8.5, 8.0, 9.0, 10.5, 12.5, 14.5, 16.5],
         partner=("Corner Inlet kelp lease", -38.70, 146.47), smr=True, gas_heat_share=0.80),
    dict(key="PTA", name="Port Augusta (Northern)", state="SA", grid="NEM", lat=-32.542518, lon=137.78785,
         share=0.15, wcf=0.40, pcf=0.27, amp=6.5, wind_region="south",
         tm=[25.5, 25.5, 23.0, 19.0, 15.0, 12.0, 11.5, 13.0, 16.0, 19.0, 21.5, 23.5],
         partner=("Spencer Gulf kelp lease", -33.03, 137.58), smr=True, gas_heat_share=0.50),
    dict(key="COL", name="Collie (Muja)", state="WA", grid="SWIS", lat=-33.445875, lon=116.307528,
         share=0.12, wcf=0.42, pcf=0.24, amp=6.5, wind_region="west",
         tm=[22.0, 22.0, 20.0, 16.5, 13.5, 11.0, 10.0, 10.5, 12.0, 14.5, 17.5, 20.5],
         partner=("Geographe Bay kelp lease", -33.33, 115.64), smr=True, gas_heat_share=0.60),
]
NHUB = len(HUBS)
HUB_KEYS = [h["key"] for h in HUBS]

# Comparator: Weddell-type on-site gas campus, NT (Beetaloo Digital proposal site)
WEDDELL = dict(name="Weddell (NT) gas campus site", lat=-12.6173, lon=131.0066)

# ---------------------------------------------------------------- ERA5 resource conversion
PV_DC_AC = 1.30                          # DC/AC ratio, single-axis tracker
PV_LOSS = 0.14                           # DC system losses (soiling, mismatch, wiring, degradation mid-life)
HUB_HEIGHT_M = 130.0
SHEAR_ALPHA = 0.14                       # power-law shear 100 m -> hub height
ERA5_CF_BIAS = 0.30                      # median ERA5 capacity-factor under-prediction at 54 Australian wind farms (Palmer)

# ---------------------------------------------------------------- loads
IT_TWH = 32.861982                       # common IT electricity service, TWh/y
IT_GW = IT_TWH * 1e3 / HPY               # 3.7514 GW
FLEX_SHARE = 0.15                        # share of hub IT load migratable between hubs (inference)
# PUE model for dry-loop / direct-liquid-cooled halls (no evaporative water)
PUE_BASE = 1.065
PUE_COOL_A = 0.020                       # always-on fans/pumps
PUE_COOL_SLOPE = 0.0045                  # per K above 18 C (dry-cooler fan law region)
PUE_TRIM_SLOPE = 0.012                   # per K above 32 C (mechanical trim chillers)

# ---------------------------------------------------------------- community programme
ENROLLED = 300_000                       # design enrolment cap across seven host regions
PRODUCE_KG = 146.0
SEAFOOD_KG = 46.0
GH_YIELD = 50.0                          # kg/m2-year protected cropping
RAS_YIELD = 100.0                        # kg/m3-year
FCR = 1.6
RAS_KWH_PER_KG = 9.59                    # electricity analogue (salmon grow-out case)
RAS_SET_T = 28.0                         # barramundi culture temperature
RAS_HEAT_KWH_PER_KG_PER_K = 0.30         # kWh_th per kg fish per K of (28 - Tamb), assumption
GH_HEAT_KWH_M2_PER_HDD = 0.25            # kWh_th/m2 per K-day (base 18 C)
HH_SIZE = 2.5
HH_CONNECT = 0.20                        # share of enrolled households connected to low-temp loops
DHW_MWH_HH = 2.4                         # domestic hot water per connected household-year
SPACE_KWH_HH_PER_HDD = 3.0               # kWh_th per household per K-day (small, efficient homes)
DIGESTER_TWH = 0.010
COMMUNITY_DRYING_T = 60_000              # t/y fruit, grain, fish drying service
COMMUNITY_DRYING_MWH_T = 1.5             # MWh_th per t
DRYER_BOOSTER_SHARE = 0.10               # share of drying heat supplied by electric booster

# Heat-driven water treatment (low-temperature multi-effect distillation of mine-affected or saline water)
DESAL_M3 = 15.0e6                        # m3/y freshwater product, design
DESAL_KWH_TH_M3 = 65.0                   # thermal input at ~65-70 C
DESAL_KWH_E_M3 = 1.5                     # pumps, vacuum, pre-treatment

# Seaweed
FEEDLOT_CAPACITY = 1_794_806             # head, ALFA/MLA June 2026
ASP_COVER_SHARE = 0.25                   # share of national feedlot capacity supplied
ASP_G_PER_HEAD_DAY = 20.0                # g DM per head-day (~0.2% of DMI)
ASP_YIELD_T_HA = 25.0                    # t DW / ha-year, land-based tanks (assumption)
ASP_KWH_PER_KG = 2.5                     # pumping/aeration/CO2 dosing electricity
ASP_HEAT_KWH_PER_KG = 5.0                # tank warming, applied at southern sites only
DRY_KWH_TH_PER_KG = 3.8                  # dried product (85% -> 18.5% moisture, 80% dryer eff.)
CH4_KG_HEAD_YR = 40.0                    # feedlot enteric CH4 (assumption)
ASP_CH4_CUT = 0.50                       # central commercial efficacy (range 0.3-0.8)
GWP_CH4 = 28.0                           # AR5 GWP100, Australian NGA convention
KELP_HA_PER_SITE = 500.0
KELP_DRIED_T_HA = 3.35                   # Hasselstrom et al. 2020 midpoint (3.14-6.28)
KELP_DRIED_SHARE_WET = 0.1789
KELP_KG_CO2E_PER_T_FRESH = 55.2          # cultivation + harvest
KELP_N_KG_PER_T_DW = 16.0
KELP_KWH_PER_KG_DRIED = 0.6              # handling, pumps, cold store (assumption)

# Drones
DRONE_PARCEL_SHARE = 0.10                # share of covenant food parcels by drone
DRONE_PARCEL_KG = 2.0
DRONE_KWH_PER_DELIVERY = 0.12            # incl. charger losses, ~10 km round trip
DRONE_DELIV_PER_DAY = 20
DRONE_DAYS = 300
DRONE_INSPECT_PER_HUB = 20
DRONE_INSPECT_KWH_YR = 900.0             # per inspection drone
DRONE_AG_PER_HUB = 10
DRONE_AG_KWH_YR = 2500.0                 # spraying/monitoring multirotor
VAN_L_PER_KM = 0.11                      # diesel van displaced
VAN_KM_PER_DELIVERY = 1.2

# Electrified highways (overhead catenary, eHighway type)
ERS_CORRIDORS = [
    # name, route km, heavy-vehicle AADT (two-way, screening), hub allocation {hub: share}
    ("Hunter: Muswellbrook-Newcastle port", 125, 3000, {"MUS": 1.0},
     [(150.98, -32.37), (151.30, -32.55), (151.78, -32.92)]),
    ("Central West: Lithgow-Sydney", 140, 2000, {"LIT": 1.0},
     [(150.03, -33.36), (150.31, -33.72), (150.90, -33.80), (151.05, -33.85)]),
    ("Hume: Sydney-Melbourne", 880, 5500, {"MUS": 0.30, "LIT": 0.30, "LAT": 0.40},
     [(150.85, -33.95), (150.60, -34.45), (149.70, -34.75), (148.90, -35.05),
      (147.65, -35.40), (147.10, -35.98), (146.40, -36.30), (145.60, -36.75),
      (145.10, -37.40), (144.95, -37.75)]),
    ("Gippsland: Latrobe Valley-Melbourne", 150, 3500, {"LAT": 1.0},
     [(146.58, -38.25), (146.10, -38.15), (145.50, -38.05), (145.00, -37.85)]),
    ("Brisbane Valley: Tarong-Brisbane", 180, 1200, {"TAR": 1.0},
     [(151.90, -26.67), (152.40, -27.05), (152.70, -27.45), (153.02, -27.47)]),
    ("Dawson: Biloela-Gladstone port", 120, 900, {"CAL": 1.0},
     [(150.51, -24.40), (150.90, -24.10), (151.26, -23.85)]),
    ("Augusta-Port Wakefield: Port Augusta-Adelaide", 310, 1800, {"PTA": 1.0},
     [(137.77, -32.49), (138.00, -33.10), (138.20, -33.85), (138.60, -34.93)]),
    ("Coalfields-Forrest: Collie-Bunbury-Perth", 235, 2200, {"COL": 1.0},
     [(116.15, -33.36), (115.64, -33.33), (115.75, -32.70), (115.86, -31.95)]),
]
ERS_SHARE = 0.25                         # share of corridor HV-km powered from catenary (central)
ERS_KWH_PER_KM = 1.5                     # at pantograph
ERS_LOSS = 0.05
TRUCK_L_PER_KM = 0.50                    # diesel prime mover displaced
DIESEL_KG_PER_L = 2.71                   # NGA diesel ~70.2 kg/GJ x 38.6 GJ/kL
ERS_CAPEX_AUD_M_PER_KM = (2.5, 4.2)      # ITF EUR1.5-2.5 M/km two lanes, converted

EV_CHARGE_GWH = 30.0                     # legacy value; replaced by the vehicle programme below
# ---------------------------------------------------------------- community vehicle & fuel-parity programme
VEH_PER_HH = 1.0                         # one free EV or plug-in hybrid per enrolled household
VEH_EV_SHARE = 0.70                      # 70% battery-electric, 30% plug-in hybrid
VEH_EV_AUD = 40_000.0; VEH_PHEV_AUD = 35_000.0
VEH_LIFE_Y = 10.0
VEH_KM_Y = 12_000.0
EV_KWH_KM = 0.18; PHEV_KWH_KM = 0.20; PHEV_E_SHARE = 0.50; PHEV_L_100KM = 5.5
CHARGER_AUD = 2_000.0                    # home charger installed
CHARGE_LOSS = 0.10
FARM_FUEL_ML = 60.0                      # enrolled farms' diesel switched to renewable diesel / biodiesel
PARITY_GAP_AUD_L = (0.25, 0.45, 0.80)    # renewable minus fossil price after fuel-tax credits, A$/L
HEAT_CONNECT_AUD = 15_000.0              # per connected dwelling (low-temperature loop branch + HIU)
ASP_N_DW = 0.04                          # Asparagopsis tissue N, share of dry weight (scrubber N uptake)
FEED_N = 0.072                           # fish feed N (45% protein / 6.25)
FISH_N_RETAIN = 0.30                     # share of feed N retained in fish
# ---------------------------------------------------------------- GPU rental premium
GPU_KW = 14.3 / 8                        # DGX B200 maximum system power per GPU, kW (conservative: fewer GPUs per MW)
GPU_UTIL = 0.70                          # share of installed GPU-hours sold
GPU_PRICE_USD_H = {"H100": 2.88, "H200": 3.48, "B200": 6.45, "B300": 7.53}   # Silicon Data indices, 24 Oct 2026
USD_PER_AUD = 0.65
WTP_PREMIUM = 0.097                      # PwC 2024 Voice of the Consumer: average willingness to pay

# ---------------------------------------------------------------- heat pumps
HP_COP = 3.5
HEAT_LOSS = 0.10
DLC_DIRECT_SHARE = 0.60                  # sensitivity: share of drying/greenhouse heat met directly by 55-60 C DLC return

# ---------------------------------------------------------------- portfolios (per hub)
# wind GW, solar GW, battery GWh (4-h), HVO engine MW, import MW, export MW
PORTFOLIOS = {
    "reference": dict(wind=0.70, solar=1.00, batt=1.0, hvo=260, imp=250, exp=400, smr=0.0),
    "enlarged":  dict(wind=1.25, solar=1.60, batt=4.5, hvo=560, imp=450, exp=700, smr=0.0),
    "enl_smr":   dict(wind=1.25, solar=1.60, batt=4.5, hvo=560, imp=450, exp=700, smr=1.0),
}
# portfolio scale is applied per hub in proportion to hub IT share * 7 (i.e., values are for an
# average hub; hub value = value * share * NHUB)
SMR_UNIT_MW = 300.0
SMR_UNITS_PER_CANDIDATE = 2              # 4 candidate hubs x 2 = 8 units = 2.4 GW
SMR_FOR = 0.03
SMR_REFUEL_DAYS = 30
SMR_CYCLE_MONTHS = 24

# ---------------------------------------------------------------- dual-fuel engines: biodiesel pilot + biogas
# Variable names keep the historical "HVO_" prefix so that downstream code is unchanged; the fuel is
# now waste-oil biodiesel (B100) co-combusted with digester biogas in dual-fuel reciprocating engines.
HVO_ANNUAL_ML = 800.0                    # fleet biodiesel supply ceiling, ML/y (feedstock-limited; see text)
HVO_MJ_PER_L = 34.6                      # NGA biodiesel energy content, GJ/kL
HVO_ELEC_EFF = 0.48                      # large dual-fuel reciprocating engine, electrical efficiency (LHV)
BD_PILOT_MIN = 0.33                      # biodiesel never below 33% of fuel energy; biogas up to 67%
UCO_ML = 60.0                            # used-cooking-oil purchase programme, ML/y collected (~half national UCO)
UCO_AUD_L = 1.25                         # A$/L paid to restaurants, food processors, councils
UCO_CONV_AUD_L = 0.40                    # A$/L biodiesel transesterification cost
UCO_YIELD = 0.95                         # L biodiesel per L UCO
UCO_G_PER_MJ = 14.0                      # EU RED Annex V default, waste vegetable/animal oil biodiesel
TALLOW_G_PER_MJ = 20.0                   # conservative allowance for rendered tallow biodiesel
TALLOW_BD_AUD_L = 2.00                   # A$/L delivered B100 from tallow (market purchase)
HVO_G_PER_MJ = 17.0                      # fleet-average placeholder; recomputed from UCO/tallow mix in model
HVO_AUD_PER_L = 1.90                     # fleet-average placeholder; recomputed in model
BIOGAS_STORE_DAYS = 5.0                  # days of digester output held in low-pressure gas holders per hub
BIOGAS_G_PER_MJ = 12.0                   # incl. digester and engine methane slip (assumption)
BIOGAS_AUD_GJ = 25.0                     # levelised digester + storage cost per GJ biogas
BIOMETHANE_UPGRADE_AUD_GJ = 12.0         # upgrading surplus biogas to farm vehicle fuel
# digester feedstocks: (label, tonnes or head basis, m3 CH4 per unit, note)
CH4_MJ_PER_M3 = 35.8
FEEDLOT_VS_KG_HEAD_DAY = 2.0             # volatile solids excreted
FEEDLOT_MANURE_CAPTURE = 0.50            # share recovered fresh from pads / effluent ponds
FEEDLOT_B0 = 0.15                        # m3 CH4 per kg VS for pad-scraped manure
FOGO_T_PER_RESIDENT = 0.15               # food & garden organics collected, t/resident-year
FOGO_VS = 0.25; FOGO_B0 = 0.40
GH_RESIDUE_T_PER_T = 0.25; GH_RESIDUE_VS = 0.10; GH_RESIDUE_B0 = 0.25
RAS_SLUDGE_DM_PER_FEED = 0.25; RAS_SLUDGE_VS = 0.80; RAS_SLUDGE_B0 = 0.30
FISH_OFFAL_SHARE = 0.40; FISH_OFFAL_VS = 0.30; FISH_OFFAL_B0 = 0.50
BATT_RTE = 0.85
FIRM_RESTRICT_MW = 250.0                 # per-site cap in restricted-firm stress

# ---------------------------------------------------------------- carbon factors
WIND_G_KWH = 12.0                        # UNECE (2021) onshore wind
PV_G_KWH = 37.0                          # UNECE (2021) poly-Si ground-mounted; IPCC AR5 median 48 as sensitivity
NUC_G_KWH = 12.0
BATT_KG_PER_KWH = 75.0
BATT_LIFE = 15.0
GRID_T_PER_MWH = {"NSW": 0.66, "QLD": 0.71, "VIC": 0.77, "SA": 0.23, "WA": 0.50}  # WA assumed
GAS_KG_PER_GJ = 51.53                    # NGA natural gas, scope 1, GCV basis
CCGT_EFF_HHV = 0.57
CH4_KG_PER_GJ = 18.02                    # methane content per GJ HHV
LEAK = 0.01
CCS_PENALTY = 0.15
GAS_AUD_GJ = (10.0, 13.5)                # ACCC east-coast producer offers ~A$13.5/GJ; Beetaloo ~10-12
RES_HEAT_GAS_BOILER_EFF = 0.85
DRY_GAS_EFF = 0.80

# water
WUE_CASES = [0.0, 0.2, 0.5]              # L/kWh IT
GAL_TO_M3 = 0.003785411784
NREL_GAL_MWH = {"ccgt_dry": 2, "ccgt_tower": 198, "ccs_tower": 378, "nuclear_tower": 672}

# economics (A$, illustrative)
PRICE_PRODUCE = (2.5, 3.5, 4.5)          # A$/kg
PRICE_SEAFOOD = (10.0, 14.0, 18.0)       # A$/kg
PRICE_HH_HEAT = (25.0, 35.0, 45.0)       # A$/GJ
WAGE_FTE = 104_000.0                     # A$ incl. on-costs
FEED_AUD_KG = 1.8
ELEC_AUD_MWH = 100.0
NET_CHARGE_AUD_MWH = 20.0
CAP_CHARGE = 0.08
FIRM_CAPEX_AUD_KW = (1400.0, 3300.0)
SMR_CAPEX_AUD_KW = 19_200.0              # Darlington C$20.9bn/1.2 GW ~C$17.4k/kW, x1.10 A$/C$
FTE_PER_GW_IT = 250.0
FOOD_FTE_PER_KT = 7.44
KELP_FTE_PER_HA = 0.20
ASP_FTE_PER_HA = 2.0
ERS_FTE_PER_KM = 0.05
DRONE_FTE_PER_DRONE = 0.08
SMR_FTE_PER_UNIT = 100.0
