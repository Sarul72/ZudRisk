# ZudRisk: data sources and methods for a dzud risk map

Researched 2026-11-08. Every claim carries its source URL. "Checked live" means a request was
sent to the endpoint on that date and the answer is quoted. "Not verified" means no primary
source confirmed it.

## Summary

**Inputs.** Use the five inputs that NAMEM's own map and the peer-reviewed models share:
1. Previous summer's pasture: July-August NDVI anomaly.
2. Snow: depth or SWE, plus snow-cover onset and days.
3. Winter cold: November-February temperature anomaly.
4. Grazing pressure: livestock in sheep units against carrying capacity.
5. Ice crust: no direct product exists, so use a thaw-refreeze proxy.

Validate against NSO's soum-level "losses of adult animals". The sources are in sections 1 and 3.

**GEE path.**
- NDVI: `MODIS/061/MOD13A3` (or `MOD13A2`).
- Snow cover: `MODIS/061/MOD10A1`.
- Snow and temperature: `ECMWF/ERA5_LAND/DAILY_AGGR`, with `NASA/GLDAS/V021/NOAH/G025/T3H` and `NASA/FLDAS/NOAH01/C/GL/M/V001` as the NASA alternatives.
- Land surface temperature: `MODIS/061/MOD11A2`.
- Boundaries: `FAO/GAUL/2025/level2` (CC BY 4.0) or geoBoundaries uploaded as an asset.
- Livestock: NSO soum table uploaded as a CSV asset.

**No-GEE path.**
- MODIS/VIIRS: NASA AppEEARS API, area task with the Mongolia polygon, GeoTIFF output. Needs a free Earthdata Login. Alternative: `earthaccess` or CMR-STAC to fetch the HDF tiles.
- Temperature: NASA POWER API. No key needed. Regional boxes are limited to 10°×10°, one parameter per request.
- Snow depth/SWE: ERA5-Land from the Copernicus CDS (free account and token, CC-BY), or GLDAS-2.1 Early Product from GES DISC (Earthdata Login, about 1.5-month latency).
- Livestock and losses: NSO PxWeb API at `data.1212.mn` (no login).
- Boundaries: geoBoundaries `MNG` ADM1/ADM2 (OSM/ODbL and NSO/OCHA, CC BY 3.0 IGO), or OSM `admin_level` 4/6 via Overpass or Geofabrik.

**Avoid.**
- POWER `SNODP`: checked live, it flat-lines at 17.33 cm all winter.
- CHIRPS: its northern edge is 50°N, so it misses the north of Mongolia.
- Terra/Aqua MODIS: shutting down "late 2026/early 2027". Plan the VIIRS NOAA-20 (`VJ1*`) continuity products now (section 2.6).

---

## 1. How dzud risk is computed

### 1.1 NAMEM / IRIMHE dzud risk map (the official product)

Source: IRIMHE/NAMEM slides, "Dzud early warning system over Mongolia", Davaadorj et al., 5th EASCOF, Tokyo, Nov 2017.
<https://ds.data.jma.go.jp/gmd/tcc/tcc/library/EASCOF/2017/P3-4.pdf>

- **Method:** GIS multi-criteria decision analysis (MCDA): rank each layer, standardise it, weight it, then overlay the weighted layers. Output is five classes: very high, high, medium, low and very low (slides 12-13).
- **Weights:** rank-sum, `W_i = (n − r_k + 1) / Σ_k (n − r_k + 1)` with n = 11 layers (slide 13, formula and table).
- **Timing:** the slide says the map "was produced on 20 Oct, 20 Nov and 31 Dec. in 2015". It is presented to Government by end of November and updated monthly through winter (slides 12 and 17).
- **Map unit:** the 2017/18 map is drawn as a raster within soum boundaries (slide 14).

| # | Layer (as named on slide 13) | Rank | Weight |
|---|---|---|---|
| 1 | Summer condition | 3 | 0.09 |
| 2 | Pasture carrying capacity | 2 | 0.10 |
| 3 | Livestock number | 3 | 0.09 |
| 4 | Biomass / 1500 site (ground plots) | 2 | 0.10 |
| 5 | Anomalous precipitation | 5 | 0.07 |
| 6 | Anomalous temperature | 5 | 0.07 |
| 7 | Drought index / MODIS | 4 | 0.08 |
| 8 | Snow depth | 1 | 0.11 |
| 9 | Snow cover / MODIS | 3 | 0.09 |
| 10 | Air temperature forecast | 2 | 0.10 |
| 11 | Precipitation forecast | 1 | 0.11 |

Read the weights this way:
- Snow depth and the precipitation forecast weigh most (0.11 each).
- Carrying capacity, biomass and the temperature forecast follow (0.10 each).
- Past temperature and precipitation anomalies weigh least (0.07 each).

**Carrying capacity map.** A pasture carrying capacity map (2017-18 winter-spring, per bag) gives load as % of capacity in five classes. Source: slide 8 legend, read from Mongolian.

| Load (% of capacity) | Legend meaning |
|---|---|
| 0-50 % | pasture in reserve |
| 50-100 % | sufficient |
| 100-300 % | capacity exceeded 1-3× |
| 300-500 % | capacity exceeded 3-5× |
| >500 % | exceeded many times |

**Defining parameters.** Slide 6 lists: previous summer condition, pasture carrying capacity, time of snow-cover formation, depth of snow cover, snow density, number of days with snow cover, and air temperature.

**Not verified:**
- Whether the 2017 weights still apply to the current (2025/26) map.
- How each layer is standardised to its 0-100 scale.
- A public URL where the current map is published. `namem.gov.mn` and `irimhe.namem.gov.mn` answer HTTP 200 (checked live), but no map page was found.

### 1.2 Government definitions of dzud types (Resolution 286)

Source: Mongolian Red Cross Society, *Forecast-Based Financing Early Action Protocol: Dzud*, updated 08/10/2019, p. 1. The protocol quotes "the 286th resolution by the Mongolian government".
<https://adore.ifrc.org/Download.aspx?FileId=261683>

| Type | Threshold (as quoted in the EAP) |
|---|---|
| White | snow density ≥ 0.25 g/cm³ for ≥ 10 days, monthly mean T ≥ 3.0 °C below normal, depth > 25 cm (high mountain / forest steppe), > 22 cm (steppe), > 12 cm (desert) |
| Near-white | density 0.20-0.24 g/cm³, depth > 16 cm / > 11 cm / > 5 cm for the same three zones |
| Black | harsh summer, no winter precipitation for 10 days, monthly T ≥ 3.0 °C below normal |
| Near-black | as black, with low precipitation and T ≥ 2.0 °C below normal |
| Iron / ice | top layer or core of the snowpack frozen to ice, or density ≥ 0.35 g/cm³ |

The same EAP sets these terms (pp. 1-2):
- **Trigger:** "20% of 3 or more provinces" in the highest risk class of the NAMEM map.
- **Map timing:** NAMEM publishes the map "in mid to late November" and updates it monthly. It is "jointly produced by the University of Nagoya".
- **Unit count:** Mongolia has 331 soums.

These thresholds give the website a physically defined label set. The snow-depth zones, density and temperature anomaly are all derivable from ERA5-Land, which carries a `snow_density` band (section 2).

### 1.3 Peer-reviewed models

**Tachiiri, Shinoda, Klinkenberg & Morinaga (2008).** "Assessing Mongolian snow disaster risk using livestock and satellite data", *J. Arid Environments* 72(12):2251-2263. <https://doi.org/10.1016/j.jaridenv.2008.06.015> (metadata via <https://api.openalex.org/works/doi:10.1016/j.jaridenv.2008.06.015>)
- **Method:** regression tree.
- **Predictors:** NDVI, SWE, and the previous year's livestock numbers and mortality.
- **Finding:** high mortality followed low August NDVI, high December SWE, and large high-mortality herds the year before.
- **Limits:** the model covers white dzud only, and cross-validation error was large.
- **Not verified:** the publisher page returned 403, so this summary comes from a search-index abstract. The SWE and NDVI source sensors are also unconfirmed.

**Rao et al. (2015).** "Dzuds, droughts, and livestock mortality in Mongolia", *Environ. Res. Lett.* 10:074012, CC BY 3.0. <https://doi.org/10.1088/1748-9326/10/7/074012> (read at <https://iopscience.iop.org/article/10.1088/1748-9326/10/7/074012>)
- **Data:** aimag mortality 1955-2013 from the NSO December census; climate from CRU TS 3.21; PDSI from published datasets.
- **Method:** stepwise regression per aimag with AIC selection. Median adjusted R² is 48.4 %.
- **Strongest predictor:** November-February mean temperature. Mean mortality correlates with it at r = −0.44.
- **Secondary predictor:** July-September PDSI, precipitation and PET. These matter more in the south and west.
- **Snow:** excluded, because "reliable snow and wind data" are lacking.
- **Trigger statistic:** the 6 % index-insurance trigger is exceeded in 26 % of years.

**Nandintsetseg, Shinoda, Erdenetsetseg (2018).** "Contributions of multiple climate hazards and overgrazing to the 2009/2010 winter disaster in Mongolia", *Natural Hazards* 92(S1):109-126. <https://doi.org/10.1007/s11069-017-2954-8>
- **Method:** a regression tree on cold, heavy snow and an overgrazing rate explains 58 % of the spatial variation in 2009/10 mortality.
- **Finding:** areas with spare pasture capacity in the north and east had low mortality even under extreme cold and snow.
- **Not verified:** these points come from a search summary of the abstract; the publisher page redirected to a login. The exact overgrazing-rate formula is also unread.

**Nandintsetseg, Shinoda, Du, Munkhjargal (2018).** "Cold-season disasters on the Eurasian steppes: Climate-driven or man-made", *Sci. Rep.* 8:14769. <https://doi.org/10.1038/s41598-018-33046-1>. Full text read at Europe PMC PMC6170381: <https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6170381/fullTextXML>.
- **Scope:** aimag-level regression for 2000-2014 cold seasons, with mortality from NSO.
- **Hazard indicators** (Table 1; r = correlation with livestock deaths):

  | Indicator | Definition | r |
  |---|---|---|
  | P6-8 | June-August precipitation anomaly % | −0.24 |
  | T11-2 | November-February mean temperature anomaly | −0.35 |
  | SD | monthly maximum snow depth, November-March | 0.41 |

- **Vulnerability indicators:**
  - previous-year livestock in sheep units (r = 0.29);
  - previous-year losses;
  - herder age structure and herd-size classes;
  - trucks;
  - hay/forage preparedness;
  - GDP.
- **Sheep units:** camel 5, horse 7, cow 6, sheep 1, goat 0.9.
- **Result:** 93.5 % of mortality is explained, split into multi-hazards 47.3 % and vulnerability 46.2 %.
- **Low-mortality regions:** snow depth contributes 17.3 % and winter temperature 16.1 %, against drought 10.4 %.

**Nandintsetseg et al. (2021).** "Risk and vulnerability of Mongolian grasslands under climate change", *Environ. Res. Lett.* 16:034035. <https://doi.org/10.1088/1748-9326/abdb5b>
- **Scope:** a grid-scale (0.5°) drought risk for grassland, not for livestock.
- **Formula:** risk = P(hazardous drought, from SPEI) × vulnerability.
- **Vulnerability:** the expected loss of productivity or soil moisture between hazard and no-hazard years.
- **Use for ZudRisk:** a formula template for the summer component.

**Middleton, Rueff, Sternberg, Batjav & Thomas (2015).** "Explaining spatial variations in climate hazard impacts in western Mongolia", *Landscape Ecology* 30(1):91-107. <https://doi.org/10.1007/s10980-014-0091-2> (metadata via OpenAlex)
- **Method:** a qualitative and mixed study of one western province: questionnaire, interviews, station data and two satellite datasets.
- **Finding:** losses are explained by site-specific circumstances, including a lack of alternative income.
- **Use for ZudRisk:** it gives no formula. Cite it as the caution that soum-scale losses carry non-climate noise.
- **Not verified:** abstract details beyond the search summary.

### 1.4 What matters most (synthesis)

| Input | Evidence | Weight to start with |
|---|---|---|
| Snow depth / SWE | NAMEM highest weight 0.11; Sci Rep 2018 strongest hazard r = 0.41; Tachiiri December SWE | high |
| Winter cold (Nov-Feb anomaly) | Rao 2015 strongest national predictor; Sci Rep 2018 r = −0.35 | high |
| Grazing pressure (sheep units vs carrying capacity) | NAMEM PCC + livestock = 0.19 combined; Nat. Hazards 2018 overgrazing rate; Sci Rep r = 0.29 | high |
| Summer pasture (NDVI / drought / biomass) | NAMEM summer + biomass + drought = 0.27 combined; Tachiiri August NDVI; Rao regional | medium-high |
| Ice crust | Resolution 286 iron-dzud definition (density ≥ 0.35 g/cm³); no satellite product found | proxy only |

Two things lower confidence:
- Hay/forage preparedness and herder capacity explain much of the variance (Sci Rep 2018), but they have no open gridded source.
- A climate-only map will miss that part of the variance. Say so on the website.

---

## 2. Datasets per input

Notes for all tables:
- "EDL" = free NASA Earthdata Login (<https://urs.earthdata.nasa.gov>).
- GEE facts come from each catalog page, read 2026-11-08.
- "Latest" = the newest granule in NASA CMR on 2026-11-08 (checked live via `cmr.earthdata.nasa.gov/search/granules.json`).
- Mongolia spans about 87-120°E and 41.5-52.2°N.

### 2.1 Vegetation / summer pasture

| Product | ID | Provider | Res. | Period | Latency | GEE ID | No-GEE access |
|---|---|---|---|---|---|---|---|
| MODIS Terra VI 16-day | MOD13A2 v061, DOI 10.5067/MODIS/MOD13A2.061 | LP DAAC | 1 km, 16 d | 2000-02-18 → | composite of 2026-10-16 produced 2026-11-03 (file stamp 2026307) | `MODIS/061/MOD13A2` | AppEEARS, CMR-STAC `.../stac/LPCLOUD/collections/MOD13A2_061`, HTTPS `data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/` (EDL) |
| MODIS Terra VI monthly | MOD13A3 v061 | LP DAAC | 1 km, monthly | 2000-02-01 → | GEE has 2026-10-01 | `MODIS/061/MOD13A3` | same as above |
| MODIS Terra VI 250 m | MOD13Q1 v061 | LP DAAC | 250 m, 16 d | 2000 → | not verified | `MODIS/061/MOD13Q1` (not verified) | same as above |
| VIIRS NOAA-20 VI (continuity) | VJ113A2 v002 | LP DAAC | 1 km, 16 d | 2018-01-01 → | not verified | not verified | AppEEARS / earthaccess (EDL) |
| VIIRS S-NPP VI | VNP13A1 v002 | LP DAAC | 500 m | 2012-01-17 → | **S-NPP stopped new data** | `NASA/VIIRS/002/VNP13A1` | EDL |

Sources:
- MOD13A2 on GEE (NDVI scale 0.0001; LP DAAC MODIS data "no restrictions on subsequent use, sale, or redistribution"): <https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A2>
- MOD13A2 on Earthdata: <https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13a2-061>
- MOD13A3: <https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A3>
- VNP13A1: <https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP13A1>
- VJ113A2 and VNP13A2: CMR collections `C2519122898-LPCLOUD` and `C2519127613-LPCLOUD`.
- AppEEARS API: <https://appeears.earthdatacloud.nasa.gov/api/>. It takes a GeoJSON polygon, returns GeoTIFF or NetCDF4, uses an EDL Basic login that returns a Bearer token valid about 48 h, and answers 429 when rate-limited.

### 2.2 Snow cover, depth, SWE

| Product | ID | Provider | Res. | Period | Latency | GEE ID | No-GEE access |
|---|---|---|---|---|---|---|---|
| MODIS Terra snow cover daily | MOD10A1 v61 | NSIDC | 500 m, daily | 2000-02-24 → | "a few days"; CMR latest 2026-11-05 | `MODIS/061/MOD10A1` | EDL: NSIDC tool, earthaccess, HTTPS, AppEEARS |
| MODIS snow cover monthly CMG | MOD10CM v61 | NSIDC | 0.05°, monthly | 2000-03-01 → | not verified | not found in GEE (not verified) | EDL, same tools |
| VIIRS NOAA-20 snow, cloud-gap-filled | VJ110A1F v2 | NSIDC | 375 m, daily | 2018-01-05 → | not verified | not verified | EDL |
| GLDAS-2.1 Noah 3-hourly | GLDAS_NOAH025_3H(_EP) v2.1 | GES DISC | 0.25°, 3 h | 2000-01-01 → | Early Product about 1.5 months; main stream 3-4 months; GEE end 2026-10-15 | `NASA/GLDAS/V021/NOAH/G025/T3H` | EDL: HTTPS / OPeNDAP / earthaccess |
| FLDAS Noah global monthly | FLDAS_NOAH01_C_GL_M v001 | GES DISC | 0.1°, monthly | 1982-01 → | latest 2026-09 | `NASA/FLDAS/NOAH01/C/GL/M/V001` | EDL |
| MERRA-2 land diagnostics | M2T1NXLND / M2TMNXLND 5.12.4 | GES DISC (GMAO) | 0.5°×0.625°, hourly / monthly | 1980 → | "~3 weeks after the end of a month" | not verified | EDL |
| SMAP L4 soil moisture | SPL4SMGP v008 | NSIDC | 9 km, 3 h | 2015-03-31 → | not stated; 14 May-28 Jul 2026 being reprocessed | `NASA/SMAP/SPL4SMGP/008` | EDL, AppEEARS |
| ERA5-Land (non-NASA) | reanalysis-era5-land, DOI 10.24381/cds.e2161bac | ECMWF / C3S | 0.1° (9 km native), hourly | 1950-01 → | CDS "updated daily"; GEE daily ends 2026-10-31 | `ECMWF/ERA5_LAND/DAILY_AGGR` | CDS account + token, `cdsapi`, accept the licence per dataset; CC-BY |

Snow variables and notes:
- **MOD10A1:** `NDSI_Snow_Cover` plus QA bands. A Lights-Out Operations note says data from 7 July 2023 on may suffer more loss.
- **GLDAS:** `SWE_inst` and `SnowDepth_inst`, plus `Tair_f_inst` and soil moisture.
- **FLDAS:** `SWE_inst`, `SnowDepth_inst`, `SnowCover_inst`, `Snowf_tavg` and `Tair_f_tavg`.
- **MERRA-2:** SNODP and SNOMAS in M2T1NXLND. Not verified from the variable list.
- **SMAP L4:** GEE lists `snow_mass` and `snow_depth` bands. NSIDC lists only soil moisture as products.
- **ERA5-Land:** `snow_depth`, `snow_depth_water_equivalent`, `snow_cover`, `snow_density` and `temperature_2m` (min/max).

Sources:
- MOD10A1: <https://nsidc.org/data/mod10a1/versions/61> and <https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD10A1>
- MOD10CM: <https://nsidc.org/data/mod10cm/versions/61>
- VJ110A1F: CMR `C3173454072-NSIDC_CPRD`.
- GLDAS:
  - <https://developers.google.com/earth-engine/datasets/catalog/NASA_GLDAS_V021_NOAH_G025_T3H>
  - Latency text from CMR abstract `GLDAS_NOAH025_3H_EP`: <https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GLDAS_NOAH025_3H_EP>
- FLDAS: <https://developers.google.com/earth-engine/datasets/catalog/NASA_FLDAS_NOAH01_C_GL_M_V001>. The CMR abstract says it is "forced by a combination of" MERRA-2 and CHIRPS.
- MERRA-2 latency: CMR abstract of M2T1NXSLV.
- SMAP: <https://nsidc.org/data/spl4smgp/versions/8> and <https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008>
- ERA5-Land:
  - <https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land>
  - <https://cds.climate.copernicus.eu/how-to-api>
  - <https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR>. This page says data run "to three months from real-time" while its end date was 2026-10-31. It also lists cadence as "1 Month". Both fields are inconsistent with a daily collection.

**Which snow products are reliable over Mongolia?**
- **Snow cover:** MODIS or VIIRS snow cover is direct observation, at 500 m or 375 m. It suits the "snow-cover onset" and "days with snow cover" layers that NAMEM uses.
- **Snow depth and SWE:** every option is model or reanalysis output (GLDAS, FLDAS, MERRA-2, ERA5-Land, SMAP L4). No Mongolia-specific validation was found, so this is **not verified**.
- **Shallow snow:** Mongolian dzud thresholds are 5-25 cm (section 1.2). That is the range where coarse models and passive microwave are weakest.
- **Recommendation:** use the depth products as anomalies (z-scores against 2000-2025), not as absolute thresholds. Cross-check against NAMEM station snow depth if it can be obtained; that is not verified as openly available.
- **NASA POWER `SNODP`** is unusable (section 2.4).

### 2.3 Winter cold (air temperature, LST)

| Product | ID | Provider | Res. | Period | Latency | GEE ID | No-GEE access |
|---|---|---|---|---|---|---|---|
| MODIS Terra LST 8-day | MOD11A2 v061 | LP DAAC | 1 km, 8 d | 2000-02-18 → | CMR latest 2026-10-24 | `MODIS/061/MOD11A2` | AppEEARS / earthaccess (EDL) |
| VIIRS NOAA-20 LST 8-day | VJ121A2 v002 | LP DAAC | 1 km, 8 d | 2018-01-01 → | not verified | not verified | EDL |
| MERRA-2 single level | M2T1NXSLV 5.12.4 (T2M) | GES DISC | 0.5°×0.625°, 1 h | 1980 → | about 3 weeks after month end | `NASA/GSFC/MERRA/slv/2` | EDL; or keyless through POWER |
| NASA POWER (MERRA-2 derived) | T2M, T2M_MIN, T2M_MAX, FROST_DAYS, PRECTOTCORR | NASA LaRC | 0.5°×0.625° (MERRA-2 cell) | 1981 → | checked live: data to 2026-11-04, −999 after | none | REST, no key |
| ERA5-Land | `temperature_2m` | ECMWF | 0.1° | 1950 → | daily | `ECMWF/ERA5_LAND/DAILY_AGGR` | CDS |
| GLDAS / FLDAS | `Tair_f_inst` / `Tair_f_tavg` | GES DISC | 0.25° / 0.1° | see 2.2 | see 2.2 | see 2.2 | EDL |

Sources:
- MOD11A2: <https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2>
- MERRA-2 on GEE: <https://developers.google.com/earth-engine/datasets/catalog/NASA_GSFC_MERRA_slv_2>
- VJ121A2: CMR collection search.
- LST is skin temperature under clear sky, so it is biased in cloudy cold spells. Air-temperature anomaly is what the literature uses (Rao 2015, Sci Rep 2018).

### 2.4 NASA POWER specifics (no login)

Docs: <https://power.larc.nasa.gov/docs/services/api/> and <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>.

**Request shapes:**
- Point: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MIN&community=AG&longitude=106.9&latitude=47.9&start=YYYYMMDD&end=YYYYMMDD&format=JSON`
- Regional: `.../daily/regional?latitude-min=..&latitude-max=..&longitude-min=..&longitude-max=..&parameters=T2M&community=AG&start=..&end=..&format=CSV`

**Limits:**
- Point requests take at most 20 parameters; regional requests take 1 (docs).
- Checked live: a Mongolia-wide box was refused with "Please provide a maximum of 10 degree range in latitude" (same for longitude). Covering Mongolia needs about 4 × 2 tiles.
- HTTP 429 means "Too Many Requests" (docs). No key was needed for any request (checked live).

**Source:** the response header says `"sources":["MERRA2","POWER"]`, and the CSV header says "elevation from MERRA-2: Average for 0.5 x 0.625 degree" (checked live).

**SNODP is not usable.** Checked live at 106.9E 47.9N and 100.0E 47.5N:
- 2023-11-01 to 2024-03-31: every day returned exactly 17.33 cm.
- Summer: values were 0.
- Nov 2010: values were 17.10-17.33.

The values appear capped. Treat POWER snow depth as **unusable** for dzud snow.

### 2.5 Precipitation / drought

| Product | ID | Res. | Period | GEE ID | No-GEE | Mongolia caveat |
|---|---|---|---|---|---|---|
| CHIRPS daily | UCSB-CHG CHIRPS v2 | 0.05° | 1981-01-01 → (GEE end 2026-09-30) | `UCSB-CHG/CHIRPS/DAILY` | CHC data server (not verified) | bounding box −50 to 50 latitude, so north of 50°N is missing |
| ERA5-Land / MERRA-2 / FLDAS precipitation | see above | | | see above | see above | full coverage |
| SPEI (used by Nandintsetseg 2021) | | | | not verified | not verified | |

CHIRPS source: <https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY>.

### 2.6 MODIS end of life

- Terra and Aqua "will begin shutting down operations in late 2026/early 2027". A final MODIS reprocessing will follow. Source: <https://www.earthdata.nasa.gov/data/alerts-outages/transition-from-modis-viirs>
- Suomi NPP "is no longer delivering new data". A linked alert gives 2 Nov 2026 as the date new observations ceased (same page). The MOD13A2 Earthdata page carries the same banner.
- **Consequence:** build the NDVI, snow and LST layers so the product ID is a setting. Use the MODIS record for the 2000-2025 baseline, and the NOAA-20 `VJ113A2` / `VJ110A1F` / `VJ121A2` products going forward.
- **Not verified:** whether MODIS and VIIRS anomalies are interchangeable without cross-calibration.

---

## 3. Livestock data

### 3.1 NSO Mongolia (1212.mn), PxWeb API, no login

Base: `https://data.1212.mn/api/v1/en/NSO/Industry, service/Livestock/<table>` (checked live). `GET` returns metadata; `POST` a JSON query to get data. Formats: `csv`, `json`, `json-stat`, `xlsx`, `px` (standard PxWeb; only `csv` was checked live).

| Table | Content | Region levels | Years |
|---|---|---|---|
| `DT_NSO_1001_021V1.px` | NUMBER OF LIVESTOCK by type (total, horse, cattle, camel, sheep, goat) | national, 5 regions, aimag, soum, bag/khoroo (2,222 region codes) | 1970-2025 (56 values) |
| `DT_NSO_1001_029V1.px` | LOSSES OF ADULT ANIMALS by type | same | 1971-2025 (55 values) |
| `DT_NSO_1001_011V1.px` | LOSSES OF ADULT ANIMALS by type | aimag, by quarter | 2011-Q1 to 2026-Q3 |
| `DT_NSO_1001_007V1.px` | survival rate per 100 breeding females | aimag | not checked |
| `DT_NSO_1002_007V1.px` / `_008V1` | hay harvest and fodder laid in; handmade fodder | aimag | not checked |

**Region codes** (checked live):
- 1 digit: national and regions.
- 3 digits: aimag. There are 22 such codes, for 21 aimags plus Ulaanbaatar.
- 5 digits: soum or district. There are 341 such codes.
- 7 digits: bag or khoroo.
- Example: `183` = Bayan-Ulgii, `18301` = Ulgii soum.

**Year codes:** index strings, `"0"` = 2025, `"1"` = 2024, and so on (checked live).

**Test query** (checked live). National total losses for 2010 / 2016 / 2023 / 2024 came back as 10319.900 / 1452.148 / 4921.492 / 9364.083:
- These match the 2009/10, 2015/16, 2022/23 and 2023/24 dzuds.
- They are consistent with **thousand head**, but the unit is **inferred**: not read from table metadata.
- Some soum-year cells return `..` (missing), for example Ulgii 2010.

**Validation target.** Mortality % for year Y = losses(Y) / stock(Y−1). The December census is the NSO convention (Rao 2015; Sci Rep 2018). Convert to sheep units with 5/7/6/1/0.9 (Sci Rep 2018).

**Gap.** The hay/fodder tables are aimag-level only, so soum-level preparedness has no NSO source here.

### 3.2 FAO Gridded Livestock of the World

GLW v4, reference year 2015:
- **Format:** one Harvard Dataverse dataset per species, 5 arc-minutes (about 10 km), licence **CC0 1.0**.
- **Example:** sheep 2015, <https://doi.org/10.7910/DVN/VZOYHM>. Its files are `5_Sh_2015_Da.tif` (dasymetric), `6_Sh_2015_Aw.tif` (areal-weighted) and `7_Sh_2015_Ps_10k.tif`.
- **Other species DOIs:** goats `10.7910/DVN/YYG6ET`, horses `10.7910/DVN/JJGCTX`, cattle `10.7910/DVN/LHBICE`. These come from the Dataverse search API; licence checked for sheep only.

Other versions:
- FAO says GLW is in its fourth version and mentions a 2024 release aligned with FAOSTAT 2020 (<https://www.fao.org/livestock-systems/global-distributions/en/>). The 2020 download location is **not verified**.
- GLW3 (2010) cattle is at <https://doi.org/10.7910/DVN/GIVQ75>.
- GLW does not include camels. Not verified for v4; the v4 species list is buffaloes, cattle, chickens, ducks, goats, horses, pigs and sheep.

Use GLW only to spread soum counts within a soum. The NSO soum census is the primary and current source.

---

## 4. Admin boundaries

| Source | ADM1 | ADM2 | Vintage | Licence | Access |
|---|---|---|---|---|---|
| geoBoundaries gbOpen MNG | 22 units, from "OpenStreetMap, Wambacher" | 339 units (330 soums + 9 UB districts), from "National Statistical Office of Mongolia, OCHA ROAP" | ADM1 2017, ADM2 2021 | ADM1 **ODbL 1.0**; ADM2 **CC BY 3.0 IGO** | `https://www.geoboundaries.org/api/current/gbOpen/MNG/ADM2/` → GeoJSON on GitHub |
| OpenStreetMap | `admin_level=4` = 21 aimags + Ulaanbaatar | `admin_level=6` = soums + UB districts; `admin_level=8` = bags / khoroos | live (Overpass base 2026-11-07) | ODbL | Overpass API, or Geofabrik `asia/mongolia-latest.osm.pbf` |
| FAO GAUL 2025 (GEE) | GAUL1 | GAUL2 | 2025 | **CC BY 4.0** | `FAO/GAUL/2025/level2` (and `_FeatureView`) |
| FAO GAUL 2015 (GEE) | | | 2014 | non-commercial only; **deprecated** | `FAO/GAUL/2015/level2` |

Sources and checks:
- geoBoundaries: API checked live. There is no ADM3 in gbOpen. A gbHumanitarian ADM2 also exists: 339 units, NSO via HDX, 2020.
- OSM levels: <https://wiki.openstreetmap.org/wiki/Tag:boundary%3Dadministrative> (Mongolia row: "21 aimags + the capital Ulaanbaatar (22 in total)", "330 soums + the 9 districts of Ulaanbaatar (339 in total)", "about 1,640 bags").
- Overpass count, checked live: 22 relations at level 4 and 340 at level 6 inside the MN area. The extra 1 is not investigated and may be a border-straddling relation.
- GAUL 2025: <https://developers.google.com/earth-engine/datasets/catalog/FAO_GAUL_2025_level2>
- GAUL 2015: <https://developers.google.com/earth-engine/datasets/catalog/FAO_GAUL_2015_level2>

**Recommendation.** Use geoBoundaries ADM2 (NSO-derived):
- NSO soum names and codes should match it best. Name/code matching to the 5-digit PxWeb codes is **not verified**.
- CC BY 3.0 IGO allows a public website with attribution.
- Use OSM for the base map, roads and settlements (ODbL attribution required).

---

## 5. GEE access today (short)

1. **Cloud project.** Create one, enable Earth Engine, and register it as noncommercial at <https://console.cloud.google.com/earth-engine>. No billing is needed for noncommercial use. Projects registered before 15 Apr 2025 had to verify eligibility by 26 Sep 2025 or be paused, and reverification recurs. Source: <https://developers.google.com/earth-engine/guides/access>
2. **Quota.** Noncommercial quotas began 27 Apr 2026. Source: <https://developers.google.com/earth-engine/guides/noncommercial_tiers>
   - Community: 150 EECU-hours/month, the default.
   - Contributor: 1,000 EECU-hours/month, needs a billing account.
   - Partner: 100,000 EECU-hours/month, by application.
   - Going over the limit means a slower "restricted mode", not a cut-off.
3. **Python.** `ee.Authenticate()` then `ee.Initialize(project=...)`. gcloud is not required: the `localhost` browser flow is used when gcloud is absent. A server must use a service account. Source: <https://developers.google.com/earth-engine/guides/auth>
4. **Publishing.** An Earth Engine App needs no login to view when public. It has its own quota and needs a Cloud project, and the page says a billing account too. Source: <https://developers.google.com/earth-engine/guides/apps>
5. **Tiles in your own site.** Serving map tiles into a site of your own (`getMapId` / tile URLs): **not verified** from docs in this pass.

**Practical note.** The risk computation is about 330 soums × a few dozen rasters a year. It fits the Community tier comfortably (not measured). The simplest site is to precompute soum scores (GEE export or the no-GEE path) and serve a static GeoJSON over an OSM base map.

---

## Not verified (collected)

- Current NAMEM map weights and per-layer standardisation; the 2017 slides are the newest found. Also the public URL of the current map.
- Tachiiri 2008 details: SWE and NDVI sensor, spatial unit.
- Nandintsetseg 2018 (Nat. Hazards) overgrazing-rate formula.
- NSO table unit (thousand head inferred).
- Name/code join between NSO soums and geoBoundaries ADM2.
- Validation of any snow depth / SWE product over Mongolia.
- GEE IDs for MOD13Q1 and the VIIRS NOAA-20 products. Absence of MOD10CM from GEE.
- MERRA-2 LND variable names.
- GLW4 2020 release location. Whether camels are in GLW4.
- CHIRPS download server.
- Earth Engine tile serving for external maps.
- An ice-crust detection product. None was found. Proxy: days with Tmax > 0 °C followed by < 0 °C while snow is on the ground, from ERA5-Land daily min/max plus snow depth. This proxy is unvalidated.
