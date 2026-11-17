"""Figures and maps. Run: python dga_figures.py  (needs rez, palmer and raw results in this folder)"""
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyBboxPatch
from matplotlib.lines import Line2D

import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True          # keep the folder flat: no __pycache__
sys.path.insert(0, HERE)
import dga_params as P
J = lambda name: os.path.join(HERE, name)
N = json.load(open(J("dga_numbers_rez.json")))
R = json.load(open(J("dga_results_rez.json")))
AUS = json.load(open(J("dga_aus_outline.json")))

C = dict(blue="#2a78d6", orange="#eb6834", aqua="#1baf7a", yellow="#eda100", magenta="#e87ba4",
         green="#008300", violet="#6250d6", red="#e34948")
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 400})


def save(fig, name):
    fig.savefig(J(f"{name}.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def note(fig, text):
    fig.text(0.01, -0.02, text, fontsize=7, color=INK2, ha="left", va="top", wrap=True)


# ------------------------------------------------------------------ map helpers
BORDERS = [
    [(129.0, -14.88), (129.0, -31.69)],
    [(129.0, -26.0), (141.0, -26.0)],
    [(138.0, -26.0), (138.0, -16.54)],
    [(141.0, -26.0), (141.0, -34.0), (140.96, -38.06)],
    [(141.0, -29.0), (148.9, -29.0), (149.6, -28.6), (150.9, -28.6), (151.5, -28.95), (152.0, -28.55), (153.2, -28.25), (153.55, -28.17)],
    [(140.96, -33.98), (142.0, -34.2), (143.3, -34.8), (144.6, -35.6), (146.0, -35.95), (147.0, -36.0), (148.2, -36.8), (149.98, -37.50)],
]
STATE_LAB = {"WA": (122.0, -26.0), "NT": (133.5, -20.0), "SA": (135.0, -29.5), "QLD": (144.5, -22.5),
             "NSW": (146.0, -32.0), "VIC": (143.5, -37.0), "TAS": (146.5, -42.0)}


def base_map(ax, extent=(112, 155, -44.5, -9.5), shade=True):
    lat0 = -27.0
    for poly in AUS["coordinates"]:
        ring = np.array(poly[0])
        ax.add_patch(Polygon(ring, closed=True, facecolor="#f3f2ee", edgecolor="#9b9a95", lw=0.7, zorder=1))
    for b in BORDERS:
        b = np.array(b); ax.plot(b[:, 0], b[:, 1], color="#bdbcb6", lw=0.6, ls=(0, (4, 2)), zorder=2)
    for k, (x, y) in STATE_LAB.items():
        if extent[0] <= x <= extent[1] and extent[2] <= y <= extent[3]:
            ax.text(x, y, k, color="#a3a29c", fontsize=8, ha="center", va="center", zorder=2, fontweight="bold")
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(1 / math.cos(math.radians(lat0)))
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])


HUBXY = {h["key"]: (h["lon"], h["lat"]) for h in P.HUBS}
LABOFF = {"MUS": (1.2, 0.9), "LIT": (1.4, -1.5), "TAR": (1.3, -0.2), "CAL": (1.3, 0.4), "LAT": (0.6, -1.6),
          "PTA": (-1.0, 1.6), "COL": (-0.4, 1.6)}

# ------------------------------------------------------------------ Figure 1: network map
fig, ax = plt.subplots(figsize=(7.2, 6.0))
base_map(ax)
links = [("COL", "PTA"), ("PTA", "LAT"), ("PTA", "LIT"), ("LAT", "LIT"), ("LIT", "MUS"), ("MUS", "TAR"), ("TAR", "CAL"), ("PTA", "TAR")]
for a, b in links:
    (x1, y1), (x2, y2) = HUBXY[a], HUBXY[b]
    ax.plot([x1, x2], [y1, y2], color=C["violet"], lw=1.4, alpha=0.75, zorder=3, solid_capstyle="round")
for i, hb in enumerate(P.HUBS):
    x, y = hb["lon"], hb["lat"]
    mw = R["IT_mw"][i]
    ax.scatter([x], [y], s=mw / 2.2, color=C["blue"], edgecolor="white", lw=1.2, zorder=5)
    if hb["smr"]:
        ax.scatter([x + 0.55], [y + 0.55], marker="^", s=55, color=C["red"], edgecolor="white", lw=0.8, zorder=6)
    dx, dy = LABOFF[hb["key"]]
    ax.annotate(f"{hb['name']}\nIT {mw:,.0f} MW · wind {N['wind_cf'][i]*100:.0f}% · PV {N['pv_cf'][i]*100:.0f}%",
                (x, y), (x + dx, y + dy), fontsize=6.6, color=INK, ha="left" if dx > 0 else "right", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), zorder=7)
wx, wy = P.WEDDELL["lon"], P.WEDDELL["lat"]
ax.scatter([wx], [wy], marker="s", s=70, color=C["orange"], edgecolor="white", lw=1, zorder=6)
ax.annotate("Weddell, NT: proposed on-site\ngas-fired AI campus (comparator)", (wx, wy), (wx + 2.2, wy - 1.6), fontsize=6.8,
            color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
ax.text(113.2, -36.4, "SWIS\n(isolated WA grid)", fontsize=7, color=INK2)
ax.text(145.2, -27.4, "NEM", fontsize=8, color=INK2, fontweight="bold")
leg = [Line2D([0], [0], marker="o", color="w", markerfacecolor=C["blue"], markersize=9, label="DGA hub (area ∝ IT load)"),
       Line2D([0], [0], marker="^", color="w", markerfacecolor=C["red"], markersize=8, label="Hypothetical 2 × 300 MW SMR site"),
       Line2D([0], [0], color=C["violet"], lw=1.6, label="Inter-hub fibre path (schematic)"),
       Line2D([0], [0], marker="s", color="w", markerfacecolor=C["orange"], markersize=8, label="Gas-campus comparator site")]
ax.legend(handles=leg, loc="lower left", fontsize=7, bbox_to_anchor=(0.0, 0.0))
ax.set_title("Digital Gardens Australia: seven coal-transition hubs and comparator site", loc="left")
note(fig, "Outline: Natural Earth 1:110m (public domain); state borders schematic. Capacity factors are 2010–2025 means from ERA5 "
          "reanalysis; wind is scaled to regional wind-farm targets (central siting case), PV is modelled directly from ERA5 irradiance. SMR sites follow 2024 retiring-coal site proposals; "
          "nuclear power generation is currently prohibited under Commonwealth law.")
save(fig, "fig1_network_map")

# ------------------------------------------------------------------ Figure 2: community, seaweed and mobility map
fig, axs = plt.subplots(1, 2, figsize=(7.6, 5.0), gridspec_kw=dict(width_ratios=[2.25, 1]))
mx = max(c[2] for c in P.ERS_CORRIDORS)
lab = {"Hunter: Muswellbrook-Newcastle port": (153.3, -31.6), "Hume: Sydney-Melbourne": (147.6, -37.2),
       "Augusta-Port Wakefield: Port Augusta-Adelaide": (136.3, -35.3), "Coalfields-Forrest: Collie-Bunbury-Perth": (117.3, -32.2),
       "Gippsland: Latrobe Valley-Melbourne": (147.9, -39.3), "Dawson: Biloela-Gladstone port": (153.4, -23.4),
       "Brisbane Valley: Tarong-Brisbane": (154.0, -27.9), "Central West: Lithgow-Sydney": (148.3, -33.9)}
for ax, ext in [(axs[0], (134.0, 155.5, -40.2, -22.3)), (axs[1], (113.6, 119.2, -35.4, -30.9))]:
    base_map(ax, extent=ext)
    for name, km, aadt, alloc, path in P.ERS_CORRIDORS:
        p = np.array(path)
        ax.plot(p[:, 0], p[:, 1], color=C["orange"], lw=1.2 + 4.0 * aadt / mx, alpha=0.9, zorder=3, solid_capstyle="round")
    for i, hb in enumerate(P.HUBS):
        x, y = hb["lon"], hb["lat"]
        ax.add_patch(Circle((x, y), 0.9, facecolor=C["aqua"], alpha=0.16, edgecolor=C["aqua"], lw=0.6, zorder=3))
        ax.scatter([x], [y], s=34, color=C["blue"], edgecolor="white", lw=0.8, zorder=5)
        if hb["partner"]:
            nm, py, px = hb["partner"]
            col = C["magenta"] if "Asparagopsis" in nm else C["green"]
            ax.scatter([px], [py], marker="D", s=40, color=col, edgecolor="white", lw=0.7, zorder=6)
            ax.plot([x, px], [y, py], color=col, lw=0.8, ls=":", zorder=4)
    for r in N["ers_rows"]:
        x, y = lab[r["corridor"]]
        if ext[0] <= x <= ext[1] and ext[2] <= y <= ext[3]:
            ax.text(x, y, f"{r['corridor'].split(':')[0]}\n{r['gwh']:.0f} GWh/y", fontsize=6.2, color=INK2, ha="center", va="center", zorder=7)
ax = axs[0]
ax.add_patch(Circle((150.9, -27.6), 1.1, facecolor="none", edgecolor=C["yellow"], lw=1.3, ls="--", zorder=4))
ax.text(147.9, -27.2, "Darling Downs\nfeedlot belt\n(indicative)", fontsize=6.2, color=INK2, ha="center")
for k in ["MUS", "LIT", "TAR", "CAL", "LAT", "PTA"]:
    x, y = HUBXY[k]
    off = {"MUS": (-0.3, 0.75), "LIT": (-1.4, 0.2), "TAR": (-1.4, 0.4), "CAL": (-1.4, 0.0), "LAT": (-1.0, 0.75), "PTA": (0.5, 0.7)}[k]
    ax.text(x + off[0], y + off[1], k, fontsize=7, fontweight="bold", color=C["blue"], ha="center")
axs[1].text(116.15 + 0.15, -33.36 + 0.55, "COL", fontsize=7, fontweight="bold", color=C["blue"])
ax.set_title("A  Eastern and southern hubs", loc="left")
axs[1].set_title("B  South-west WA", loc="left")
leg = [Line2D([0], [0], color=C["orange"], lw=3, label="Catenary electric road (width ∝ heavy-vehicle AADT)"),
       Line2D([0], [0], marker="D", color="w", markerfacecolor=C["green"], markersize=7, label="Kelp longline lease, 500 ha"),
       Line2D([0], [0], marker="D", color="w", markerfacecolor=C["magenta"], markersize=7, label="Land-based Asparagopsis tanks"),
       Line2D([0], [0], marker="o", color="w", markerfacecolor=C["aqua"], alpha=0.5, markersize=11, label="~100 km drone / cold-chain service area"),
       Line2D([0], [0], marker="o", color="w", markerfacecolor=C["blue"], markersize=6, label="DGA hub")]
fig.legend(handles=leg, loc="lower center", fontsize=6.8, ncol=3, bbox_to_anchor=(0.5, -0.04))
fig.suptitle("Community layer: electric roads, seaweed farms and drone service areas", x=0.01, ha="left", fontweight="bold", fontsize=10)
fig.text(0.01, -0.09, f"Corridor energy assumes {P.ERS_SHARE*100:.0f}% of corridor heavy-vehicle km on catenary at {P.ERS_KWH_PER_KM} kWh/km; "
          "AADT values are screening assumptions pending state traffic counts. Lease and tank locations are illustrative, "
          "not identified or licensed sites. Outline: Natural Earth 1:110m.", fontsize=7, color=INK2, wrap=True)
fig.tight_layout(rect=[0, 0, 1, 0.95])
save(fig, "fig2_community_map")

# ------------------------------------------------------------------ Figure 3: carbon
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
ax = axs[0]
sym = N["sym_ext"]
labels = ["DGA\nenlarged", "DGA +\nSMR", "Gas\nunabated", "Gas\n90% CCS", "Gas\n95% CCS"]
x = np.arange(len(sym)); w = 0.38
gross = [s["gross"] for s in sym]; net = [s["net"] for s in sym]
b1 = ax.bar(x - w / 2 - 0.01, gross, w, color=C["blue"], label="Gross partial", zorder=3)
b2 = ax.bar(x + w / 2 + 0.01, net, w, color=C["aqua"], label="Net after equal credits", zorder=3)
ax.set_yscale("log"); ax.set_ylim(0.3, 25)
for i in range(len(sym)):
    ax.text(x[i] - w / 2, gross[i] * 1.08, f"{gross[i]:.2f}", ha="center", fontsize=6.5, color=INK)
    ax.text(x[i] + w / 2, net[i] * 1.08, f"{net[i]:.2f}", ha="center", fontsize=6.5, color=INK)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
ax.set_ylabel("Mt CO₂e per year (log scale)")
ax.set_title("A  Extended service, 37.84 TWh/y", loc="left")
ax.legend(fontsize=7, loc="upper right")
ax = axs[1]
gt = [r for r in N["gas_table"] if r["basis"] == "ext"]
lab2 = ["No CCS", "90% CCS", "95% CCS"]
co2 = [r["co2"] for r in gt]; ch4 = [r["ch4"] for r in gt]
xx = np.arange(3)
ax.bar(xx, co2, 0.55, color=C["orange"], label="Direct CO₂", zorder=3)
ax.bar(xx, ch4, 0.55, bottom=np.array(co2) + 0.0, color=C["yellow"], label="Upstream CH₄ (1% leak)", zorder=3,
       edgecolor="white", linewidth=1.5)
for i in range(3):
    ax.text(xx[i], co2[i] + ch4[i] + 0.25, f"{co2[i]+ch4[i]:.2f}", ha="center", fontsize=7)
ax.set_xticks(xx); ax.set_xticklabels(lab2)
ax.set_title("B  Gas-campus components", loc="left"); ax.legend(fontsize=7)
note(fig, f"Equal fossil-displacement credit of {N['cred_ext']:.3f} Mt/y (household and drying heat, catenary freight, drone parcels) "
          "applied to every case. Inventories are partial and not lifecycle-harmonised.")
fig.tight_layout()
save(fig, "fig3_carbon")

# ------------------------------------------------------------------ Figure 4: heat cascade
hs = np.load(J("dga_hourly_rez.npz"))
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.5), gridspec_kw=dict(width_ratios=[1, 1.4]))
ax = axs[0]
parts = N["heat_parts"]
order = ["water_treatment", "greenhouse", "residential", "drying", "aquaculture", "seaweed", "digester"]
names = {"water_treatment": "Thermal water treatment", "greenhouse": "Glasshouses", "residential": "Household heat/DHW",
         "drying": "Community drying", "aquaculture": "Barramundi RAS", "seaweed": "Seaweed drying/tanks", "digester": "Digester"}
cols = [C["blue"], C["green"], C["orange"], C["yellow"], C["aqua"], C["magenta"], C["violet"]]
bottom = 0
for k, c in zip(order, cols):
    v = parts[k]
    ax.bar([0], [v], 0.6, bottom=bottom, color=c, edgecolor="white", linewidth=1.2, zorder=3, label=f"{names[k]} {v:.3f}")
    bottom += v
ax.set_xlim(-0.6, 1.9); ax.set_ylim(0, 2.0); ax.set_xticks([0]); ax.set_xticklabels(["Delivered heat"])
ax.set_ylabel("TWh per year")
ax.set_title("A  Full-network heat uses", loc="left")
ax.legend(fontsize=6.4, loc="upper right", bbox_to_anchor=(1.12, 1.0))
ax.text(0, bottom + 0.04, f"{bottom:.2f} TWh delivered\n= {N['heat_util_share']*100:.1f}% of facility heat", ha="center", fontsize=6.8)
ax = axs[1]
D = hs["D_tot"].sum(0)  # MW_th
month_idx = np.searchsorted(np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]), (np.arange(len(D)) // 24) % 365, side="right")
Dm = np.array([D[month_idx == m].mean() for m in range(12)])
T = hs["T"]
hddm = []
for i in range(7):
    hddm.append([np.clip(18 - T[i][month_idx == m], 0, None).mean() for m in range(12)])
ax.plot(range(12), Dm, color=C["orange"], lw=2, marker="o", ms=4, label="Hourly-mean heat demand, all hubs (MWth)")
ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND"))
ax.set_ylabel("MW thermal (mean)")
ax.set_ylim(0, max(Dm) * 1.25)
ax.set_title("B  Seasonal heat demand (ERA5 2010–2025)", loc="left")
ax.axhline(N["E_fac"] * 1e6 / 8760 * 0.0 + Dm.mean(), color=MUTED, lw=0.8, ls="--")
ax.text(0.2, Dm.mean() * 1.04, "annual mean", fontsize=6.5, color=INK2)
ax.legend(fontsize=6.8, loc="lower left")
note(fig, "Facility heat-equivalent is ~4.1 GW continuously; delivered heat is bounded by local customers, not by heat availability. "
          "Heat delivered via heat pumps (COP 3.5, 10% network loss) or, in sensitivity, directly from 55–60 °C liquid-cooling return.")
fig.tight_layout()
save(fig, "fig4_heat_cascade")

# ------------------------------------------------------------------ Figure 5: economics
fig, ax = plt.subplots(figsize=(7.0, 3.4))
E = N["econ"]
x = np.arange(3); w = 0.26
ax.bar(x - w - 0.01, [e["final"] for e in E], w, color=C["aqua"], label="Final in-kind value", zorder=3)
ax.bar(x, [e["opcost"] for e in E], w, color=C["orange"], label="Selected operating costs", zorder=3)
ax.bar(x + w + 0.01, [e["opcost"] + e["capchg"] for e in E], w, color=C["violet"], label="Operating + selected capital charges", zorder=3)
for i, e in enumerate(E):
    ax.text(x[i], max(e["final"], e["opcost"] + e["capchg"]) + 22, f"Δ op {e['op_diff']:+.0f} · Δ with capital {e['diff_with_cap']:+.0f}",
            ha="center", fontsize=6.8, color=INK)
ax.set_xticks(x); ax.set_xticklabels(["Low prices", "Central", "High prices"])
ax.set_ylabel("A$ million per year"); ax.set_ylim(0, 640)
ax.legend(fontsize=7, loc="upper left", ncol=3)
ax.set_title("Community final services versus selected costs (partial, not project NPV)", loc="left")
note(fig, "Intermediate heat for glasshouses, RAS, drying, seaweed and water treatment is not valued separately to avoid double counting. "
          "Renewable-fuel, trade, ERS and SMR costs are reported in separate ledgers.")
save(fig, "fig5_economics")

# ------------------------------------------------------------------ Figure 6: adequacy
fig, ax = plt.subplots(figsize=(7.2, 3.4))
rows = N["adequacy"]
scn = ["central", "wind_minus10", "pv_minus10", "half_access", "firm_restricted", "combined_adverse"]
lab = ["Central", "Wind −10%", "PV −10%", "Grid ×0.5", f"Firm ≤{P.FIRM_RESTRICT_MW:.0f} MW", "Combined\nadverse"]
x = np.arange(len(scn)); w = 0.27
for k, (pf, col, nm) in enumerate([("reference", C["yellow"], "Reference"), ("enlarged", C["blue"], "Enlarged"),
                                    ("enl_smr", C["red"], "Enlarged + 2.4 GW SMR")]):
    vals = [next(r for r in rows if r["scenario"] == s)[pf]["uns"] for s in scn]
    ax.bar(x + (k - 1) * (w + 0.01), vals, w, color=col, label=nm, zorder=3)
    for i, v in enumerate(vals):
        ax.text(x[i] + (k - 1) * (w + 0.01), v + 1.0, f"{v:.1f}" if v >= 0.05 else "0", ha="center", fontsize=6.3)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=7.5)
ax.set_ylabel("Unserved TWh, 2010–2025")
ax.legend(fontsize=7)
ax.set_title("Resource adequacy with the full extended community load", loc="left")
note(fig, "Pooled hub dispatch with 15% migratable inference load; not a security-constrained AC or N−1 study.")
save(fig, "fig6_adequacy")

# ------------------------------------------------------------------ Figure 7: heat-service sensitivity
fig, ax = plt.subplots(figsize=(6.6, 3.3))
hc = N["heat_cases"][::-1]
xl = ["No network", "50% connected", "Plant 1.0×", "Full network"]
ax.plot(range(4), [h["dg_net"] for h in hc], color=C["blue"], marker="o", lw=2, ms=6, label="Digital Gardens Australia")
ax.plot(range(4), [h["gas95_net"] for h in hc], color=C["orange"], marker="s", lw=2, ms=6, label="Gas campus, 95% CCS")
for i, h in enumerate(hc):
    ax.text(i, h["dg_net"] - 0.016, f"{h['dg_net']:.3f}", ha="center", va="top", fontsize=6.8)
    ax.text(i, h["gas95_net"] + 0.010, f"{h['gas95_net']:.3f}", ha="center", va="bottom", fontsize=6.8)
ax.set_xticks(range(4)); ax.set_xticklabels(xl)
ax.set_ylabel("Partial net Mt CO₂e/y (core service)")
_v = [h["dg_net"] for h in hc] + [h["gas95_net"] for h in hc]; ax.set_ylim(min(_v) - 0.06, max(_v) + 0.05)
ax.legend(fontsize=7.5, loc="upper right")
ax.set_title("Heat-service coupling: same credit for both designs", loc="left")
save(fig, "fig7_heat_sensitivity")

# ------------------------------------------------------------------ Figure 8: dispatch window
tr = np.load(J("dga_trace_rez.npz"))
names = list(tr["names"])
j = names.index("enlarged|central")
load = tr["load"][j]
win = 24 * 10
roll = np.convolve(tr["wind"][j], np.ones(win) / win, mode="valid")
start = int(np.argmin(roll[: len(roll) - win]))
s = slice(start, start + win)
hrs = np.arange(win) / 24
stack = [("wind", "Wind", C["blue"]), ("pv", "Solar PV", C["yellow"]), ("bdis", "Battery discharge", C["aqua"]),
         ("hvo", "Biodiesel-biogas engines", C["orange"]), ("imp", "Grid imports", C["violet"])]
fig, ax = plt.subplots(figsize=(7.4, 3.4))
bot = np.zeros(win)
for k, nm, col in stack:
    v = tr[k][j][s] / 1e3
    ax.fill_between(hrs, bot, bot + v, color=col, lw=0, label=nm, step="mid")
    bot = bot + v
ax.plot(hrs, load[s] / 1e3, color=INK, lw=1.2, label="Load (incl. community & ERS)")
ax.set_xlabel("Days into window"); ax.set_ylabel("GW")
EWts = np.load(J("dga_era5_weather.npz"))["ts"]
yr = int(str(EWts[start])[:4]); d0 = (start % 8760) // 24
win_label = f"{str(EWts[start])[:10]} to {str(EWts[start + win - 1])[:10]}"
ax.set_title(f"Lowest-wind 10 days in 2010–2025 ({win_label} UTC), enlarged central case", loc="left")
ax.legend(fontsize=6.8, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.16))
ax.set_ylim(0, max(bot.max(), (load[s] / 1e3).max()) * 1.12)
fig.text(0.01, -0.12, "Supply stacked above the load line is battery charging, export or curtailment. Historical ERA5 weather; wind scaled to regional wind-farm targets.", fontsize=7, color=INK2)
save(fig, "fig8_dispatch_window")
N_extra = dict(win_year=int(yr), win_day=int(d0), win_label=win_label, win_wind_mean_gw=float(tr["wind"][j][s].mean() / 1e3),
               win_hvo_mean_gw=float(tr["hvo"][j][s].mean() / 1e3), win_load_mean_gw=float(load[s].mean() / 1e3),
               win_imp_mean_gw=float(tr["imp"][j][s].mean() / 1e3), win_pv_mean_gw=float(tr["pv"][j][s].mean() / 1e3),
               win_bdis_mean_gw=float(tr["bdis"][j][s].mean() / 1e3))

# ------------------------------------------------------------------ Figure 9: mobility and seaweed
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw=dict(width_ratios=[1.5, 1]))
ax = axs[0]
rows = sorted(N["ers_rows"], key=lambda r: r["gwh"])
yy = np.arange(len(rows))
ax.barh(yy, [r["gwh"] for r in rows], 0.6, color=C["orange"], zorder=3)
for i, r in enumerate(rows):
    ax.text(r["gwh"] + 8, yy[i], f"{r['gwh']:.0f} GWh · {r['co2_kt']:.0f} kt CO₂ avoided", va="center", fontsize=6.3)
ax.set_yticks(yy); ax.set_yticklabels([r["corridor"].split(":")[0] + f" ({r['km']} km)" for r in rows], fontsize=7)
ax.set_xlim(0, 1050); ax.set_xlabel("Catenary electricity, GWh/y")
ax.set_title("A  Electric-road corridors", loc="left")
ax = axs[1]
sw = N["seaweed"]
cats = ["Asparagopsis\n(t DW/y)", "Kelp, dried\n(t/y)"]
vals = [sw["asp_t"], sw["kelp_t"]]
ax.bar([0, 1], vals, 0.55, color=[C["magenta"], C["green"]], zorder=3)
ax.errorbar([1], [sw["kelp_t"]], yerr=[[sw["kelp_t"] - sw["kelp_t_lo"]], [sw["kelp_t_hi"] - sw["kelp_t"]]], color=INK, capsize=4, lw=1)
for i, v in enumerate(vals):
    ax.text(i, v * 0.5, f"{v:,.0f}", ha="center", color="white", fontsize=7.5, fontweight="bold")
ax.set_xticks([0, 1]); ax.set_xticklabels(cats, fontsize=7.5)
ax.set_title("B  Seaweed outputs", loc="left")
ax.text(0.05, sw["asp_t"] + 2300, f"feeds {sw['asp_head']/1e3:,.0f}k head\n{sw['asp_abate_lo']:.2f}–{sw['asp_abate_hi']:.2f} Mt CO₂e/y\nenteric CH₄ abated",
        ha="center", fontsize=6.3)
ax.set_ylim(0, 14500)
fig.tight_layout()
save(fig, "fig9_mobility_seaweed")

# ------------------------------------------------------------------ Supplement S1: ERA5 resource treatments
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3), gridspec_kw=dict(width_ratios=[1.5, 1]))
keys = P.HUB_KEYS
xx = np.arange(7); ww = 0.26
raw = np.array(N["wind_cf_raw"]) * 100; pal = np.minimum(raw / 0.70, 60); tgt = np.array(N["wind_cf"]) * 100
ax = axs[0]
for k, (v, col, nm) in enumerate([(raw, C["violet"], "Raw ERA5 at station cell"), (pal, C["aqua"], "Station cell, ERA5 bias-corrected"),
                                   (tgt, C["blue"], "Regional wind-zone target (central)")]):
    ax.bar(xx + (k - 1) * (ww + 0.01), v, ww, color=col, label=nm, zorder=3)
ax.set_xticks(xx); ax.set_xticklabels(keys, fontsize=7.5); ax.set_ylabel("Wind capacity factor, %"); ax.set_ylim(0, 52)
ax.axhline(33, color=MUTED, ls="--", lw=0.8); ax.text(-0.4, 34, "NEM fleet Q2-2026: 33%", fontsize=6, color=INK2)
ax.legend(fontsize=6.5, loc="upper left", ncol=1, bbox_to_anchor=(0, 0.93))
ax.set_title("A  Wind, 130 m hub, 2010–2025 mean", loc="left")
ax = axs[1]
cf, lo, hi = N["pv_cf"], N["pv_cf_year_min"], N["pv_cf_year_max"]
ax.bar(xx, np.array(cf) * 100, 0.55, color=C["yellow"], zorder=3)
ax.errorbar(xx, np.array(cf) * 100, yerr=[np.array(cf) * 100 - np.array(lo) * 100, np.array(hi) * 100 - np.array(cf) * 100], fmt="none", color=INK, capsize=3, lw=0.9)
ax.axhline(23.9, color=MUTED, ls="--", lw=0.8); ax.text(-0.4, 32.8, "dashed: NEM fleet Q4-2025, 23.9%", fontsize=6, color=INK2)
ax.set_xticks(xx); ax.set_xticklabels(keys, fontsize=7.5); ax.set_ylabel("PV AC capacity factor, %"); ax.set_ylim(0, 36)
ax.set_title("B  Tracker PV from ERA5 (annual range)", loc="left")
fig.tight_layout()
save(fig, "figS1_resource_calibration")

# ------------------------------------------------------------------ Figure 10: wind siting and weather-year variability
NP = json.load(open(J("dga_numbers_palmer.json"))); NR = json.load(open(J("dga_numbers_raw.json")))
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw=dict(width_ratios=[1, 1.25]))
ax = axs[0]
cases = [("Regional\nwind zones", N), ("Station sites,\nbias-corrected", NP), ("Station sites,\nraw ERA5", NR)]
nets = [{r["label"]: r for r in n["sym_ext"]}["DGA enlarged (extended)"]["net"] for _, n in cases]
smrs = [{r["label"]: r for r in n["sym_ext"]}["DGA enlarged + SMR (extended)"]["net"] for _, n in cases]
S0 = {r["label"]: r for r in N["sym_ext"]}
x3 = np.arange(3)
ax.bar(x3 - 0.19, nets, 0.36, color=C["blue"], label="DGA enlarged", zorder=3)
ax.bar(x3 + 0.19, smrs, 0.36, color=C["red"], label="DGA + 2.4 GW SMR", zorder=3)
for i in range(3):
    ax.text(x3[i] - 0.19, nets[i] + 0.05, f"{nets[i]:.2f}", ha="center", fontsize=6.6)
    ax.text(x3[i] + 0.19, smrs[i] + 0.05, f"{smrs[i]:.2f}", ha="center", fontsize=6.6)
for lab_, key, ls in [("Gas 90% CCS", "Gas campus 90% CCS (extended)", "--"), ("Gas 95% CCS", "Gas campus 95% CCS (extended)", ":")]:
    v = S0[key]["net"]; ax.axhline(v, color=C["orange"], ls=ls, lw=1.3, label=f"{lab_} ({v:.2f})", zorder=1)
ax.set_xticks(x3); ax.set_xticklabels([c[0] for c in cases], fontsize=7)
ax.set_ylabel("Conditional net Mt CO₂e/y (extended)"); ax.set_ylim(0, 4.2)
ax.legend(fontsize=6.6, loc="upper left")
ax.set_title("A  Effect of turbine siting", loc="left")
ax = axs[1]
Wh = hs["W"]; PVh = hs["PV"]; shr = np.array([h["share"] for h in P.HUBS])
wy = [(Wh[:, y * 8760:(y + 1) * 8760].mean(1) * shr).sum() * 100 for y in range(16)]
py = [(PVh[:, y * 8760:(y + 1) * 8760].mean(1) * shr).sum() * 100 for y in range(16)]
yrs = np.arange(2010, 2026)
ax.plot(yrs, wy, color=C["blue"], marker="o", ms=4, lw=1.8, label="Fleet wind CF (regional siting)")
ax.plot(yrs, py, color=C["yellow"], marker="s", ms=4, lw=1.8, label="Fleet PV CF")
ax.set_ylabel("IT-weighted fleet capacity factor, %"); ax.set_ylim(20, 42); ax.set_xticks([2010, 2013, 2016, 2019, 2022, 2025])
ax.legend(fontsize=6.6, loc="lower left")
ax.set_title("B  Year-to-year resource, 2010–2025", loc="left")
fig.tight_layout()
save(fig, "fig10_wind_siting")
N_wy = dict(wind_year_cf=wy, pv_year_cf=py)

# Supplement S3: temperature and PUE by month
fig, ax = plt.subplots(figsize=(7.0, 3.0))
FAC = hs["FAC"]
for i, (k, col) in enumerate(zip(keys, list(C.values()))):
    pue_m = [FAC[i][month_idx == m].mean() / R["IT_mw"][i] for m in range(12)]
    ax.plot(range(12), pue_m, color=col, lw=1.6, label=k)
ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND")); ax.set_ylabel("Monthly mean PUE")
ax.legend(fontsize=7, ncol=7, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_title("Dry-loop facility PUE from ERA5 hourly temperature, 2010–2025", loc="left")
save(fig, "figS2_pue")

N_extra.update(N_wy)
json.dump(N_extra, open(J("dga_fig_extra.json"), "w"), indent=1, default=float)
print("done", N_extra)
