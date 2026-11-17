"""Download the ERA5 weather input for Digital Gardens Sunraysia from the Open-Meteo archive API.

Ten sites: six Sunraysia campus groups, two South West REZ wind zones and two metropolitan comparator
sites (Eastern Creek NSW, Laverton North VIC), 2010-2025, hourly, UTC. Writes dgs_era5_hourly.csv.gz and
dgs_provenance_manifest.json into this folder; no sub-folders are created. Takes about 10 minutes.

    python dgs_download_era5.py                 # download (or reuse cached) 10 sites x 16 years, build the CSV
    python dgs_download_era5.py --offline       # rebuild the CSV from cached dgs_raw_*.json.gz only
    python dgs_download_era5.py --check-only    # report which site-years are cached

Standard library + numpy + pandas only (no `requests`). Each API response is cached as
dgs_raw_<site>_<year>_<key>.json.gz, where <key> is the first 12 hex digits of the SHA-256 of the
request parameters, so a changed coordinate or variable list can never reuse an old cache.

Source: ECMWF/Copernicus ERA5 (Hersbach et al. 2020, doi:10.1002/qj.3803) via the Open-Meteo
historical weather API (https://open-meteo.com/en/docs/historical-weather-api), model pinned to
'era5', elevation downscaling disabled, UTC timestamps. Irradiance is the mean of the PRECEDING hour.
ERA5 is an observation-constrained reanalysis, not station measurement. Campus coordinates are town anchors and the
wind-zone coordinates are approximate; none is a surveyed site.
"""
import os, sys, gzip, json, time, hashlib, argparse, urllib.parse, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

API = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "era5"
YEARS = list(range(2010, 2026))
SITES = {
    "mil": dict(name="Mildura campus group", lat=-34.185, lon=142.159, role="campus"),
    "irc": dict(name="Irymple / Red Cliffs campus group", lat=-34.232, lon=142.165, role="campus"),
    "mwd": dict(name="Merbein / Wentworth campus group", lat=-34.167, lon=142.057, role="campus"),
    "rob": dict(name="Robinvale / Euston campus group", lat=-34.584, lon=142.768, role="campus"),
    "swh": dict(name="Swan Hill / Nyah campus group", lat=-35.339, lon=143.559, role="campus"),
    "ker": dict(name="Kerang / Koondrook campus group", lat=-35.734, lon=143.919, role="campus"),
    "pot": dict(name="Pottinger project-area reference (AIA WMT #1; not surveyed turbine centroid)", lat=-34.98465556, lon=144.97216944, role="wind"),
    "yan": dict(name="South West REZ wind zone near Jerilderie (approximate)", lat=-35.29, lon=145.66, role="wind"),
    "eac": dict(name="Eastern Creek, western Sydney (metropolitan comparator)", lat=-33.80, lon=150.85, role="comparator"),
    "lav": dict(name="Laverton North, western Melbourne (metropolitan comparator)", lat=-37.82, lon=144.78, role="comparator"),
}
VARIABLES = {
    "temperature_2m": "temperature_2m_C", "relative_humidity_2m": "relative_humidity_2m_pct",
    "wind_speed_10m": "wind_speed_10m_ms", "wind_speed_100m": "wind_speed_100m_ms",
    "wind_direction_100m": "wind_direction_100m_deg", "shortwave_radiation": "ghi_Wm2",
    "direct_normal_irradiance": "dni_Wm2", "diffuse_radiation": "dhi_Wm2",
    "surface_pressure": "surface_pressure_hPa", "precipitation": "precipitation_mm", "cloud_cover": "cloud_cover_pct",
}
REQUIRED = ("temperature_2m", "wind_speed_100m", "shortwave_radiation")
WIDE_COLS = ["temperature_2m_C", "wind_speed_100m_ms", "wind_direction_100m_deg", "ghi_Wm2", "dni_Wm2", "dhi_Wm2",
             "relative_humidity_2m_pct", "surface_pressure_hPa", "precipitation_mm", "pue_temperature_formula",
             "wind_cf_generic_100m_screening"]


def params_for(site, year):
    return {"latitude": float(site["lat"]), "longitude": float(site["lon"]),
            "start_date": f"{year}-01-01", "end_date": f"{year}-12-31", "hourly": ",".join(VARIABLES),
            "models": MODEL, "timezone": "GMT", "timeformat": "unixtime", "wind_speed_unit": "ms",
            "temperature_unit": "celsius", "precipitation_unit": "mm", "cell_selection": "nearest", "elevation": "nan"}


def cache_name(slug, year, params):
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return os.path.join(HERE, f"dgs_raw_{slug}_{year}_{key}.json.gz")


def fetch(params, retries=6, timeout=90):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, dict) or data.get("error"):
                raise RuntimeError(f"API error: {str(data)[:300]}")
            return data, url
        except Exception as exc:          # network, HTTP 429/5xx, JSON
            print(f"    attempt {attempt}/{retries} failed: {exc}", flush=True)
            if attempt == retries:
                raise RuntimeError(f"could not fetch {url}") from exc
            time.sleep(30 * attempt)          # Open-Meteo rate limits: back off and retry


def read_or_download(slug, year, offline):
    params = params_for(SITES[slug], year)
    path = cache_name(slug, year, params)
    url = API + "?" + urllib.parse.urlencode(params)
    if not os.path.exists(path):
        if offline:
            raise FileNotFoundError(f"offline mode: cache missing {os.path.basename(path)}")
        data, url = fetch(params)
        time.sleep(4)                         # stay under the free API's per-minute limit
        tmp = path + ".tmp"
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest(), os.path.basename(path), url


def wind_cf_screen(v):
    v = np.asarray(v, dtype=float)
    pf = np.where(v < 3.0, 0.0, np.where(v < 11.5, (v ** 3 - 27.0) / (11.5 ** 3 - 27.0), np.where(v < 25.0, 1.0, 0.0)))
    return np.clip(0.90 * pf, 0.0, 0.90)


def frame_for(payload, slug, year):
    hourly = payload.get("hourly"); units = payload.get("hourly_units", {})
    if not isinstance(hourly, dict) or "time" not in hourly:
        raise ValueError(f"{slug}/{year}: malformed response")
    for f in VARIABLES:
        if f not in hourly:
            raise ValueError(f"{slug}/{year}: missing {f}")
    for name, ok in {"wind_speed_100m": ("m/s",), "wind_speed_10m": ("m/s",), "temperature_2m": ("°C",),
                     "shortwave_radiation": ("W/m²", "W/m2")}.items():
        if units.get(name) not in ok:
            raise ValueError(f"{slug}/{year}: bad unit for {name}: {units.get(name)!r}")
    ts = pd.to_datetime(hourly["time"], unit="s", utc=True)
    exp = pd.date_range(f"{year}-01-01T00:00:00Z", f"{year}-12-31T23:00:00Z", freq="h")
    if len(ts) != len(exp) or not np.array_equal(ts.as_unit("s").asi8, exp.as_unit("s").asi8):
        raise ValueError(f"{slug}/{year}: missing/duplicate/non-hourly timestamps")
    d = {"timestamp_utc": ts}
    for a, o in VARIABLES.items():
        d[o] = pd.to_numeric(pd.Series(hourly[a]), errors="coerce").to_numpy()
    fr = pd.DataFrame(d)
    for f in REQUIRED:
        if fr[VARIABLES[f]].isna().any():
            raise ValueError(f"{slug}/{year}: missing {f}")
    leap = (fr["timestamp_utc"].dt.month == 2) & (fr["timestamp_utc"].dt.day == 29)
    fr = fr.loc[~leap].reset_index(drop=True)
    if len(fr) != 8760:
        raise ValueError(f"{slug}/{year}: expected 8760 hours after dropping 29 February")
    T = fr["temperature_2m_C"].to_numpy(dtype=float)
    fr["pue_temperature_formula"] = 1.085 + 0.0045 * np.maximum(0, T - 18) + 0.012 * np.maximum(0, T - 32)
    fr["wind_cf_generic_100m_screening"] = wind_cf_screen(fr["wind_speed_100m_ms"].to_numpy(dtype=float))
    meta = dict(site=slug, year=year, returned_grid_lat=payload.get("latitude"), returned_grid_lon=payload.get("longitude"),
                returned_grid_elevation_m=payload.get("elevation"), raw_hours=int(len(ts)),
                dropped_feb29_hours=int(leap.sum()), model_hours=int(len(fr)))
    return fr, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="use cached responses only")
    ap.add_argument("--check-only", action="store_true", help="list cache status and exit")
    ap.add_argument("--out", default="dgs_era5_hourly.csv.gz", help="output file name (in this folder)")
    a = ap.parse_args()
    if os.path.basename(a.out) != a.out:
        sys.exit("--out must be a bare file name: this package keeps everything in one folder")
    if a.check_only:
        miss = [(s, y) for s in SITES for y in YEARS if not os.path.exists(cache_name(s, y, params_for(SITES[s], y)))]
        print(f"{len(SITES) * len(YEARS) - len(miss)} of {len(SITES) * len(YEARS)} site-years cached")
        for s, y in miss:
            print("  missing", s, y)
        return 0
    frames, downloads = {}, []
    for slug in SITES:
        parts = []
        for y in YEARS:
            print(f"{slug} {y}", flush=True)
            payload, digest, fname, url = read_or_download(slug, y, a.offline)
            fr, meta = frame_for(payload, slug, y)
            meta.update(raw_file=fname, raw_api_sha256=digest, url=url)
            downloads.append(meta); parts.append(fr)
        frames[slug] = pd.concat(parts, ignore_index=True)
    ref = frames["mil"]["timestamp_utc"].reset_index(drop=True)
    wide = pd.DataFrame({"timestamp_utc": ref})
    for slug in SITES:
        if not ref.equals(frames[slug]["timestamp_utc"].reset_index(drop=True)):
            raise ValueError(f"timestamp alignment failure for {slug}")
        for c in WIDE_COLS:
            wide[f"{slug}__{c}"] = frames[slug][c].to_numpy()
    if len(wide) != len(YEARS) * 8760:
        raise ValueError("expected 140,160 rows")
    out = os.path.join(HERE, a.out)
    wide.to_csv(out, index=False, compression={"method": "gzip", "mtime": 0})
    with open(out, "rb") as fh:
        gz_sha = hashlib.sha256(fh.read()).hexdigest()
    csv_sha = hashlib.sha256(wide.to_csv(index=False).encode("utf-8")).hexdigest()
    man = dict(created_utc=datetime.now(timezone.utc).isoformat(), api_endpoint=API, model_requested=MODEL,
               years=YEARS, no_leap_days=True, expected_hours_per_site=len(YEARS) * 8760,
               source_type="observation-constrained reanalysis; NOT direct observations",
               time_reference="UTC; solar and precipitation values refer to the preceding hour",
               sites=SITES, variable_names=VARIABLES, output_file=a.out, output_sha256_gzip=gz_sha,
               output_sha256_uncompressed_csv=csv_sha, downloads=downloads)
    with open(os.path.join(HERE, "dgs_provenance_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, default=str)
    print(f"wrote {a.out}: {len(wide):,} rows x {wide.shape[1]} columns; uncompressed CSV SHA-256 {csv_sha}")
    print("compare with the supplied file: python dgs_checksums.py --compare-csv", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
