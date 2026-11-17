"""Convert the ERA5 downloader output into the model's weather file.

Put  dispatch_hourly_wide.csv.gz  (from DGA_ERA5_Historical_Weather_Downloader) in this
folder, then run:  python dga_weather.py   ->  writes dga_era5_weather.npz in this folder.
An explicit path may be given as the first argument.
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "dispatch_hourly_wide.csv.gz")
if not os.path.exists(SRC):
    sys.exit(f"Weather file not found: {SRC}\nCopy dispatch_hourly_wide.csv.gz from the ERA5 download into this folder.")
SITES = ["muswellbrook", "lithgow", "nanango", "biloela", "latrobe_valley", "port_augusta", "collie", "weddell"]
FIELDS = [("T", "temperature_2m_C"), ("ws100", "wind_speed_100m_ms"), ("ghi", "ghi_Wm2"), ("dni", "dni_Wm2"),
          ("dhi", "dhi_Wm2"), ("rh", "relative_humidity_2m_pct"), ("ps", "surface_pressure_hPa")]

df = pd.read_csv(SRC)
ts = pd.to_datetime(df["timestamp_utc"], utc=True)
n = len(df)
assert n == 140160, f"expected 140,160 hourly rows (16 x 8,760), found {n}"
assert int(((ts.dt.month == 2) & (ts.dt.day == 29)).sum()) == 0, "29 February rows present"
assert ts.is_monotonic_increasing, "timestamps not in order"
out = {}
for key, col in FIELDS:
    cols = [f"{s}__{col}" for s in SITES]
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
np.savez_compressed(os.path.join(HERE, "dga_era5_weather.npz"), **out)
print(f"OK: {n} hours, {ts.iloc[0]} to {ts.iloc[-1]}, {len(SITES)} sites -> dga_era5_weather.npz")
