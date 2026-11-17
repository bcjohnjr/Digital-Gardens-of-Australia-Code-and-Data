# Digital Gardens Australia — model code

Everything runs from **one folder with no subfolders**. Scripts, the weather file and all outputs sit side by side.

## Run

1. Put these files in one folder:
   - `dga_params.py`, `dga_weather.py`, `dga_model.py`, `dga_model_synthetic.py`, `dga_analysis.py`, `dga_figures.py`, `run_all.py`
   - `dga_aus_outline.json` (map outline, Natural Earth 1:110m, public domain)
   - `requirements.txt`
   - `dispatch_hourly_wide.csv.gz` (copied from the ERA5 downloader output folder)
2. Install the dependencies once (Python 3.10 or newer):
   - Windows: `py -m pip install -r requirements.txt`
   - macOS/Linux: `python3 -m pip install -r requirements.txt`
3. Run everything:
   - Windows: `py run_all.py`
   - macOS/Linux: `python3 run_all.py`

The full run takes about one minute. Nothing is written outside the folder, and no `__pycache__` folder is created.

## Steps (what `run_all.py` does)

| Step | Command | Writes |
|---|---|---|
| Check and convert weather | `dga_weather.py` | `dga_era5_weather.npz` |
| Dispatch, regional wind siting (central) | `dga_model.py rez` | `dga_results_rez.json`, `dga_trace_rez.npz`, `dga_hourly_rez.npz` |
| Dispatch, station sites, ERA5 bias-corrected | `dga_model.py palmer` | `dga_results_palmer.json` (+ npz) |
| Dispatch, station sites, raw ERA5 | `dga_model.py raw` | `dga_results_raw.json` (+ npz) |
| Earlier synthetic-weather comparison | `dga_model_synthetic.py` | `dga_results_synthetic.json` (+ npz) |
| Ledgers (carbon, heat, water, economics) | `dga_analysis.py rez` (and `palmer`, `raw`, `synthetic`) | `dga_numbers_*.json` |
| Figures and maps | `dga_figures.py` | `fig*.png`, `dga_fig_extra.json` |

Any step can be run on its own in the same order. `dga_weather.py` stops with a message if the weather file is missing, has the wrong number of hours (expects 140,160), contains 29 February, or has missing values.

## Notes

- All assumptions are in `dga_params.py`.
- Weather: ERA5 reanalysis via Open-Meteo, 2010–2025, at the power-station coordinates. Electricity prices and grid and SMR outages are synthetic, using a fixed random seed.
- Wind treatments: `rez` scales ERA5 wind speeds so that each hub reaches its regional wind-farm capacity-factor target. `palmer` corrects the median ERA5 under-prediction (−30%) at the station cells. `raw` uses ERA5 unchanged.
