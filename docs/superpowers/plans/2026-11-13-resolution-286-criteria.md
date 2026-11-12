# Resolution 286 main dzud criteria: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every shown winter and the current outlook, flag each soum with the most severe dzud type whose Resolution 286 main criteria the data meet. Show it as a separate site view with a fixed caveat, and report how the flags line up with recorded losses.

**Architecture:** A new `pipeline/summer.py` fetches May-Aug precipitation and temperature from ERA5-Land monthly means, following `pipeline/era5.py`. A new `pipeline/decree286.py` holds pure rule functions plus a `main(year, as_of)` that writes per-winter files, and is called from `pipeline.hindcast` and `pipeline.outlook`. The site reads `site/data/decree286_<label>.json` in a new view.

**Tech Stack:** Python 3.12+ (stdlib, numpy, netCDF4, shapely as already used), `uv run python -m pipeline.<module> --check` self-checks with `assert`, vanilla JS + Leaflet site.

**Spec:** `docs/superpowers/specs/2026-11-13-resolution-286-criteria-design.md`

## Global Constraints

- Baseline for every "long-term mean" and σ: winters/summers 2001-2020 (`indicators.BASELINE`), population σ as in `score.zscore`.
- Month step only; months not over by `as_of` are left out (`indicators._months_over`).
- Snow thresholds (cm), "dzud" / "moderate":
  - mountain, taiga, forest_steppe: 25 / 16;
  - steppe: 22 / 11;
  - desert: 12 / 5.
- "Above" means strictly greater than the threshold.
- No snow is depth < 1 cm (`indicators.SNOW_MIN_M` = 0.01 m).
- Not assessed, and said so on the site: snow density, the auxiliary criteria, the dekad step, and hoof, storm and iron dzud.
- Severity order: `black`, `white`, `black_moderate`, `white_moderate`, then `none`. A soum missing an input is `unassessed`, never `none`.
- ZudRisk's risk score, weights and README figures are not changed.
- Site text in Mongolian and English. The caveat reads verbatim: "Туслах шалгуур (өдрийн хамгийн бага температур, салхи), цасны нягтыг үнэлээгүй; сар бүрээр; суурь 2001–2020. Албан ёсны үнэлгээ биш." / "Auxiliary criteria (daily minimum temperature, wind) and snow density not assessed; by month; baseline 2001–2020. Not an official assessment."
- Cite the source as "Засгийн газрын 2015 оны 286-р тогтоол, 5-р хавсралт" / "Government Resolution 286 (2015), annex 5".

**Spec clarification (decided here, state it in `decree286.py`'s docstring):** the procedure's two summer classes leave gaps.

| Summer class | Rule here |
|---|---|
| `drought` | precipitation share ≤ 0.50 **and** (t_anom ≥ 2.0 or t_anom > 2σ) |
| `near` | not `drought`, precipitation share ≤ 0.80, **and** (t_anom ≥ 1.0 or t_anom > σ) |

So a summer drier than 50 % but only 1.0-1.9 °C hot counts as `near`, rather than as no drought.

## Review Focus

1. **Outlook in October.** No winter month is over yet, so every soum is `unassessed`, never `none`.
   - Test: `winter_status({})` is `("unassessed", [])` in Task 2.
2. **A soum with no herd or no ERA5 cell.** It is grey on the map and does not crash the popup.
   - Test: Task 3, a fixture row with `depth_cm=None` gives `unassessed`.
3. **Summer missing for 2000/01's previous summer.** ERA5 has 2000; a gap still must not drop white dzud.
   - Test: Task 2, `month_flags(..., summer="unassessed")` still flags `white`.
4. **Zero baseline σ.** A soum whose 2001-2020 temperatures are constant (never in practice, but possible with bad data) must not divide by zero.
   - Test: Task 3, `anomaly(...)` with equal values returns σ 0.0 and the −3 °C rule still works.
5. **Exactly-on-threshold values** (25.0 cm, −3.0 °C, share 0.50 and 0.80).
   - Test: Task 2 boundary asserts.

---

### Task 1: Summer precipitation and temperature per soum

**Files:**
- Create: `pipeline/summer.py`
- Modify: `README.md` (Run block: one line `uv run python -m pipeline.summer  # ERA5-Land May-Aug precipitation and temperature (CDS)`)
- Test: `pipeline/summer.py` `check()`

**Interfaces:**
- Consumes: `pipeline.http.cached`, `cds_retrieve`; `pipeline.gldas.map_cells`, `soum_means`; `pipeline.era5.yyyymm` (all existing).
- Produces:
  - `OUT = Path("data/derived/soum_summer.csv")` with columns `pcode,yyyymm,tp_mm,t2m_c`;
  - `monthly_total_mm(rate_m: float, yyyymm: str) -> float`;
  - `load_summer(path: Path = OUT) -> dict[str, dict[str, dict[str, float]]]`, i.e. pcode → `{"tp_mm": {yyyymm: v}, "t2m_c": {...}}`.

- [ ] **Step 1: Write the failing check**

```python
def check() -> None:
    assert monthly_total_mm(0.002, "202407") == 62.0          # 2 mm a day, 31 days
    assert monthly_total_mm(0.001, "202406") == 30.0          # 30 days
    assert INPUTS["month"] == ["05", "06", "07", "08"]
    assert INPUTS["variable"] == ["total_precipitation", "2m_temperature"]
    assert INPUTS["year"][0] == "2000" and INPUTS["area"] == era5.INPUTS["area"]
    print("summer check: ok")
```

- [ ] **Step 2: Run** `uv run python -m pipeline.summer --check`. Expected: `NameError` / `ImportError`.

- [ ] **Step 3: Implement `pipeline/summer.py`**
  - `DATASET = "reanalysis-era5-land-monthly-means"`. `INPUTS` is `era5.INPUTS` with `variable` and `month` as above and `year` 2000 to the last full summer.
  - `RAW = Path("data/raw/era5_land_summer_<first>_<last>.nc")`, fetched via `cached`.
  - Convert `t2m` with `era5.to_celsius`.
  - `tp` in the file is a mean daily rate in metres: `monthly_total_mm` multiplies it by `calendar.monthrange` days and 1000, rounded to 0.1 mm.
  - `main()` writes `OUT` like `era5.main`.

- [ ] **Step 4: Run** `uv run python -m pipeline.summer --check`, then `uv run python -m pipeline.summer`.
  Expected: `summer check: ok`, then a line `N months, 339 soums, M rows -> data/derived/soum_summer.csv`, where N = 4 × the number of summers.

- [ ] **Step 5: Commit** `pipeline/summer.py`, `README.md` and `data/derived/soum_summer.csv`, with message "ERA5-Land May-Aug precipitation and temperature per soum, for Resolution 286's summer drought".

### Task 2: The rules

**Files:**
- Create: `pipeline/decree286.py` (rules and `check()` only in this task)

**Interfaces:**
- Produces:
  - `THRESHOLDS: dict[str, tuple[float, float]]`;
  - `zone_thresholds(zone: str) -> tuple[float, float]` (cm, raises `KeyError` naming an unknown zone);
  - `UNASSESSED = "unassessed"`;
  - `summer_drought(precip_share: float | None, t_anom: float | None, t_sd: float | None) -> str | None`, which returns `"drought"`, `"near"`, `None` or `UNASSESSED`;
  - `month_flags(depth_cm: float | None, t_anom: float | None, t_sd: float | None, zone: str, summer: str | None) -> set[str] | None`, where `None` means unassessed;
  - `ORDER = ["black", "white", "black_moderate", "white_moderate"]`;
  - `winter_status(months: dict[str, set[str] | None]) -> tuple[str, list[str]]`, which returns the status (`ORDER` entry, `"none"` or `UNASSESSED`) and the sorted months that gave it.

- [ ] **Step 1: Write the failing check**

```python
def check() -> None:
    assert zone_thresholds("taiga") == (25.0, 16.0) and zone_thresholds("desert") == (12.0, 5.0)
    try: zone_thresholds("tundra"); raise AssertionError
    except KeyError as e: assert "tundra" in str(e)
    assert summer_drought(0.50, 2.0, 5.0) == "drought" and summer_drought(0.50, 1.0, 5.0) == "near"
    assert summer_drought(0.80, 0.5, 0.4) == "near" and summer_drought(0.81, 3.0, 1.0) is None
    assert summer_drought(0.6, 0.5, 1.0) is None and summer_drought(None, 1.0, 1.0) == UNASSESSED
    assert month_flags(25.0, -3.0, 1.0, "mountain", None) == {"white_moderate"}   # 25 is not above 25
    assert month_flags(25.1, -3.0, 1.0, "mountain", None) == {"white", "white_moderate"}
    assert month_flags(25.1, -1.5, 1.0, "mountain", None) == {"white", "white_moderate"}  # below −1σ
    assert month_flags(0.5, -3.0, 1.0, "steppe", "near") == {"black"}
    assert month_flags(5.0, -2.0, 1.0, "desert", "drought") == {"black_moderate"}      # 1 ≤ depth ≤ 5
    assert month_flags(0.5, -3.0, 1.0, "steppe", None) == set()
    assert month_flags(30.0, -4.0, 1.0, "steppe", UNASSESSED) == {"white", "white_moderate"}
    assert month_flags(None, -4.0, 1.0, "steppe", None) is None
    assert winter_status({}) == (UNASSESSED, [])
    assert winter_status({"202512": {"white_moderate"}, "202601": {"black", "white_moderate"}}) == ("black", ["202601"])
    assert winter_status({"202512": set(), "202601": None}) == ("none", [])
    assert winter_status({"202512": None}) == (UNASSESSED, [])
    print("decree286 check: ok")
```

- [ ] **Step 2: Run** `uv run python -m pipeline.decree286 --check`. Expected: `NameError`.

- [ ] **Step 3: Implement the rule functions** with the values in Global Constraints and the summer clarification.
  - White needs `t_anom <= -3.0 or t_anom < -t_sd`.
  - Black needs `t_anom <= -3.0` and depth < 1 cm.
  - Black moderate needs `t_anom <= -2.0` and 1 ≤ depth ≤ the moderate threshold.
  - Both black types need `summer in ("drought", "near")`.
  - Any `None` among depth and t_anom gives `None`.
  - `winter_status`:
    - `none` when at least one month was assessed and none flagged;
    - `UNASSESSED` when no month was assessed;
    - otherwise the first `ORDER` entry met and the months it was met in.
  - The docstring cites the clauses (3.3.1 to 3.3.4, 2.2) and the summer clarification.

- [ ] **Step 4: Run** `uv run python -m pipeline.decree286 --check`. Expected: `decree286 check: ok`.

- [ ] **Step 5: Commit** with message "Resolution 286 main dzud criteria as plain rules, checked at their thresholds".

### Task 3: Per-winter files, validation, and the pipeline hooks

**Files:**
- Modify: `pipeline/decree286.py` (add the inputs, `main`, `validate`)
- Modify: `pipeline/hindcast.py` (call it for every shown winter, then `validate`), `pipeline/outlook.py` (call it for the outlook winter at its `as_of`)

**Interfaces:**
- Consumes:
  - `era5.load_era5()` (sde in m, t2m in °C, by `yyyymm`);
  - `summer.load_summer()`;
  - `zones.soum_zone()`;
  - `indicators.BASELINE`, `indicators.snow_months(year, as_of)`, `indicators.winter_end(year)`;
  - `export.label(year)`, `export.SITE`;
  - `validate.mortality(herds, pcode, year)`;
  - `nso.load_livestock()`;
  - `indicators.read_risk(year)` with `score.risk_class`.
- Produces:
  - `anomaly(series: dict[str, float], month: str, year: int, years=BASELINE) -> tuple[float | None, float | None]`, which returns the value minus the baseline mean of that calendar month (`month` like "12"), and the baseline population σ;
  - `summer_share(series_tp, series_t, year) -> tuple[float | None, float | None, float | None]`, the May-Aug totals against the baseline;
  - `main(year: int, as_of: date | None = None) -> dict[str, dict]`, which writes `data/derived/decree286_<year>.csv` and `site/data/decree286_<label>.json`;
  - `validate(years: list[int]) -> dict`, which writes `site/data/decree286_validation.json`.
- JSON shape per soum: `{"status": str, "months": [yyyymm], "summer": str | null, "by_month": {yyyymm: [types] | null}, "inputs": {yyyymm: {"depth_cm", "t_anom", "t_sd"}}, "zone": str}`.
- Validation shape: `{status: {"n": int, "loss5": float}}` for soum-winters 2011/12 on with losses (adult losses in sheep units ≥ 5 % of the census), plus `"risk_class_4"` for ZudRisk's very-high class, for comparison.

- [ ] **Step 1: Add to `check()`**

```python
    s = {f"{y}12": -20.0 for y in range(2001, 2021)}; s["202512"] = -24.0
    assert anomaly(s, "12", 2025) == (-4.0, 0.0)            # constant baseline: σ 0, −3 °C rule still applies
    assert month_flags(30.0, -4.0, 0.0, "steppe", None) == {"white", "white_moderate"}
    tp = {f"{y}{m}": 25.0 for y in range(2001, 2021) for m in ("05", "06", "07", "08")}
    tp.update({f"2025{m}": 10.0 for m in ("05", "06", "07", "08")})
    t = {k: 15.0 for k in tp}; t.update({f"2025{m}": 17.5 for m in ("05", "06", "07", "08")})
    share, ta, sd = summer_share(tp, t, 2025)
    assert share == 0.4 and ta == 2.5 and summer_drought(share, ta, sd) == "drought"
```

- [ ] **Step 2: Run** `uv run python -m pipeline.decree286 --check`. Expected: `NameError: anomaly`.

- [ ] **Step 3: Implement** `anomaly`, `summer_share`, `main`, `validate` and the two hooks.
  - In `hindcast.main`, run `decree286.main(y)` for every year in `shown()`, after `export.main`, then `decree286.validate(WINTERS)`.
  - In `outlook.main`, run `decree286.main(year, as_of)`.

- [ ] **Step 4: Run** the check, then `uv run python -m pipeline.decree286` (a `__main__` that runs `main` for `hindcast.shown()` and then `validate`).
  - Expected: one line per winter with status counts. 2009/10 must have more `white` soums than 2017/18.
  - Print `decree286_validation.json`.

- [ ] **Step 5: Run every self-check** (the README loop plus `summer decree286`). Expected: all ok.

- [ ] **Step 6: Commit** the code and the generated `data/derived/decree286_*.csv` and `site/data/decree286_*.json`, with message "Resolution 286 status per soum and winter, and its line-up with recorded losses".

### Task 4: The site view

**Files:**
- Modify: `site/app.js` (a view `decree` in `views`, colours, legend, popup, validation table, both languages), `site/index.html` (an `<option value="decree">` in `#view`)

**Interfaces:**
- Consumes: `site/data/decree286_<label>.json` and `site/data/decree286_validation.json` from Task 3, both fetched with the existing `optional()`.
- Produces: no new interface.

- [ ] **Step 1: Implement.**
  - Colours:

    | Status | Colour |
    |---|---|
    | `black` | `#1a1a1a` |
    | `white` | `#2c7fb8` |
    | `black_moderate` | `#7f7f7f` |
    | `white_moderate` | `#a6cee3` |
    | `none` | `#f7f7f7` |
    | `unassessed` | `GREY` |

  - Labels (MN / EN):
    - "Хар зуд" / "Black dzud";
    - "Цагаан зуд (нягтгүйгээр)" / "White dzud (density not assessed)";
    - "Хараар зудархуу" / "Black, moderate";
    - "Цагаанаар зудархуу (нягтгүйгээр)" / "White, moderate (density not assessed)";
    - "Шалгуур биелээгүй" / "No main criterion met";
    - "Үнэлэх өгөгдөлгүй" / "Not assessed".
  - The caveat from Global Constraints sits above the legend, styled like the outlook banner, every time the view is on.
  - The popup lists each month with its types and inputs: depth vs threshold, t_anom, and the summer class.
  - The validation table sits under the legend.
  - The source line cites Resolution 286.

- [ ] **Step 2: Check in a browser** (node static server, as before: `python -m http.server` cuts files over 457 kB on this PC).
  - On 2009/10: the caveat is visible; black and white colours appear; the popup lists months.
  - On the outlook: everything is grey with the October stage, or flagged months once November is in.
  - Switching back to the risk view restores it.
  - No console errors other than missing optional files.

- [ ] **Step 3: Commit** with message "Site: Resolution 286 view with its caveat, popup and line-up with losses".

### Task 5: Docs and publish

**Files:**
- Modify: `README.md` ("What the site shows": one bullet with the caveat), `plan.md` (Done table row: Z2, with the validation figures)

- [ ] **Step 1: Write the two text changes.** Quote the validation shares from `decree286_validation.json`.
- [ ] **Step 2: Run every self-check.** Expected: all ok.
- [ ] **Step 3: Commit.** Push to `main` only after the user says yes, then confirm the Pages deploy serves `data/decree286_validation.json`.
