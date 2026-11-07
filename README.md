# ZudRisk

An open, reproducible estimate of dzud (зуд) risk for every soum of Mongolia, built from public
data: Copernicus ERA5-Land winter temperature and snow, NASA MODIS summer NDVI, NSO livestock counts and
losses, OCHA COD-AB soum boundaries. Research hindcasts plus a monthly 2026/27 outlook, not a warning. Design: `docs/superpowers/specs/2026-11-08-zudrisk-design.md`.

## Run

Needs `uv`. v0.1 sources are public. From v0.2 the snow (GLDAS) and NDVI (MODIS) steps need a free
NASA Earthdata Login in `~/.netrc` (`machine urs.earthdata.nasa.gov login ... password ...`, mode 600),
with the "NASA GESDISC DATA ARCHIVE" application approved in the Earthdata profile. From v0.3 the ERA5-Land
step needs a free Copernicus CDS account: `~/.cdsapirc` with `url: https://cds.climate.copernicus.eu/api` and
`key: <API Token from your CDS profile>`, and the ERA5-Land licence accepted on the dataset page.

```bash
uv sync
uv run python -m pipeline.boundaries          # OCHA COD-AB soums -> data/derived/soums.geojson
uv run python -m pipeline.nso                 # NSO herds and losses -> data/derived/livestock.csv
uv run python -m pipeline.era5                # ERA5-Land t2m, snow depth/density/cover, Nov-Mar, to the latest month (CDS)
uv run python -m pipeline.gldas               # GLDAS-2.1 snow depth, for the snow comparison only (Earthdata)
uv run python -m pipeline.ndvi                # MODIS MOD13C2 NDVI, Jul-Aug 2001 to the latest summer (Earthdata)
uv run python -m pipeline.hindcast            # 15 winters scored (2009/10, 2011/12-2024/25), the pre-registered
                                              # pooled test, snow comparison, as-of stages, greenness trend
                                              # (pipeline.trends) and the learned vulnerability model (pipeline.model)
uv run python -m pipeline.zones              # natural zones from RESOLVE Ecoregions 2017 (downloads 149 MB once)
uv run python -m pipeline.nso --hay           # NSO hay laid in per aimag (the model's hay_per_su), livestock untouched
uv run python -m pipeline.outlook --through 2026-10   # the 2026/27 outlook at its latest stage
python3 -m http.server -d site 8765           # open http://localhost:8765
```

## Monthly outlook update (November 2026 to March 2027)

ERA5-Land publishes a month about 5 days after it ends. Once it has, re-run with that month:

```bash
uv run python -m pipeline.era5 && uv run python -m pipeline.outlook --through 2026-11
```

`outlook` refuses a stage whose months have not landed and names them; run it again a few days later.
NASA POWER (`pipeline.power`) is no longer scored: it runs 5-6 weeks behind.

Self-checks (no network): `uv run python -m pipeline.<step> --check` for every step except `score`,
which runs its check with no flag.
