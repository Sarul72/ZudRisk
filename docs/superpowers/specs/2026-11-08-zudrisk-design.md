# ZudRisk: design and roadmap

Date: 2026-11-08. Status: **draft, waiting for approval**. Nothing is built yet.
Evidence for every data and method claim is in [docs/research/data-sources.md](../../research/data-sources.md).

## Товч (Mongolian summary)

ZudRisk бол Монгол орны зудын эрсдэлийг сум бүрээр тооцох **судалгааны төсөл** юм. Үр дүнг нэг хуудастай вэб сайт дээр газрын зургаар харуулна.
Мэдээлэл NASA-гийн хиймэл дагуул болон реанализын бүтээгдэхүүнээс авна. Малын тоо, хорогдол Үндэсний статистикийн хорооноос, засаг захиргааны хил geoBoundaries / OpenStreetMap-аас ирнэ.
Эхний хувилбар (v0.1) нэвтрэх эрхгүйгээр ажиллана. Түүгээр 2023/24 оны өвлийн эрсдэлийн зургийг тооцож, бодит хорогдолтой харьцуулна.
Дараагийн шатуудад NASA Earthdata-аар цас, NDVI нэмнэ. Дараа нь ERA5-Land-аар цасны нягт, мөсөн бүрхүүлийн орлуулагч үзүүлэлтийг нэмнэ.
Эцэст нь 2026/27 оны өвлийн урьдчилсан эрсдэлийг тооцно. Google Earth Engine заавал биш, нэмэлт зам болно.

## 1. Intent

Dzud is a winter in which large numbers of livestock die: from deep or crusted snow, extreme cold, or a poor summer that left no pasture and no fat.
Mongolia's agency NAMEM publishes an official dzud risk map each November. Its method is an 11-layer weighted overlay (research §1.1). Its inputs and per-layer scaling are not public in full.

ZudRisk is a **research project**: an open, reproducible estimate of dzud risk per soum, built from public data.
- Every number on the map can be traced to a dataset and a formula.
- The map is checked against what actually happened: NSO's recorded adult livestock losses per soum.

The user's stated constraints:
- Research project, Mongolia, dzud risk.
- NASA data where possible.
- Google Earth Engine if usable; otherwise another path.
- OpenStreetMap for geography.

## 2. Goals, non-goals, anti-goals

**Goals**
1. A soum-level risk score and a five-class map for one winter, from public data. The pipeline is reproducible with one command per step.
2. Hindcasts for past dzud winters (2009/10, 2015/16, 2022/23, 2023/24) plus normal winters for contrast. Each is validated against NSO soum mortality.
3. A static website that shows the map, each soum's indicator breakdown, and the validation result, with text in Mongolian and English.
4. Later: a pre-winter outlook for the coming winter (2026/27), updated monthly through the winter as NAMEM does.

**Non-goals**
- Replacing NAMEM's official map, or issuing warnings to herders.
- Weather forecasting. We use observed and reanalysis data only. NAMEM also uses forecast layers (weight 0.21 combined); we do not.
- Bag-level (sub-soum) results.
- User accounts, a database, or a live backend.

**Anti-goals** (a failure even if it "works")
- A map that looks authoritative but hides that it is climate plus herd size only. Hay reserves and herder capacity explain about half the variance (research §1.4), and the site must say so.
- An index whose weights were tuned until the 2023/24 map looked right, then presented as validated. Weights are fixed before validation, and any fitted weights are cross-validated across winters.
- Any credential in the repo.

## 3. Constraints

- Machine today: macOS, Python 3.14 with `uv`, Node 26. No geospatial Python libraries are installed, and there is no `ee`, no gcloud, no GEE login and no Earthdata login.
- Credentials live outside the repo: `~/.netrc` (Earthdata), `~/.cdsapirc` (Copernicus) and `~/.config/earthengine` (GEE). `.gitignore` blocks `.env`, `*.netrc`, `*credentials*` and `*service-account*.json` from day one.
- Licences require attribution on the site: OCHA COD-AB soums (CC BY-IGO), OSM (ODbL), ERA5-Land (CC-BY). MODIS/GLDAS from NASA carry no restriction.
- MODIS Terra/Aqua shut down late 2026 or early 2027, and S-NPP stopped on 2 Nov 2026. Each satellite product id is a setting, so NOAA-20 VIIRS (`VJ113A2`, `VJ110A1F`, `VJ121A2`) can replace MODIS for 2026/27 onward.
- NASA POWER `SNODP` (snow depth) is unusable: it is flat at 17.33 cm all winter. CHIRPS stops at 50°N. Neither is used.
- User rule: smallest stack. No new dependency for what a few lines do. Dependencies are listed in §6 for approval.

## 4. Method

### 4.1 Spatial unit
- **Soum**: OCHA COD-AB `cod-ab-mng` ADM2, 339 units (330 soums plus 9 Ulaanbaatar districts). The source is NSO and the licence is CC BY-IGO.
  - It carries the same polygons as geoBoundaries ADM2 (same NSO/OCHA source), plus fields geoBoundaries lacks: Cyrillic `adm2_name1`, the parent aimag `adm1_name1`, `adm2_pcode` and `area_sqkm`.
  - Checked 2026-11-08: 335 of 339 soums join to NSO's 5-digit codes by (aimag, soum) Cyrillic name. The rest need the fixes listed in the plan.
  - Builder's call: use this source, replacing geoBoundaries.
- **Ulaanbaatar districts** are shown greyed and excluded from scoring and validation, since herds there are small and peri-urban.
- **Aimag** results are the herd-weighted mean of their soums.
- Gridded inputs are reduced to a soum by the mean of grid cells whose centre falls inside it. A soum with no cell centre inside takes the nearest cell.

### 4.2 Winter and years
- Winter `W = Y/Y+1` runs from 1 November Y to 31 March Y+1.
- Inputs: the summer of Y (July-August), the livestock census of December Y, and the snow and temperature of the winter.
- Outcome: adult losses in calendar year Y+1 divided by stock in Y, in sheep units. This is the convention of Rao 2015 and Nandintsetseg 2018.

### 4.3 Indicators

| id | Indicator | Definition | Direction | Source in v0.1 | Source from v0.2 | Literature r with mortality |
|---|---|---|---|---|---|---|
| `cold` | Winter cold | Nov-Feb mean 2 m air temperature anomaly vs 2001-2020 | colder = riskier | NASA POWER T2M (keyless) | same | −0.35 (Sci Rep 2018), −0.44 (Rao 2015) |
| `snow` | Snow load | Nov-Mar max monthly snow depth, as a z-score vs 2001-2020 | deeper = riskier | — | GLDAS-2.1 `SnowDepth_inst` (v0.2); ERA5-Land `snow_depth` from v0.3 | 0.41 |
| `summer` | Summer pasture | Jul-Aug NDVI anomaly vs 2001-2020 | lower = riskier | — | MODIS MOD13A2 (VIIRS VJ113A2 later) | 0.24 (precip. proxy) |
| `pressure` | Grazing pressure | log of sheep units per km² of soum area | higher = riskier | NSO census + soum area | same | 0.29 |

Sheep units: camel 5, horse 7, cow 6, sheep 1, goat 0.9 (Sci Rep 2018).

Calls made before any validation is run (builder's calls, open to change):
- **Scoring snow product.** It is fixed by latency, not by which product validates better. v0.2 uses GLDAS. From v0.3 ERA5-Land replaces it, because it is updated daily and GLDAS runs about 1.5 months late, which would make an outlook impossible. GLDAS stays as a comparison only.
- **MODIS snow-cover days** are shown on the site as context and carry no weight.
- **`pressure` stays sheep units per km²** until a published NDVI-to-carrying-capacity formula is found and cited. None is in the research yet.

### 4.4 Score
1. Each indicator becomes a z-score, sign-flipped so that higher means riskier, and clipped to ±3.
   - Climate indicators (`cold`, `snow`, `summer`): z against the soum's own 2001-2020 baseline. This is a temporal anomaly.
   - `pressure`: z across all scored soums in that year. This is spatial.
2. `risk = Σ wᵢ·zᵢ / Σ wᵢ` (a weighted mean z) over the indicators available in that version.
   - Weights are the literature correlations: snow 0.41, cold 0.35, pressure 0.29, summer 0.24.
   - They are fixed before any validation is run.
3. Five classes on the weighted mean z, with fixed cuts (builder's call):

   | Class | Weighted mean z |
   |---|---|
   | very low | < −1.0 |
   | low | −1.0 to −0.5 |
   | medium | −0.5 to 0.5 |
   | high | 0.5 to 1.0 |
   | very high | ≥ 1.0 |

   - The labels are the same five that NAMEM uses.
   - A single-hazard extreme is diluted by the mean. For example, snow z = 3 with all else normal gives 0.95 under four indicators, which is "high".
   - This is a known limit of a weighted overlay, and the site says so. v0.5's fitted model is where a non-additive rule would come from.
4. Every soum keeps its per-indicator z values, so the site can show what drove its score.

Fitted weights come only in v0.5 (§7), cross-validated leave-one-winter-out, and are shown beside the fixed-weight result.

### 4.5 Validation
These choices are fixed now, before any number is seen (builder's calls):
- **Target:** raw mortality % (losses ÷ previous stock, sheep units).
- **Secondary target:** excess mortality, meaning raw minus the soum's median over the scored non-dzud winters. Both are reported.
- **Per-winter:** Spearman ρ across soums, at soum and at aimag level, with n reported. Also the share of the top risk quintile's soums that landed in the top mortality quintile.
- **Pooled:** Spearman ρ across every soum-winter of all hindcast winters. This is what the normal winters are for: it asks whether scores rise in dzud years, which per-winter ranking cannot show.
- **Missing data:** soums with missing NSO cells (`..`) are dropped and counted.
- **Normal winters:** the two winters with the lowest national mortality between 2001 and 2024 that are not dzud winters, chosen by that rule before scoring.

The site shows these numbers next to the map. There is no pass bar: the result is reported whether it is good or bad.

**Hindcast vs outlook.** A hindcast uses the whole observed winter, so its validation says nothing about a November outlook.
- Until "as-of" hindcasts exist, the outlook is labelled **unvalidated** on the site. "As-of" means the same winters re-scored using only the data available on 1 Nov, 1 Dec, 1 Jan and so on.
- The as-of runs belong to v0.4.
- From v0.1, every indicator function takes an `as_of` date (default: 31 March) so that v0.4 adds no rework.

## 5. Data access paths

| Path | Needs | Gives | When |
|---|---|---|---|
| Keyless | nothing | POWER T2M, NSO livestock and losses, geoBoundaries | v0.1 |
| NASA Earthdata | free Earthdata Login in `~/.netrc` | MODIS NDVI and snow cover (AppEEARS API), GLDAS snow depth/SWE | v0.2 |
| Copernicus CDS | free CDS account and token in `~/.cdsapirc` | ERA5-Land snow depth, density and daily min/max T (ice-crust proxy) | v0.3 |
| Google Earth Engine (optional) | Cloud project registered noncommercial; 150 EECU-h/month free | the same indicators computed server-side, as a cross-check and a faster path | v0.6 |

The pipeline writes one tidy table per indicator: `soum_id, winter, value`. The source is a setting. Swapping GLDAS for ERA5-Land, MODIS for VIIRS, or the local path for GEE changes nothing downstream.

## 6. Build: what it is made of

These are my calls, open to change.

**Pipeline:** Python run with `uv`. Dependencies, for approval:
- `shapely`: point-in-polygon and area.
- `numpy`.
- `requests`: plain `urllib` is enough for POWER and NSO, so add `requests` only if `earthaccess` pulls it in anyway.

From v0.2:
- `earthaccess` or the AppEEARS REST API.
- `rasterio` or `xarray` + `netCDF4` to read GeoTIFF and NetCDF.

From v0.3: `cdsapi`.

**Site:** one static `site/index.html` with:
- Leaflet 1.9.4 from a CDN.
- An OSM raster basemap.
- One precomputed GeoJSON per winter, with soum polygons simplified to keep the file under about 2 MB.

There is no framework, no build step and no backend.

**Layout:**

```
pipeline/        one script per source and step (boundaries, livestock, power, index, validate)
data/raw/        downloads, gitignored
data/derived/    per-indicator CSVs and per-winter GeoJSON, committed when small
site/            index.html, app.js, data/ (copied GeoJSON)
docs/            research, design (this file), plans
```

**Checks:** one small `pytest`-free self-check per non-trivial step, as `python -m pipeline.<step> --check`. For example, the score function maps known z-scores to known classes, and the NSO parser reads a saved sample response.

**Run locally:** `python3 -m http.server -d site`. Hosting (GitHub Pages or similar) is decided later.

## 7. Roadmap

| Version | Delivers | Needs from you | Done when |
|---|---|---|---|
| **v0.1, keyless hindcast** | boundaries, NSO herds and losses, POWER winter cold, `cold` + `pressure` score for 2023/24, map on the site, validation numbers for 2023/24 | nothing | the map renders in a browser from the committed GeoJSON and the validation table is printed and shown |
| v0.2, NASA snow and pasture | MODIS NDVI `summer`, GLDAS `snow`, MODIS snow-cover days; full four-indicator score; hindcasts 2009/10, 2015/16, 2022/23, 2023/24 plus two normal winters; a winter selector on the site | an Earthdata Login | all six winters scored and validated |
| v0.3, snow quality | ERA5-Land snow depth and density as an alternative `snow`; an ice-crust proxy (thaw-refreeze days on snow, unvalidated, shown as such); a GLDAS vs ERA5-Land comparison | a CDS account | the comparison is written up in `docs/` |
| v0.4, 2026/27 outlook | the pre-winter score: summer 2026 NDVI (VIIRS NOAA-20 if MODIS is gone), census 2025, autumn snow so far; re-run monthly through March 2027; as-of hindcasts (1 Nov, 1 Dec, 1 Jan) that validate each outlook stage | — | the first outlook is on the site with its as-of validation, or labelled unvalidated until then |
| v0.5, fitted weights | regression weights fitted leave-one-winter-out, shown beside the fixed weights | — | both results are on the site with their scores |
| v0.6, GEE path (optional) | the same indicators computed in Earth Engine and compared with the local path | a GEE Cloud project | per-soum differences are reported |

Each version gets its own implementation plan in `docs/superpowers/plans/`, written when the version starts.

**Order decided by the user (2026-11-08): past winters first.** The roadmap runs v0.1 → v0.3 hindcasts before the v0.4 outlook. No partial 2026/27 outlook is rushed out for NAMEM's November date.

## 8. Known risks

- **Snow depth is model output everywhere.** No Mongolia validation was found, and dzud thresholds (5-25 cm) are where models are weakest. Mitigation: use anomalies, not absolute depths; compare two products in v0.3.
- **NSO soum codes may not join to geoBoundaries ADM2.** The join is by name and code and is unverified. Mitigation: v0.1 builds the join table first and lists every soum that fails it.
- **NSO units** are inferred as thousand head. This does not matter for mortality %, which is a ratio.
- **Coarse temperature:** POWER is about 55 × 48 km per cell against an average soum of about 4,700 km². Expect neighbouring soums to share values in v0.1.
- **MODIS continuity:** the switch to VIIRS may shift the NDVI anomaly. Mitigation: VIIRS has its own 2018-2025 baseline, compared with MODIS over the overlap.

## 9. Left to the builder

- Simplification tolerance for the soum polygons.
- Colours for the five classes: sequential, colour-blind safe, with a legend in both languages.
- How the per-soum breakdown is shown: a popup or a side panel.
- File and function names inside `pipeline/`.
