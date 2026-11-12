# Resolution 286 dzud criteria: design

Date: 2026-11-13. Status: **approved in conversation; spec awaiting review.** Plan task Z2 (plan.md).

## Товч (Mongolian summary)

Засгийн газрын 2015 оны 286-р тогтоолын 5-р хавсралт "Ган, зудын байдалд үнэлгээ хийх журам" нь зудын төрөл ба эрчмийг
тогтоодог. ZudRisk энэ журмын **үндсэн шалгуурыг** сум бүрээр, өвлийн сар бүрээр тооцож, сайтад тусдаа давхарга болгон
харуулна. Туслах шалгуур (өдрийн хамгийн бага температур, салхитай өдөр) болон цасны нягтыг одоо байгаа өгөгдлөөр
тооцох боломжгүй тул "үнэлээгүй" гэж тэмдэглэнэ. Иймээс энэ нь албан ёсны үнэлгээ биш, журмын үндсэн шалгуур биелсэн эсэхийн
тойм юм. ZudRisk-ийн оноог өөрчлөхгүй.

## 1. Intent

Resolution 286 (2015), annex 5, is the official procedure for judging drought and dzud. Herders, soum governors and
NEMA speak its terms: "цагаан зуд", "хар зуд", "зудтай", "зудархуу". ZudRisk's score is a z-score blend that does not
map onto those terms. This adds a second, separate view that says, soum by soum and month by month, which of the
procedure's **main** criteria the data meet, so a reader can set ZudRisk's score beside the official definitions.

Success: for every winter on the site and the current outlook, each soum shows the most severe dzud type whose main
criteria were met, with the months and the criteria behind it, and the site says plainly what was not assessed.
The flags are compared with recorded losses, and the comparison is reported.

Not in scope: the auxiliary criteria (daily minimum temperature, windy days), snow density, the dekad step, hoof dzud
("туурайн"), storm dzud ("шуурган") and iron dzud ("төмөр"). The procedure gives no thresholds for hoof and storm dzud,
and iron dzud needs density or ice data (task Z6). These may come later; nothing here should block them.

## 2. The procedure, as used here

Main criteria only (annex 5, 3.3 and 3.5). The procedure judges by dekad or month; ZudRisk judges by month.

| Type | Main criteria, per winter month | Clause |
|---|---|---|
| White dzud (цагаан зуд) | mean snow depth above the zone's "dzud" threshold **and** monthly mean temperature at least 3.0 °C below the long-term mean, or more than one standard deviation below it | 3.3.1 |
| White, moderate (цагаанаар зудархуу) | mean snow depth above the zone's "moderate" threshold | 3.3.2 |
| Black dzud (хар зуд) | the previous summer was drought or near-drought **and** no snow **and** temperature at least 3.0 °C below the mean | 3.3.3 |
| Black, moderate (хараар зудархуу) | the previous summer was drought or near-drought **and** little snow **and** temperature at least 2.0 °C below the mean | 3.3.4 |

The procedure also requires snow density for white dzud (at least 0.25 g/cm³) and for its moderate form (0.20-0.24 g/cm³).
ERA5-Land's monthly soum means never reach 0.20 g/cm³: the highest in 2009/10 was 0.19 g/cm³. So density is
**not assessed**, and a white-dzud flag means "the main criteria other than density are met".

Snow thresholds by zone (3.3.1, 3.3.2), with ZudRisk's five zones (pipeline.zones):

| ZudRisk zone | Procedure's zone | "Dzud" depth | "Moderate" depth |
|---|---|---|---|
| mountain, forest_steppe | high mountain and forest steppe | > 25 cm | > 16 cm |
| taiga | not named in the procedure; taken as high mountain and forest steppe | > 25 cm | > 16 cm |
| steppe | steppe | > 22 cm | > 11 cm |
| desert (includes desert steppe, ZudRisk's choice) | gobi and desert | > 12 cm | > 5 cm |

Definitions the procedure leaves open, fixed here:
- **No snow** (black dzud): monthly mean depth below 1 cm, the same floor ZudRisk uses for snow on the ground
  (indicators.SNOW_MIN_M).
- **Little snow** (black, moderate): from 1 cm up to the zone's "moderate" threshold.
- **Previous summer drought** (2.2, 2.3.1): May to August of the summer before the winter, as a season.
  - **Drought (гантай)**: precipitation at most 50 % of its mean **and** temperature at least 2.0 °C above its mean, or
    more than two standard deviations above it.
  - **Near-drought (гандуу)**: precipitation 51-80 % of its mean **and** temperature 1.0-1.9 °C above its mean, or more
    than one standard deviation above it.
  - Either one counts as "drought or near-drought" for black dzud.
- **Long-term mean**: 2001-2020, ZudRisk's baseline (indicators.BASELINE). This is a choice, made in conversation on
  2026-11-13: the official normal may be 1991-2020, and the site says which period is used.
- **Duration** (1.3: one month or longer): one winter month meeting the criteria is enough, since the step is a month.

A winter's status for a soum is the most severe type met in any month, in this order: black dzud, white dzud, black
moderate, white moderate, none. Severity order follows the procedure's split of "зудтай" over "зудархуу"; between white
and black at the same level, black is listed first only to fix an order, not as a judgement.

## 3. Data

| Input | Source | Status |
|---|---|---|
| Snow depth, 2 m temperature, Nov-Mar, 2000/01 on | ERA5-Land monthly means, already in pipeline.era5 | have |
| Precipitation and 2 m temperature, May-Aug, 2000 on | ERA5-Land monthly means (`total_precipitation`, `2m_temperature`) | **new fetch**, one CDS request for 2000-2025 plus a request per new summer |
| Soum zone | pipeline.zones (Mongolia's natural zoning map) | have |
| Losses | NSO, pipeline.nso | have |

Monthly-means requests have been fast so far, unlike the daily statistics behind Z6.
ERA5-Land `total_precipitation` in monthly means is a mean daily rate in metres. A month's total is the rate × the
days in the month.

## 4. Components

- `pipeline/summer.py`: fetch and read May-Aug precipitation and temperature per soum. It follows pipeline.era5:
  a cached CDS download, soum means over land cells, and a CSV under data/derived.
- `pipeline/decree286.py`, with plain functions and a `--check`:
  - `zone_thresholds(zone)` returns the two snow thresholds;
  - `summer_drought(precip_share, t_anom, t_sd)` returns "drought", "near" or None;
  - `month_flags(depth_m, t_anom, t_sd, zone, summer)` returns the types met that month;
  - `winter_status(months)` returns the most severe type and the months behind it;
  - `main(year, as_of)` writes `data/derived/decree286_<year>.csv` and `site/data/decree286_<label>.json`, with each
    soum's status, flags by month, and the inputs used.
- `pipeline.hindcast` and `pipeline.outlook` call it, so every shown winter and the current outlook (through its
  stage) have a file.
- **Site** (`site/app.js`, `site/index.html`): a new view, "286-р тогтоол (үндсэн шалгуур)" / "Resolution 286 (main
  criteria)".
  - It shows five colours for the statuses, and grey where data are missing.
  - The popup lists the months and the criteria met, with the inputs (depth, threshold, temperature anomaly, summer
    precipitation share).
  - A fixed note above the legend reads: "Туслах шалгуур (өдрийн хамгийн бага температур, салхи), цасны нягтыг
    үнэлээгүй; сар бүрээр; суурь 2001–2020. Албан ёсны үнэлгээ биш." The English site carries the same note.
- **Validation**: in `decree286.main` over the validated winters.
  - For each status, report the number of soum-winters and the share with adult losses of 5 % or more (2011/12 on,
    soum level).
  - Report the same for ZudRisk's top risk class, for comparison.
  - The figures are written to `site/data/decree286_validation.json` and shown under the view.

## 5. Error handling

- A soum missing any input for a month gets no flag for that month and is shown grey for it, not "none".
- A summer with no precipitation data leaves the black-dzud criteria unassessed for that winter, and the popup says so.
- A zone missing from the threshold table stops the run (KeyError naming it), as pipeline.zones does for subzones.
- The outlook's months not yet over are left out, as indicators does with `as_of`.

## 6. Testing

`--check` covers:
- each threshold row;
- the boundary cases: exactly 25 cm, exactly −3.0 °C, 50 % and 51 % precipitation;
- a winter whose status comes from one month;
- the severity order;
- the summer-drought rule with the σ alternatives;
- the precipitation conversion from rate to monthly total;
- a missing input giving "unassessed", not "none".

The site is checked in a browser on a dzud winter (2009/10), a calm one and the current outlook.

## 7. Open points

- The official long-term mean period (1991-2020 or other) is not confirmed. 2001-2020 is used and stated.
- Hoof, storm and iron dzud, the auxiliary criteria and density: later, if daily data come (Z6 fetch).
