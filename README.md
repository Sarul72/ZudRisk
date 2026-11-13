# ZudRisk

An open, reproducible estimate of dzud (зуд) risk for every soum of Mongolia, built from public data:
- Copernicus ERA5-Land winter temperature and snow;
- NASA MODIS summer NDVI;
- NSO livestock counts and losses;
- OCHA COD-AB soum boundaries;
- the Environmental Information Center's hayland and pasture map (Байгаль орчны мэдээллийн сан, eic.mn), for
  each soum's pasture area. Only the derived shares are published (`data/derived/soum_pasture.csv`), citing EIC.

It covers research hindcasts of 25 winters (2000/01-2024/25) plus a 2026/27 outlook updated monthly. It is not a
warning.

Online: <https://sarul72.github.io/ZudRisk/> (GitHub Pages serves `site/`; see "Publishing").

## What the site shows

The side panel has three tabs: the map (a status card naming the winter shown, with a jump to the 2009/10 dzud and
back, then the legend and the zone and aimag tables), results (the validation) and method (a short introduction, the
model, weights, limits and sources). The default basemap is Esri's light grey canvas; the site falls back to
OpenStreetMap by itself if those tiles do not load. `node --test "tests/site/*.test.js"` checks the page's structure and
its small decisions (`site/ui.js`).

- **Risk** per soum, aimag or natural zone for any winter: four indicators (cold, snow, summer pasture, grazing
  pressure) as z-scores, weighted into one score and five classes. Grazing pressure is sheep units per km² of
  pasture: the soum less EIC's "other land" (large lakes, closed forest), 4.5 % of the country.
- **Chance** of adult losses of 5 % or more. The map is coloured by it at soum and aimag level; the five classes stay
  one click away ("Өнгө / Colour"). Soums are calibrated per outlook stage on 2011/12-2024/25, aimags on their own
  525 aimag-winters 2000/01-2024/25. A stage whose held-out Brier skill is 0 or below shows classes, not a chance.
- **Vulnerability** from a small learned model, replaying 20 winters' weather on today's herds.
- **Greenness trend** (desertification) and five natural zones from Mongolia's natural zoning map
  (`data/source/naturalzone`). Desert steppe is counted in the desert (gobi) zone by our choice, for Resolution 286's
  gobi snow thresholds; the map has it in the steppe zone, and the site says so.
- **Resolution 286** (main criteria): which of the official procedure's dzud types each soum met in a winter month,
  from ERA5-Land depth, temperature and the summer before. Density, the auxiliary criteria and the dekad step are not
  assessed, and the site says so; it is not an official assessment. Losses >= 5 % followed in 37 % of the soum-winters
  flagged white and 11 % of those flagged nothing. Of the soums NAMEM named in white dzud, 4 % are flagged white here
  and 64 % white or moderate (`pipeline.decree286`, `pipeline.official`).
- **Validation** beside every map: how each winter and each outlook stage ranked the losses that followed.

## How well it works (2026-11-13)

Spearman rho of the risk score against adult livestock mortality:

| Test | rho | n |
|---|---|---|
| Pre-registered winters, soum level (2013/14, 2015/16, 2021/22-2023/24) | 0.600 | 1683 |
| Every soum-winter with losses, 2011/12-2024/25 | 0.440 | 4688 |
| Every aimag-winter, 2000/01-2024/25 | 0.544 | 525 |
| Outlook stage, pre-registered winters: Oct / Nov / Dec / Jan / Feb / Mar | 0.23 / 0.50 / 0.64 / 0.64 / 0.60 / 0.60 | 1683 |

The learned model ranks below the fixed weights when each winter is held out: soum rho 0.373 against 0.440, and AUC
0.745 against 0.762. The site says so. October, before any winter weather, is the weakest stage.

## Docs

- [plan.md](plan.md): what next, ranked, and what this round did.
- [Design and roadmap](docs/superpowers/specs/2026-11-08-zudrisk-design.md): the method and why.
- [Data sources](docs/research/data-sources.md): the research behind every input.
- [EIC data options](docs/research/eic-data-options.md): what eic.mn publishes and what ZudRisk and hazard can use (in Mongolian).
- [Official dzud lists](docs/research/official-dzud-lists.md): where soums named in dzud or near-dzud are published (in
  Mongolian); the lists found are in `data/source/dzud_official_lists.csv`, matched to soums by `pipeline.official`.
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
uv run python -m pipeline.pasture             # EIC pasture map -> each soum's pasture share (data/derived/soum_pasture.csv)
uv run python -m pipeline.era5                # ERA5-Land t2m, snow depth/density/cover, Nov-Mar, to the latest month (CDS)
uv run python -m pipeline.gldas               # GLDAS-2.1 snow depth, for the snow comparison only (Earthdata)
uv run python -m pipeline.ndvi                # MODIS MOD13C2 NDVI, Jul-Aug 2000 to the latest summer (Earthdata)
uv run python -m pipeline.summer              # ERA5-Land May-Aug precipitation and temperature (CDS)
uv run python -m pipeline.seasonal --fetch && uv run python -m pipeline.seasonal  # SEAS5 1 October forecasts (CDS);
                                              # before hindcast, which tests them as the "Oct + SEAS5" stage
uv run python -m pipeline.hindcast            # natural zones, 25 winters scored, the pooled tests, snow comparison,
                                              # outlook stages, chance calibration, greenness trend and the model
uv run python -m pipeline.outlook --through 2026-10   # the 2026/27 outlook at its latest stage
python3 -m http.server -d site 8765           # open http://localhost:8765 (on Windows: START_SITE.bat)
```

`pipeline.zones` reads the natural zoning map in `data/source/naturalzone`. `pipeline.ice` (see "Tested and not used") is not
part of the run.

## Monthly outlook update (November 2026 to March 2027)

`pipeline.update` does the whole update and is safe to run daily: it refreshes ERA5-Land and the NSO census, then
publishes the newest stage whose data has landed, and does nothing out of season or when that stage is out. After it
publishes, it commits `site/data` alone and pushes it, so the online site follows (`--no-push` skips the push).

On Windows, to run it every day at 09:30 (Git must be able to push without asking, as Git for Windows' credential
manager does after one `git push` by hand):

```bat
schtasks /Create /SC DAILY /ST 09:30 /TN ZudRiskUpdate /TR "cmd /c cd /d %CD% && uv run python -m pipeline.update >> %LOCALAPPDATA%\zudrisk-update.log 2>&1"
```

Run it from the ZudRisk folder. To stop it: `schtasks /Delete /TN ZudRiskUpdate /F`.

To run it every day at 09:30 on a Mac (a missed run happens at wake; log in `~/Library/Logs/zudrisk-update.log`):

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

## Publishing

`.github/workflows/pages.yml` deploys `site/` to GitHub Pages on every push to `main` that changes it. Once, in the
repository on GitHub: Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**. Nothing under
`data/raw/` and no credential is committed (`.gitignore`); `site/` is about 14 MB of Pages' 1 GB.

## Self-checks

Each step has one, run from local files:

```bash
for m in boundaries http era5 ndvi gldas nso indicators validate export aimags compare asof hindcast outlook trends model power zones seasonal ice calibrate update herdmix thaw summer decree286 official pasture; do uv run python -m pipeline.$m --check; done; uv run python -m pipeline.score
```

## Tested and not used

- **Iron dzud (`pipeline.ice`)**: ERA5-Land Nov-Feb snowmelt and rain on snow, z against 2001-2020. Against losses,
  soum-winters 2011/12-2024/25: melt rho 0.049, rain on snow 0.018 (n 4688); aimag-winters 2000/01-2024/25: 0.036
  and 0.051 (n 525). Added to the model, held-out soum rho fell 0.372 -> 0.358 and AUC 0.745 -> 0.730 (aimag rho
  rose 0.523 -> 0.542). The rule fixed before the run was to keep them only if both soum figures rose.
  Monthly means may be too coarse: a crust is a one-day thaw, which a month's mean melt hides.
- **Herd composition (`pipeline.herdmix`)**: each species' share of the census in sheep units (camel, horse, cattle,
  goat; sheep the reference) added to the model. Held-out soum rho fell 0.372 -> 0.352 and AUC 0.745 -> 0.732
  (aimag rho rose 0.523 -> 0.538). The rule fixed before the run was to keep them only if both soum figures rose.
- **SEAS5 seasonal forecast (`pipeline.seasonal`)**: shown on the site as the "Oct + SEAS5" stage; it lowers the
  October stage's skill, so the outlook does not use it.

## Waiting for data

- **Iron dzud from daily data (`pipeline.thaw`)**: thaw days on snow, Nov-Feb, from ERA5-Land daily maxima (UTC+8).
  The code and its test are in; the 100 CDS requests are not, since they need the CDS account. Run
  `uv run python -m pipeline.thaw --fetch` (hours; it resumes), then `uv run python -m pipeline.thaw`, which prints the
  verdict under the same rule as the monthly test.
