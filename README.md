# ZudRisk

An open, reproducible estimate of dzud (зуд) risk for every soum of Mongolia, built from public data:
- Copernicus ERA5-Land winter temperature and snow;
- NASA MODIS summer NDVI;
- NSO livestock counts and losses;
- OCHA COD-AB soum boundaries.

It covers research hindcasts of 25 winters (2000/01-2024/25) plus a 2026/27 outlook updated monthly. It is not a
warning.

## What the site shows

- **Risk** per soum, aimag or natural zone for any winter: four indicators (cold, snow, summer pasture, grazing
  pressure) as z-scores, weighted into one score and five classes.
- **Chance** of adult losses of 5 % or more, in the soum popup. It is calibrated per outlook stage on 2011/12-2024/25.
- **Vulnerability** from a small learned model, replaying 20 winters' weather on today's herds.
- **Greenness trend** (desertification) and the six natural zones.
- **Validation** beside every map: how each winter and each outlook stage ranked the losses that followed.

## How well it works (2026-11-08)

Spearman rho of the risk score against adult livestock mortality:

| Test | rho | n |
|---|---|---|
| Pre-registered winters, soum level (2013/14, 2015/16, 2021/22-2023/24) | 0.596 | 1683 |
| Every soum-winter with losses, 2011/12-2024/25 | 0.434 | 4688 |
| Every aimag-winter, 2000/01-2024/25 | 0.547 | 525 |
| Outlook stage, pre-registered winters: Oct / Nov / Dec / Jan / Feb / Mar | 0.22 / 0.50 / 0.63 / 0.63 / 0.60 / 0.60 | 1683 |

The learned model ranks below the fixed weights when each winter is held out: soum rho 0.372 against 0.434, and AUC
0.745 against 0.763. The site says so. October, before any winter weather, is the weakest stage.

## Docs

- [plan.md](plan.md): what next, ranked, and what this round did.
- [Design and roadmap](docs/superpowers/specs/2026-11-08-zudrisk-design.md): the method and why.
- [Data sources](docs/research/data-sources.md): the research behind every input.
- [Snow comparison](docs/research/snow-comparison.md): GLDAS against ERA5-Land, generated.
- `docs/superpowers/plans/`: one implementation plan per version, v0.1-v0.5.

## Run

Needs `uv`. The boundaries and NSO steps need no login. The other sources need free accounts:
- **NASA Earthdata**, for the snow (GLDAS) and NDVI (MODIS) steps.
  - `~/.netrc` with `machine urs.earthdata.nasa.gov login ... password ...`, mode 600.
  - The "NASA GESDISC DATA ARCHIVE" application approved in the Earthdata profile.
- **Copernicus CDS**, for ERA5-Land and SEAS5.
  - `~/.cdsapirc` with `url: https://cds.climate.copernicus.eu/api` and `key: <API Token from your CDS profile>`.
  - Every licence on each dataset's page accepted. SEAS5 asks for more than one.

```bash
uv sync
uv run python -m pipeline.boundaries          # OCHA COD-AB soums -> data/derived/soums.geojson
uv run python -m pipeline.nso                 # NSO herds, losses and hay -> data/derived/
uv run python -m pipeline.era5                # ERA5-Land t2m, snow depth/density/cover, Nov-Mar, to the latest month (CDS)
uv run python -m pipeline.gldas               # GLDAS-2.1 snow depth, for the snow comparison only (Earthdata)
uv run python -m pipeline.ndvi                # MODIS MOD13C2 NDVI, Jul-Aug 2000 to the latest summer (Earthdata)
uv run python -m pipeline.seasonal --fetch && uv run python -m pipeline.seasonal  # SEAS5 1 October forecasts (CDS);
                                              # before hindcast, which tests them as the "Oct + SEAS5" stage
uv run python -m pipeline.hindcast            # natural zones, 25 winters scored, the pooled tests, snow comparison,
                                              # outlook stages, chance calibration, greenness trend and the model
uv run python -m pipeline.outlook --through 2026-10   # the 2026/27 outlook at its latest stage
python3 -m http.server -d site 8765           # open http://localhost:8765
```

`pipeline.zones` downloads RESOLVE Ecoregions 2017 (149 MB) once. `pipeline.ice` (see "Tested and not used") is not
part of the run.

## Monthly outlook update (November 2026 to March 2027)

`pipeline.update` does the whole update and is safe to run daily: it refreshes ERA5-Land and the NSO census, then
publishes the newest stage whose data has landed, and does nothing out of season or when that stage is out.
To run it every day at 09:30 on this Mac (a missed run happens at wake; log in `~/Library/Logs/zudrisk-update.log`):

```bash
sed "s|__HOME__|$HOME|g" docs/launchd/mn.zudrisk.update.plist > ~/Library/LaunchAgents/mn.zudrisk.update.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mn.zudrisk.update.plist
```

To stop it: `launchctl bootout gui/$(id -u)/mn.zudrisk.update && rm ~/Library/LaunchAgents/mn.zudrisk.update.plist`.
By hand, the same steps:

ERA5-Land publishes a month about 5 days after it ends. Once it has, re-run with that month:

```bash
uv run python -m pipeline.era5 && uv run python -m pipeline.outlook --through 2026-11
```

`outlook` refuses a stage whose months have not landed and names them; run it again a few days later.
NASA POWER (`pipeline.power`) is no longer scored: it runs 5-6 weeks behind.

## Self-checks

Each step has one, run from local files:

```bash
for m in boundaries http era5 ndvi gldas nso indicators validate export aimags compare asof hindcast outlook trends model power zones seasonal ice calibrate update; do uv run python -m pipeline.$m --check; done; uv run python -m pipeline.score
```

## Tested and not used

- **Iron dzud (`pipeline.ice`)**: ERA5-Land Nov-Feb snowmelt and rain on snow, z against 2001-2020. Against losses,
  soum-winters 2011/12-2024/25: melt rho 0.049, rain on snow 0.018 (n 4688); aimag-winters 2000/01-2024/25: 0.036
  and 0.051 (n 525). Added to the model, held-out soum rho fell 0.372 -> 0.358 and AUC 0.745 -> 0.730 (aimag rho
  rose 0.523 -> 0.542). The rule fixed before the run was to keep them only if both soum figures rose.
  Monthly means may be too coarse: a crust is a one-day thaw, which a month's mean melt hides.
- **SEAS5 seasonal forecast (`pipeline.seasonal`)**: shown on the site as the "Oct + SEAS5" stage; it lowers the
  October stage's skill, so the outlook does not use it.
