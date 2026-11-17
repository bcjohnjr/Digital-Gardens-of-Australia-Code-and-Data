# Digital Gardens Australia — model code and data (v1.1.0)

Repository: https://github.com/bcjohnjr/Digital-Gardens-of-Australia-Code-and-Data

Everything runs from **one folder with no subfolders**. Scripts, the weather file and all outputs sit side by side.

## Files to upload to the repository (all in the top level)

| File | What it is |
|---|---|
| `dga_params.py` | Every assumption, with its source |
| `dga_weather.py` | Checks the weather file (140,160 hours, no 29 February, no gaps) and converts it |
| `dga_model.py` | Hourly dispatch for the seven hubs, 2010–2025, and the carbon, heat, food, fuel and mobility ledgers |
| `dga_analysis.py` | Derives every number reported in the manuscript |
| `dga_premium.py` | Community-benefit cost ledger and the GPU-rental premium that would fund it |
| `dga_figures.py` | Figures and maps |
| `dga_verify.py` | Clean-reproduction check against the published values |
| `dga_checksums.py` | SHA-256 verification of the data and code |
| `dga_download_era5.py` | Optional: rebuilds the weather file from the Open-Meteo ERA5 archive (stdlib + pandas) |
| `run_all.py` | Runs everything in order |
| `dispatch_hourly_wide.csv.gz` | ERA5 weather input, 8 sites × 140,160 hours (23.2 MB) |
| `provenance_manifest.json` | Download provenance: API, model pin, coordinates, raw-response SHA-256 for all 128 site-years |
| `dga_checksums.sha256` | SHA-256 of the data and code files |
| `dga_reference_values.json` | The 159 published values that `dga_verify.py` checks |
| `dga_aus_outline.json` | Australia outline for the maps (Natural Earth 1:110m, public domain) |
| `requirements.txt`, `README.md`, `CITATION.cff`, `LICENSE` | Dependencies, this file, citation metadata, MIT licence |

All files are under GitHub's 25 MB web-upload limit.

## Run

1. Put the files above in one folder.
2. Install the dependencies once (Python 3.10 or newer):
   - Windows: `py -m pip install -r requirements.txt`
   - macOS/Linux: `python3 -m pip install -r requirements.txt`
3. Run everything:
   - Windows: `py run_all.py`
   - macOS/Linux: `python3 run_all.py`

The full run takes about one minute on a fast laptop and can take several minutes on slower machines. The last line should read
`RESULT: 159 of 159 values reproduced - CLEAN REPRODUCTION`, and the details are written to
`dga_reproduction_report.txt`. Nothing is written outside the folder and no `__pycache__` folder is created.

## Steps (what `run_all.py` does)

| Step | Command | Writes |
|---|---|---|
| Verify input data | `dga_checksums.py --data-only` | — |
| Check and convert weather | `dga_weather.py` | `dga_era5_weather.npz` |
| Dispatch, regional wind siting (central) | `dga_model.py rez` | `dga_results_rez.json`, `dga_trace_rez.npz`, `dga_hourly_rez.npz` |
| Dispatch, station sites, ERA5 bias-corrected | `dga_model.py palmer` | `dga_results_palmer.json` (+ npz) |
| Dispatch, station sites, raw ERA5 | `dga_model.py raw` | `dga_results_raw.json` (+ npz) |
| Ledgers (carbon, heat, water, fuel, economics) | `dga_analysis.py rez` (and `palmer`, `raw`) | `dga_numbers_*.json` |
| Community cost and GPU premium | `dga_premium.py rez` (and `palmer`, `raw`) | `dga_premium_*.json` |
| Figures and maps | `dga_figures.py` | `fig*.png`, `dga_fig_extra.json` |
| Clean-reproduction check | `dga_verify.py` | `dga_reproduction_report.txt` |

## Checking the data independently

- `python dga_checksums.py` verifies all 14 listed files; `sha256sum -c dga_checksums.sha256` does the same on Linux/macOS.
- SHA-256 of `dispatch_hourly_wide.csv.gz`: `4e7be3e638b312aedb59a41539d6d23081f371184abcac0faafbfa1885a3ecc9`.
- To rebuild the weather file from the provider: `python dga_download_era5.py --out era5_rebuilt.csv.gz`, then
  `python dga_checksums.py --compare-csv era5_rebuilt.csv.gz`. The gzip bytes will differ (compression
  metadata and line endings), but the values agree: an offline rebuild from the 128 cached API responses
  matched the supplied file to within 2.2 × 10⁻¹⁶ in every cell.

## Notes

- Weather: ERA5 reanalysis (Hersbach et al. 2020) via the Open-Meteo archive API, model pinned to `era5`, elevation downscaling disabled, UTC timestamps, 2010–2025 with 29 February removed. ERA5 is an observation-constrained reanalysis, not station measurement, and the coordinates are retired coal-station proxies, not verified wind-farm or solar-farm sites. Electricity prices and grid and SMR outages are synthetic, using a fixed random seed.
- Wind treatments: `rez` scales ERA5 wind speeds so that each hub reaches its regional wind-farm capacity-factor target. `palmer` corrects the median ERA5 under-prediction (−30%) at the station cells. `raw` uses ERA5 unchanged.
- Firming engines are dual-fuel: digester biogas up to 67% of fuel energy, with waste-oil biodiesel never below 33%. Biodiesel comes first from a used-cooking-oil purchase programme and then from rendered tallow.
- The GPU premium (`dga_premium.py`) covers the community programme only (free food, hot water, drying, Asparagopsis, biomethane, vehicles, charging and renewable-fuel price parity). Electricity-supply costs are not in it.

## Licence and citation

Code: MIT. Data: ERA5 is © ECMWF/Copernicus, distributed by Open-Meteo under CC BY 4.0; cite both. See `CITATION.cff`.
