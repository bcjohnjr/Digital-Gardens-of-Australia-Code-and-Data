"""Check and convert the ERA5 weather input into dgs_weather.npz.

Normal use: dgs_era5_hourly.csv.gz (written by dgs_download_era5.py; ten Sunraysia-network sites) is in
this folder ->  python dgs_weather.py

PROVISIONAL use: if dgs_era5_hourly.csv.gz is absent but the earlier ERA5 file dispatch_hourly_wide.csv.gz
is present, the script builds a clearly flagged PROXY: Port Augusta weather stands in for every Sunraysia
campus and both wind zones, Muswellbrook for Eastern Creek and the Latrobe Valley for Laverton. Every
output then carries proxy=True and the manuscript builders print a PROVISIONAL banner.
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import dgs_params as P

FIELDS = [("T", "temperature_2m_C"), ("ws100", "wind_speed_100m_ms"), ("ghi", "ghi_Wm2"), ("dni", "dni_Wm2"),
          ("dhi", "dhi_Wm2"), ("rh", "relative_humidity_2m_pct"), ("ps", "surface_pressure_hPa")]
REAL = os.path.join(HERE, "dgs_era5_hourly.csv.gz")
OLD = os.path.join(HERE, "dispatch_hourly_wide.csv.gz")
PROXY_MAP = {"mil": "port_augusta", "irc": "port_augusta", "mwd": "port_augusta", "rob": "port_augusta",
             "swh": "port_augusta", "ker": "port_augusta", "pot": "port_augusta", "yan": "port_augusta",
             "eac": "muswellbrook", "lav": "latrobe_valley"}
sites = [k.lower() for k in P.SITE_KEYS]

if os.path.exists(REAL):
    src, proxy, colmap = REAL, False, {s: s for s in sites}
elif os.path.exists(OLD):
    src, proxy, colmap = OLD, True, PROXY_MAP
    print("WARNING: dgs_era5_hourly.csv.gz not found - building a PROVISIONAL proxy from dispatch_hourly_wide.csv.gz")
else:
    sys.exit("No weather file. Run  python dgs_download_era5.py  first (about 10 minutes, needs internet).")

df = pd.read_csv(src)
ts = pd.to_datetime(df["timestamp_utc"], utc=True)
n = len(df)
assert n == P.NH, f"expected {P.NH:,} hourly rows (16 x 8,760), found {n:,}"
assert int(((ts.dt.month == 2) & (ts.dt.day == 29)).sum()) == 0, "29 February rows present"
assert ts.is_monotonic_increasing and ts.is_unique, "timestamps not strictly increasing"
assert (ts.diff().dropna() >= pd.Timedelta(hours=1)).all(), "sub-hourly step"
out = {}
for key, col in FIELDS:
    cols = [f"{colmap[s]}__{col}" for s in sites]
    missing = [c for c in cols if c not in df.columns]
    assert not missing, f"missing columns: {missing}"
    arr = np.stack([df[c].to_numpy(float) for c in cols]).astype(np.float32)
    assert not np.isnan(arr).any(), f"missing values in {col}"
    out[key] = arr
out["year"] = ts.dt.year.to_numpy()
out["month0"] = (ts.dt.month - 1).to_numpy()
out["doy"] = ts.dt.dayofyear.to_numpy()
out["hour_utc"] = ts.dt.hour.to_numpy()
out["ts"] = ts.dt.strftime("%Y-%m-%d %H:%M").to_numpy().astype("U16")
out["proxy"] = np.array(proxy)
out["source"] = np.array(os.path.basename(src))
out["sites"] = np.array(sites)
np.savez_compressed(os.path.join(HERE, "dgs_weather.npz"), **out)
print(f"OK: {n:,} hours, {ts.iloc[0]} to {ts.iloc[-1]}, {len(sites)} sites from {os.path.basename(src)}"
      + (" [PROVISIONAL PROXY]" if proxy else ""))
