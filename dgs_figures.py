"""Figures and maps for Digital Gardens Sunraysia. Run: python dgs_figures.py  (after the model, analysis and premium steps)"""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dgs_params as P

J = lambda name: os.path.join(HERE, name)
N = json.load(open(J("dgs_numbers_rez.json")))
R = json.load(open(J("dgs_results_rez.json")))
Q = json.load(open(J("dgs_premium_rez.json")))
NP_ = json.load(open(J("dgs_numbers_palmer.json")))
NR_ = json.load(open(J("dgs_numbers_raw.json")))
AUS = json.load(open(J("dgs_aus_outline.json")))
PROXY = bool(N["proxy"])

C = dict(blue="#2a78d6", orange="#eb6834", aqua="#1baf7a", yellow="#eda100", magenta="#e87ba4",
         green="#008300", violet="#6250d6", red="#e34948")
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
CAMPUS_COL = dict(zip(P.CKEYS, [C["violet"], C["blue"], C["aqua"], C["orange"], C["magenta"], C["yellow"]]))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 400})
MONTHS = "JFMAMJJASOND"


def save(fig, name):
    if PROXY:
        fig.text(0.99, 0.995, "PROVISIONAL: proxy weather", ha="right", va="top", fontsize=7, color=C["red"])
    fig.savefig(J(f"{name}.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


MURRAY = [(140.96, -33.98), (141.5, -34.08), (142.0, -34.17), (142.4, -34.30), (142.8, -34.58), (143.3, -34.80),
          (143.6, -35.25), (144.0, -35.60), (144.6, -35.75), (146.0, -35.95), (147.0, -36.05), (148.2, -36.8), (149.98, -37.50)]
OTHER_BORDERS = [[(129.0, -14.88), (129.0, -31.69)], [(129.0, -26.0), (141.0, -26.0)], [(138.0, -26.0), (138.0, -16.54)],
                 [(141.0, -26.0), (141.0, -34.0), (140.96, -38.06)],
                 [(141.0, -29.0), (148.9, -29.0), (149.6, -28.6), (150.9, -28.6), (151.5, -28.95), (152.0, -28.55), (153.2, -28.25), (153.55, -28.17)]]


def land(ax):
    for poly in AUS["coordinates"]:
        ax.add_patch(Polygon(np.array(poly[0]), closed=True, facecolor="#f3f2ee", edgecolor="#9b9a95", lw=0.7, zorder=1))
    for b in OTHER_BORDERS + [MURRAY]:
        b = np.array(b); ax.plot(b[:, 0], b[:, 1], color="#bdbcb6", lw=0.6, ls=(0, (4, 2)), zorder=2)


# ------------------------------------------------------------------ Figure 1: national context and the Sunraysia network
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw=dict(width_ratios=[1, 1.15]))
land(a1)
a1.set_xlim(112, 155); a1.set_ylim(-44.5, -9.5); a1.set_aspect(1 / np.cos(np.radians(27))); a1.grid(False)
a1.set_xticks([]); a1.set_yticks([])
for s in a1.spines.values():
    s.set_visible(False)
syd = [x for x in N["named"] if x["state"] == "NSW"]; mel = [x for x in N["named"] if x["state"] == "VIC"]
for grp, (x, y), lab in ((syd, (150.85, -33.80), "Western Sydney"), (mel, (144.85, -37.80), "Melbourne")):
    mw = sum(g["mw"] for g in grp)
    a1.scatter([x], [y], s=mw / 6, color=C["red"], alpha=0.55, edgecolor="white", lw=0.8, zorder=4)
    a1.annotate(f"{lab}: {len(grp)} named\nprojects, {mw:,.0f} MW", (x, y), xytext=(x + (1.0 if lab == "Melbourne" else 1.2), y + (-3.8 if lab == "Melbourne" else 2.6)),
                fontsize=7.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), zorder=5)
a1.scatter([142.4], [-34.6], s=P.IT_MW / 6, color=C["violet"], alpha=0.8, edgecolor="white", lw=0.8, zorder=4)
a1.annotate(f"Digital Gardens Sunraysia\n6 campuses, {P.IT_MW:.0f} MW IT", (142.4, -34.6), xytext=(126.0, -40.5),
            fontsize=7.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), zorder=5)
a1.add_patch(plt.Rectangle((141.2, -36.3), 4.8, 2.6, fill=False, ec=C["violet"], lw=0.8, zorder=3))
a1.set_title("(a) Sunraysia and the named mega-campus projects", loc="left")
land(a2)
a2.set_xlim(141.6, 146.1); a2.set_ylim(-36.1, -33.8); a2.set_aspect(1 / np.cos(np.radians(35)))
a2.set_xlabel("Longitude (°E)"); a2.set_ylabel("Latitude (°S)")
route = [(142.057, -34.167), (142.159, -34.185), (142.165, -34.232), (142.768, -34.584), (143.559, -35.339), (143.919, -35.734)]
r = np.array(route); a2.plot(r[:, 0], r[:, 1], color=C["violet"], lw=1.2, ls=(0, (5, 2)), zorder=3)
for wz in P.WIND_ZONES:
    a2.scatter([wz["lon"]], [wz["lat"]], marker="^", s=70, color=C["aqua"], edgecolor="white", zorder=5)
a2.text(145.25, -34.3, "South West REZ\nwind zones", fontsize=7.5, color=INK2, ha="center")
camp = {c["group"]: c["key"] for c in P.CAMPUSES}
import csv
towns = list(csv.DictReader(open(J("dgs_towns_2021.csv"), encoding="utf-8")))
TC = {"Mildura": (142.159, -34.185), "Buronga": (142.177, -34.172), "Gol Gol": (142.218, -34.183), "Irymple": (142.165, -34.232),
      "Red Cliffs": (142.188, -34.306), "Merbein": (142.057, -34.167), "Wentworth": (141.917, -34.107), "Dareton": (142.039, -34.093),
      "Koorlong": (142.09, -34.264), "Cardross": (142.174, -34.308), "Robinvale": (142.768, -34.584), "Euston": (142.736, -34.581),
      "Swan Hill": (143.559, -35.339), "Nyah": (143.378, -35.173), "Kerang": (143.919, -35.734), "Koondrook": (144.117, -35.643)}
for t in towns:
    x, y = TC[t["town"]]; k = camp[t["shared_campus"]]
    a2.scatter([x], [y], s=int(t["2021_census_locality_population"]) / 60 + 8, color=CAMPUS_COL[k], alpha=0.75, edgecolor="white", lw=0.6, zorder=4)
for nm, dx, dy in (("Mildura", 0.10, 0.10), ("Wentworth", -0.05, 0.10), ("Red Cliffs", 0.08, -0.12), ("Robinvale", 0.08, 0.08),
                   ("Swan Hill", 0.10, 0.02), ("Kerang", 0.10, -0.04), ("Koondrook", 0.06, 0.08)):
    a2.text(TC[nm][0] + dx, TC[nm][1] + dy, nm, fontsize=7, color=INK)
handles = [Line2D([], [], marker="o", ls="", color=CAMPUS_COL[c["key"]], label=f"{c['group']} ({c['share'] * P.IT_MW:.0f} MW)") for c in P.CAMPUSES]
handles += [Line2D([], [], color=C["violet"], ls=(0, (5, 2)), label="Proposed fibre corridor (not surveyed)"),
            Line2D([], [], marker="^", ls="", color=C["aqua"], label="Contracted wind zones (approximate)")]
a2.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=6.5, ncol=1)
a2.text(141.7, -34.9, "VIC", color="#a3a29c", fontweight="bold"); a2.text(142.6, -34.0, "NSW", color="#a3a29c", fontweight="bold")
a2.text(144.1, -35.5, "Murray River (state border)", color="#9b9a95", fontsize=6.5, rotation=-28)
a2.set_title("(b) Sixteen towns in six shared campuses (bubble area = 2021 population)", loc="left")
fig.tight_layout(); save(fig, "fig1_network_map")

# ------------------------------------------------------------------ Figure 2: town allocations
fig, ax = plt.subplots(figsize=(8.6, 3.6))
ts = sorted(towns, key=lambda t: -int(t["2021_census_locality_population"]))
mw = [P.IT_MW * int(t["2021_census_locality_population"]) / P.POP for t in ts]
cols = [CAMPUS_COL[camp[t["shared_campus"]]] for t in ts]
ax.bar(range(len(ts)), mw, color=cols, width=0.72)
for i, v in enumerate(mw):
    ax.text(i, v + 2, f"{v:.1f}", ha="center", fontsize=6.5, color=INK2)
ax.set_xticks(range(len(ts))); ax.set_xticklabels([t["town"] for t in ts], rotation=50, ha="right", fontsize=7.5)
ax.set_ylabel("Allocated IT capacity (MW)")
ax.set_title(f"IT entitlement = {P.IT_MW:.1f} MW × locality population ÷ {P.POP:,}", loc="left")
ax.legend(handles=[Line2D([], [], marker="s", ls="", color=CAMPUS_COL[c["key"]], label=c["group"]) for c in P.CAMPUSES], fontsize=6.5, ncol=2)
fig.tight_layout(); save(fig, "fig2_town_allocation")

# ------------------------------------------------------------------ Figure 3: carbon ledger
fig, ax = plt.subplots(figsize=(8.6, 3.8))
rows = N["ledger"]
labs = [r["label"] for r in rows][::-1]; vals = [r["net"] for r in rows][::-1]
cl = [C["violet"] if l.startswith("DGS") else (C["red"] if "Metropolitan" in l else C["orange"]) for l in labs]
ax.barh(range(len(labs)), vals, color=cl, height=0.65)
for i, v in enumerate(vals):
    ax.text(v + 0.03, i, f"{v:.2f}", va="center", fontsize=7.5, color=INK2)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs, fontsize=7.5)
ax.set_xlabel("Net emissions, Mt CO₂e/year (partial inventory, equal heat credit)")
ax.set_title(f"Equal service: {P.IT_MW:.0f} MW IT plus the community electricity loads", loc="left")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "fig3_carbon")

# ------------------------------------------------------------------ Figure 4: named projects
fig, (b1, b2) = plt.subplots(1, 2, figsize=(10.0, 4.0), sharey=True)
nm = sorted(N["named"], key=lambda x: x["mw"])
labs = [f"{x['name']} ({x['operator'].split(' (')[0]})" for x in nm] + ["Digital Gardens Sunraysia (6 campuses)"]
mws = [x["mw"] for x in nm] + [P.IT_MW]
mts = [x["mt_loc"] for x in nm] + [N["fac_basis"]["dgs"]]
cl = [C["red"] if x["state"] == "NSW" else C["orange"] for x in nm] + [C["violet"]]
b1.barh(range(len(labs)), mws, color=cl, height=0.65); b1.set_yticks(range(len(labs))); b1.set_yticklabels(labs, fontsize=7)
b1.set_xlabel("Announced capacity (MW, as reported)"); b1.set_title("(a) Capacity", loc="left"); b1.grid(axis="y", visible=False)
b2.barh(range(len(labs)), mts, color=cl, height=0.65); b2.set_xlabel("Mt CO₂e/year at full load, location-based")
for i, v in enumerate(mts):
    b2.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=6.5, color=INK2)
b2.set_title("(b) Grid emissions screen (PUE 1.25; NGA 2025–26)", loc="left"); b2.grid(axis="y", visible=False)
b1.legend(handles=[Line2D([], [], marker="s", ls="", color=C["red"], label="NSW grid (0.64 t/MWh)"),
                   Line2D([], [], marker="s", ls="", color=C["orange"], label="VIC grid (0.78 t/MWh)"),
                   Line2D([], [], marker="s", ls="", color=C["violet"], label="DGS, modelled dispatch")], fontsize=6.5, loc="lower right")
fig.tight_layout(); save(fig, "fig4_named_projects")

# ------------------------------------------------------------------ Figure 5: dispatch weeks
TRZ = np.load(J("dgs_trace_rez.npz"))
names = list(TRZ["names"]); j = names.index("balanced|central")
ts_ = np.load(J("dgs_weather.npz"))["ts"]
yrs = np.array([int(x[:4]) for x in ts_]); mon = np.array([int(x[5:7]) for x in ts_]); day = np.array([int(x[8:10]) for x in ts_])
fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.4), sharey=True)
for ax, (m, lab) in zip(axs, ((7, "Winter week (July 2019)"), (1, "Summer week (January 2019)"))):
    i0 = int(np.where((yrs == 2019) & (mon == m) & (day == 8))[0][0]); sl = slice(i0, i0 + 168)
    h = np.arange(168)
    stack = [("Solar", TRZ["pv"][j][sl], C["yellow"]), ("Wind", TRZ["wind"][j][sl], C["aqua"]), ("Battery", TRZ["bdis"][j][sl], C["blue"]),
             ("Grid import", TRZ["imp"][j][sl], MUTED), ("Engines", TRZ["eng"][j][sl], C["red"])]
    base = np.zeros(168)
    for nm_, v, c_ in stack:
        ax.fill_between(h, base, base + v, color=c_, alpha=0.85, lw=0, label=nm_); base = base + v
    ax.plot(h, TRZ["load"][j][sl], color=INK, lw=1.0, label="Load")
    ax.set_title(lab, loc="left"); ax.set_xlabel("Hour of week (UTC)")
axs[0].set_ylabel("MW"); axs[1].legend(fontsize=7, ncol=3, loc="upper right")
fig.tight_layout(); save(fig, "fig5_dispatch")

# ------------------------------------------------------------------ Figure 6: IT size scenarios
rows = [r for r in N["it_rows"] if r["scenario"] == "central"]
adv = [r for r in N["it_rows"] if r["scenario"] == "combined_adverse"]
fig, (c1, c2) = plt.subplots(1, 2, figsize=(9.6, 3.4))
x = np.arange(len(rows)); lab = [f"{r['it']:.0f} MW\n({r['kw_per_res']:.1f} kW/res.)" for r in rows]
c1.bar(x - 0.18, [r["re"] * 100 for r in rows], width=0.36, color=C["aqua"], label="Renewable share of load (central)")
c1.bar(x + 0.18, [r["imp"] / r["load"] * 100 for r in rows], width=0.36, color=MUTED, label="Grid imports share")
c1.set_xticks(x); c1.set_xticklabels(lab, fontsize=7); c1.set_ylabel("% of annual load"); c1.legend(fontsize=7)
c1.set_title("(a) Supply mix as the network grows", loc="left")
c2.bar(x - 0.18, [r["uns_share"] * 100 for r in rows], width=0.36, color=C["violet"], label="Unserved, central")
c2.bar(x + 0.18, [r["uns_share"] * 100 for r in adv], width=0.36, color=C["red"], label="Unserved, combined adverse")
c2.set_xticks(x); c2.set_xticklabels(lab, fontsize=7); c2.set_ylabel("% of load unserved"); c2.legend(fontsize=7)
c2.set_title(f"(b) Adequacy behind a fixed {P.IMPORT_CAP_MW:.0f}-MW import right", loc="left")
fig.tight_layout(); save(fig, "fig6_it_scale")

# ------------------------------------------------------------------ Figure 7: heat by month
fig, ax = plt.subplots(figsize=(8.6, 3.3))
hm = R["heat_monthly"]; base = np.zeros(12)
for k, c_ in (("greenhouse", C["green"]), ("residential", C["orange"]), ("drying", C["yellow"]), ("aquaculture", C["blue"]), ("digester", C["magenta"])):
    v = np.array(hm[k]); ax.bar(range(12), v, bottom=base, color=c_, width=0.7, label=k.capitalize() if k != "residential" else "Homes (hot water, heat)"); base += v
ax2 = ax.twinx(); ax2.plot(range(12), np.array(R["led_monthly"]), color=C["violet"], marker="o", ms=3, lw=1.2, label="Purple-LED electricity")
ax2.set_ylabel("LED electricity (GWh/month)", color=C["violet"]); ax2.grid(False); ax2.spines["right"].set_visible(True)
ax.set_xticks(range(12)); ax.set_xticklabels(list(MONTHS)); ax.set_ylabel("Heat delivered (GWh_th/month)")
ax.set_title(f"Community heat uses {N['heat']['share'] * 100:.1f}% of rejected server heat", loc="left")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=7, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.08))
ax.set_ylim(0, ax.get_ylim()[1] * 1.05)
fig.tight_layout(); save(fig, "fig7_heat")

# ------------------------------------------------------------------ Figure 8: GPU premium
fig, ax = plt.subplots(figsize=(7.8, 3.3))
g = list(P.GPU_PRICE_USD_H); x = np.arange(len(g))
for off, key, c_, lb in ((-0.25, "community_low", C["aqua"], "Low costs"), (0, "community_central", C["violet"], "Central"), (0.25, "community_high", C["red"], "High costs")):
    v = [Q["premium"][key]["pct"][k] * 100 for k in g]
    ax.bar(x + off, v, width=0.24, color=c_, label=lb)
ax.axhline(P.WTP_PREMIUM * 100, color=INK, ls="--", lw=1.0); ax.text(3.45, P.WTP_PREMIUM * 100 + 0.2, "9.7% stated willingness to pay (PwC 2024)", ha="right", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([f"{k}\nUS${P.GPU_PRICE_USD_H[k]:.2f}/h" for k in g], fontsize=7.5)
ax.set_ylabel("Surcharge, % of GPU-hour price"); ax.legend(fontsize=7, loc="upper right", bbox_to_anchor=(1.0, 0.85))
ax.set_title(f"Funding the community programme: US${Q['premium']['community_central']['usd_per_gpu_h']:.3f} per GPU-hour (central)", loc="left")
fig.tight_layout(); save(fig, "fig8_premium")

# ------------------------------------------------------------------ Supplement S1: resource by year and wind treatment
fig, (d1, d2) = plt.subplots(1, 2, figsize=(9.6, 3.2))
yy = np.arange(N["year0"], N["year0"] + P.YEARS)
for n_, lab, c_ in ((N, "Regional target (central)", C["violet"]), (NP_, "ERA5 bias-corrected", C["aqua"]), (NR_, "Raw ERA5", MUTED)):
    d1.plot(yy, np.array(n_["wind_cf_year"]) * 100, marker="o", ms=3, color=c_, label=lab)
d1.set_ylabel("Wind capacity factor (%)"); d1.legend(fontsize=7); d1.set_title("(a) Contracted wind, by weather year", loc="left")
d2.plot(yy, np.array(N["pv_cf_year"]) * 100, marker="o", ms=3, color=C["yellow"])
d2.set_ylabel("PV capacity factor (%)"); d2.set_title("(b) Campus solar (single-axis tracker)", loc="left")
fig.tight_layout(); save(fig, "figS1_resource")
print("figures written" + (" [PROVISIONAL]" if PROXY else ""))
