# Digital Gardens Sunraysia — model code and data (v2.1.0)

Repository: https://github.com/bcjohnjr/Digital-Gardens-of-Australia-Code-and-Data

This model covers a population-weighted, distributed AI data-centre network. It serves 16 Sunraysia and Murray-corridor towns (75,833 residents at the 2021 Census) through six shared campuses. It is compared with grid-supplied metropolitan campuses in western Sydney and Melbourne, with a gas-fired campus, and with nine named Australian mega-campus projects.

Everything runs from **one folder with no subfolders**.

## Files

| File | What it is |
|---|---|
| `dgs_params.py` | Every assumption, with its source |
| `dgs_towns_2021.csv` | ABS 2021 locality populations, campus groups and IT allocations |
| `dgs_download_era5.py` | Downloads ERA5 weather for 10 sites, 2010–2025, from Open-Meteo (about 15–30 min) |
| `dgs_weather.py` | Checks the weather file (140,160 hours, no 29 February, no gaps) and converts it |
| `dgs_model.py` | Hourly dispatch for all scenarios; carbon, heat, food, biogas and vehicle ledgers |
| `dgs_analysis.py` | Every number reported in the manuscript |
| `dgs_premium.py` | Community-benefit cost ledger and the GPU-rental surcharge |
| `dgs_figures.py` | Figures and maps |
| `dgs_verify.py`, `dgs_checksums.py` | Reproduction check and SHA-256 checks |
| `run_all.py` | Runs everything in order |
| `dgs_era5_hourly.csv.gz`, `dgs_provenance_manifest.json` | ERA5 input and its download record |
| `dgs_checksums.sha256`, `dgs_reference_values.json` | Checksums and published values |
| `dgs_aus_outline.json` | Australia outline for the maps (Natural Earth, public domain) |

## Run

1. Install the dependencies (Python 3.10+): `python -m pip install -r requirements.txt`
2. If `dgs_era5_hourly.csv.gz` is not present, download the weather first: `python dgs_download_era5.py`
3. Run everything: `python run_all.py`

The last line of the run should report that every published value was reproduced. If the weather file is missing, the model falls back to a clearly labelled PROVISIONAL proxy (when `dispatch_hourly_wide.csv.gz` is present). Do not cite proxy results.

**Maintainer, after new weather data:** run `python run_all.py`, then `python dgs_verify.py --make-reference`, then `python dgs_checksums.py --write`, then `python run_all.py` again.

## Notes

- **Weather.** ERA5 reanalysis (Hersbach et al. 2020) via the Open-Meteo archive, model pinned to `era5`, UTC timestamps. Coordinates are town anchors and approximate wind zones, not surveyed sites.
- **Synthetic inputs.** Prices, grid contingencies and campus outages are synthetic, with a fixed seed.
- **Standby engines.** The engines are standby only. They co-fire stored biogas with at least 33% biodiesel and are supplied first by a used-cooking-oil purchase programme.
- **GPU surcharge.** The surcharge covers community benefits only; electricity-supply costs are excluded.
- **Concept status.** Digital Gardens Sunraysia is a concept. No land, grid, fibre, licence or contract exists.

## Licence

Code: MIT. ERA5 data: © ECMWF/Copernicus, distributed by Open-Meteo under CC BY 4.0.
