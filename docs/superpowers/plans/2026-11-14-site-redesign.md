# Site Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the ZudRisk site readable at first sight. The left panel gets three tabs and a status card with a jump to 2009/10. The map uses a light grey basemap with an automatic OSM fallback, and its floating items are frosted. Nothing that works today may break.

**Architecture:** The markup is restructured in `site/index.html`, with its CSS moved to `site/style.css` behind tokens. The pure decision functions go into a new classic script, `site/ui.js`, so Node can test them. `app.js` changes only where it wires those functions in, and every element `id` it writes into is kept.

**Tech Stack:** static HTML/CSS/JS, Leaflet 1.9.4 (unchanged), `node --test` for the new unit tests, and the Claude Browser pane for the acceptance checks.

**Spec:** `docs/superpowers/specs/2026-11-14-site-redesign-design.md`

## Global Constraints

- There is no build step and no new JS library. Leaflet stays 1.9.4 from unpkg with its SRI hash.
- `app.js` and `ui.js` are classic scripts. `ui.js` loads before `app.js`. It exposes `window.ZRui` in the browser and `module.exports` in Node.
- These element `id`s must exist exactly once, as now:
  - header and panel: `level`, `view`, `winter`, `search`, `soums`, `lang`, `banner`;
  - legend: `scale_row`, `scale_l`, `scale`, `legend`, `layer_note`;
  - tables and charts: `zones`, `zone_note`, `aimags`, `validation_h`, `validation`, `unit_note`, `national_chart`, `pooled`, `stages`, `model_table`, `model_note`, `model_chart`, `weights`;
  - the map: `map`.
- Cache busting: `style.css?v=0.7.0`, `ui.js?v=0.7.0`, `app.js?v=0.7.0`.
- Tabs, by the `h2` key (`data-t`, or the `id` for `validation_h`):
  - **map:** `legend`, `zone_table`, `aimags`;
  - **res:** `validation_h`, `national`, `pooled`, `stages`;
  - **how:** `model`, `model_by_winter`, `weights`, `limits`, `sources`.
- The status card's strings are copied verbatim from the spec table. EN outlook titles use `T.months[stage]`, which gives "2026/27 outlook · Oct". This settles the spec's "October" example in favour of its own "same pattern with `T.months[stage]`" rule.
- The Method tab's introduction text is copied verbatim from the spec.
- Esri base URL: `https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`. The reference labels use `World_Light_Gray_Reference`. `maxZoom` is 16. The attribution is `Tiles &copy; Esri — Esri, HERE, Garmin, (c) OpenStreetMap contributors, and the GIS user community`.
- Map extents:
  - fit bounds `[[41.5, 87.7], [52.2, 119.9]]`;
  - max bounds `[[28, 68], [60, 140]]`;
  - `minZoom` 4.
- Tokens on `:root`, with these values:
  - `--ink #1d2433`, `--muted #5b6475`, `--line #d9dde5`, `--bg #f6f7f9`;
  - `--accent #2f6fd6`, `--glass rgba(255,255,255,.78)`;
  - `--grid #eef0f3`, `--bar #8a93a6`, `--axis #9aa1ae`.
- Data palettes stay as they are, except `ZONE_COLORS.desert`, which leaves `#d95f0e`.
- Popup content: `max-height: 280px; overflow-y: auto`.

## Review Focus

1. **Switching MN ⇄ EN after a winter change.** The card title, line and button, the tab names, the caption and the intro must all follow the language. They are written in `render()`, not once at start-up.
2. **A slow Esri, not a dead one.** The fallback triggers only when the first view's base tiles all errored and none loaded. A slow load must never switch to OSM.
3. **Search or table links used while the Results or Method tab is open.** Zooming and opening the popup must still work, and the tab itself does not have to change.
4. **The decree view.** Its caveat `<p class="banner">` inside the legend must still show. Hiding the old top banner must not hide every `.banner`.
5. **Phone width (375 px).** The tabs stay reachable at the top of the panel, touch targets are at least 44 px, and the popup fits within the 55vh map.

Each line is checked in Task 6's browser pass. Lines 1 and 2 also have unit tests in Tasks 3 and 4.

---

### Task 1: CSS out of the page, behind tokens

**Files:**
- Create: `site/style.css` (everything now in `index.html`'s `<style>`, plus the tokens)
- Modify: `site/index.html:8-70` (drop `<style>`, link `style.css?v=0.7.0`, `app.js?v=0.7.0`)
- Test: `tests/site/structure.test.js`

**Interfaces:**
- Produces: the CSS custom properties listed in Global Constraints, defined on `:root` in `site/style.css`.

- [ ] **Step 1: Write the failing test** `tests/site/structure.test.js`. It reads `site/index.html` and `site/style.css` as text.

```js
const test = require("node:test"), assert = require("node:assert/strict"), fs = require("node:fs");
const html = fs.readFileSync("site/index.html", "utf8");
test("styles live in style.css behind tokens", () => {
  assert.ok(!/<style[\s>]/.test(html), "no inline <style>");
  assert.match(html, /href="style\.css\?v=0\.7\.0"/);
  assert.match(html, /src="app\.js\?v=0\.7\.0"/);
  const css = fs.readFileSync("site/style.css", "utf8");
  for (const v of ["--ink", "--muted", "--line", "--bg", "--accent", "--glass", "--grid", "--bar", "--axis"])
    assert.match(css, new RegExp(`${v}:`), v);
});
test("every id app.js writes into exists exactly once", () => {
  for (const id of ["level","view","winter","search","soums","lang","banner","scale_row","scale_l","scale","legend","layer_note","zones","zone_note","aimags","validation_h","validation","unit_note","national_chart","pooled","stages","model_table","model_note","model_chart","weights","map"])
    assert.equal((html.match(new RegExp(`id="${id}"`, "g")) || []).length, 1, id);
});
```

- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL on "no inline <style>".
- [ ] **Step 3: Move the CSS.**
  - Move the `<style>` body unchanged into `site/style.css`.
  - Add the token block.
  - Replace the hard-coded hexes inside the CSS with `var(--…)`. Use `--accent` for the old `#3b6fd8` focus ring.
  - Link the file from `index.html` and bump `app.js` to `?v=0.7.0`.
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. Then open `http://localhost:8766/` with the node static server (scratchpad `serve.mjs`, port 8766, root `site`). The page must look as before, with the pressed buttons now blue.
- [ ] **Step 5: Commit** `git add site tests/site && git commit -m "Site: CSS in style.css behind colour tokens"`.

### Task 2: Three tabs in the panel

**Files:**
- Create: `site/ui.js`
- Modify: `site/index.html` (`<aside>`: a tab bar and three `<section class="pane" data-tab=…>` holding the existing blocks in their current order; a Method intro `<p class="note" data-t="intro">` first in `how`; `<script src="ui.js?v=0.7.0">` before `app.js`)
- Modify: `site/app.js` (`T.mn` and `T.en`: `tab_map`, `tab_res`, `tab_how`, `intro`; call `ZRui.initTabs` once at start-up)
- Modify: `site/style.css` (tab bar sticky at the top of `aside`, active tab `box-shadow: inset 0 -2px var(--accent)`, `.pane[hidden]`, buttons ≥ 44 px in the existing coarse-pointer media query)
- Test: `tests/site/structure.test.js`, `tests/site/ui.test.js`

**Interfaces:**
- Produces:
  - `ZRui.TAB_OF: Record<string, "map"|"res"|"how">`, keyed as in Global Constraints;
  - `ZRui.initTabs(root: HTMLElement, store?: Storage): void`. It wires `[data-tab-btn]` buttons to `section.pane[data-tab]`, opens `map` (or the stored tab), and sets `aria-selected`/`hidden`. Storage access is wrapped in try/catch.

- [ ] **Step 1: Write the failing tests.**
  - In `structure.test.js`, add "each section sits in its tab". For every `<h2>`, find the enclosing `section.pane` and assert its `data-tab` equals `ZRui.TAB_OF[key]`, where `key` is `data-t` or `id`.
  - Also assert `html.match(/<h2/g).length === 12`, so all 12 sections are still present.
  - In `ui.test.js`, `require("../../site/ui.js")` and assert that `TAB_OF.validation_h === "res"`, `TAB_OF.sources === "how"` and `TAB_OF.legend === "map"`.
- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL with "Cannot find module ../../site/ui.js".
- [ ] **Step 3: Implement.**
  - Write `site/ui.js` with the UMD-style footer (`if (typeof module !== "undefined") module.exports = ui; else window.ZRui = ui;`).
  - Restructure the `<aside>` markup.
  - Add the four `T` keys. Tab names: MN "Газрын зураг" / "Үр дүн" / "Арга зүй"; EN "Map" / "Results" / "Method". The intro text is verbatim from the spec.
  - Call `ZRui.initTabs(document.querySelector("aside"), localStorage)`.
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. In the browser, each tab shows its sections, MN ⇄ EN renames the tabs, and the Results tables fill after a winter change.
- [ ] **Step 5: Commit** `git commit -am "Site: three tabs in the panel"`, adding `site/ui.js` too.

### Task 3: Status card and the 2009/10 jump

**Files:**
- Modify: `site/ui.js` (`statusCard`)
- Modify: `site/index.html` (a `<div class="card" id="status">` first in the `map` pane, holding `#banner` as its line, plus `<b id="status_title">` and `<button id="status_go">`)
- Modify: `site/app.js` (`T` keys; `render()` fills the card in place of `$("banner").hidden = …`; the button handler)
- Modify: `site/style.css` (`.card`, the button in `--accent`)
- Test: `tests/site/ui.test.js`

**Interfaces:**
- Consumes: `T[lang].months`, `T[lang].banner`, `T[lang].no_losses_yet`, and app.js's `shown`, `outlook`, `pending`.
- Produces: `ZRui.statusCard(t, s) -> { title: string, line: string|null, button: string, target: string }`, with `s = { shown: string, outlookWinter: string|null, stage: string|null, pending: boolean }`. `target` is the winter-select value the button switches to: `"2009-10"`, or `"outlook"` when `shown === "2009-10"`. Any `.banner` other than `#banner` stays untouched.

- [ ] **Step 1: Write the failing test** in `ui.test.js`, with a stub `t` that carries the MN and EN strings from the spec table:

```js
const T = { months: { oct: "10-р сар", nov: "11-р сар" }, banner: "B", no_losses_yet: "N",
  card_outlook: (w, m) => `${w} өвлийн төлөв · ${m}`, card_oct_line: "Өвлийн цаг агаар хараахан ороогүй; 11-р сараас сар бүр шинэчлэгдэнэ.",
  card_winter: (w) => `${w} өвөл`, card_observed: (w) => `${w} өвөл · ажигласан`,
  card_go: "2009/10-ын зудыг үзэх →", card_back: "← Одоогийн төлөв рүү буцах" };
test("status card says what is shown", () => {
  assert.deepEqual(statusCard(T, { shown: "outlook", outlookWinter: "2026-27", stage: "oct", pending: false }),
    { title: "2026/27 өвлийн төлөв · 10-р сар", line: T.card_oct_line, button: T.card_go, target: "2009-10" });
  assert.equal(statusCard(T, { shown: "outlook", outlookWinter: "2026-27", stage: "nov", pending: false }).line, "B");
  assert.deepEqual(statusCard(T, { shown: "2025-26", outlookWinter: "2026-27", stage: "oct", pending: true }),
    { title: "2025/26 өвөл", line: "N", button: T.card_go, target: "2009-10" });
  assert.deepEqual(statusCard(T, { shown: "2009-10", outlookWinter: "2026-27", stage: "oct", pending: false }),
    { title: "2009/10 өвөл · ажигласан", line: null, button: T.card_back, target: "outlook" });
});
```

- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL with "statusCard is not a function".
- [ ] **Step 3: Implement.**
  - Add `statusCard` to `ui.js`.
  - Add the eight `card_*` keys to `T.mn` and `T.en`, verbatim from the spec table.
  - In `render()`, call `ZRui.statusCard(t, { shown, outlookWinter: outlook?.winter ?? null, stage: outlook?.stage ?? null, pending: pending.has(shown) })` and write the result into `#status_title`, `#banner` (hidden when `line` is null) and `#status_go`.
  - The button sets `sel.value = target`, dispatches `change`, and calls `render()` once `load` resolves.
  - Without an outlook, `target` from the 2009/10 view falls back to the last winter. Make `statusCard` return `target: s.outlookWinter ? "outlook" : null`, and have the button hide itself when `target` is null.
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. In the browser:
  - the card shows the October outlook;
  - the button goes to 2009/10 and reads "back", then returns;
  - EN switches all three strings;
  - the decree view's caveat still shows (Review Focus 4).
- [ ] **Step 5: Commit** `git commit -am "Site: status card with the 2009/10 jump"`.

### Task 4: Light grey basemap with OSM fallback, fitted to Mongolia

**Files:**
- Modify: `site/ui.js` (`shouldFallback`)
- Modify: `site/app.js:201-211` (the base layers and the control), `site/app.js:665` (`fitBounds`)
- Modify: `site/app.js` `T.*.sources_text`: one added sentence. MN: "Саарал суурь зураг: Esri (World Light Gray Canvas)." EN: "Grey base map: Esri (World Light Gray Canvas)."
- Test: `tests/site/ui.test.js`

**Interfaces:**
- Produces: `ZRui.shouldFallback(loaded: number, errored: number) -> boolean`. It returns true only when `loaded === 0 && errored > 0`.
- Produces in app.js: `const grey = L.layerGroup([base, labels])`, which is the default. The control's base layers are `{ "Саарал / Light grey": grey, OpenStreetMap: osm, OpenTopoMap: topo }`. The overlay stays as it is.

- [ ] **Step 1: Write the failing test**: `shouldFallback(0, 6) === true`, `shouldFallback(1, 5) === false`, `shouldFallback(0, 0) === false`. The last case is Review Focus 2: a slow load that has not settled must not switch.
- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL with "shouldFallback is not a function".
- [ ] **Step 3: Implement.**
  - Labels go in a pane `labels` with `zIndex` 650 and `pointerEvents: "none"`.
  - Count `tileload` and `tileerror` on the base layer until its first `load` event. Then, if `ZRui.shouldFallback(...)`, swap `grey` for `osm`, which updates the control's radio.
  - Map setup: `L.map("map", { minZoom: 4, maxBounds: [[28, 68], [60, 140]] })`, fitted to `[[41.5, 87.7], [52.2, 119.9]]`. Line 665 uses the same fit instead of `layer.getBounds()`.
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. In the browser, check acceptance 1 (fit, grey basemap, labels above the soums). For acceptance 4, block `server.arcgisonline.com` in DevTools and reload: the page must load on OSM with no visible error. The OSM and OpenTopoMap switches work, and the zone overlay toggles.
- [ ] **Step 5: Commit** `git commit -am "Site: light grey basemap with OSM fallback, fitted to Mongolia"`.

### Task 5: Chrome colours from tokens, desert brown, header

**Files:**
- Modify: `site/app.js`:
  - the chart and SVG chrome hexes read the tokens through `const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim()`;
  - `ZONE_COLORS.desert` changes;
  - a `level` label key.
- Modify: `site/index.html` (`<span class="lbl" data-t="level">` before `#level`; "ZudRisk" beside the title)
- Modify: `site/style.css` (`header h1` 20 px)
- Test: `tests/site/structure.test.js`

**Interfaces:**
- Consumes: the tokens from Task 1.

- [ ] **Step 1: Write the failing test** "no chrome hex in app.js, and a distinct desert". For each of `#1d2433 #5b6475 #d9dde5 #8a93a6 #9aa1ae #3b6fd8`, assert it no longer occurs in `site/app.js`. Then parse `ZONE_COLORS.desert` and assert its RGB distance (√Σ(Δ)²) is greater than 60 from every colour in `COLORS` and `CHANCE`.
- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL, listing `#1d2433`.
- [ ] **Step 3: Implement.**
  - Replace the six hexes with `css("--ink")`, `css("--muted")`, `css("--line")`, `css("--bar")`, `css("--axis")` and `css("--accent")`.
  - Pick a brown for the desert that passes the test, for example `#8c510a`.
  - Add `T.*.level`: "Түвшин" / "Level".
  - Add the header markup.
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. In the browser, the charts in Results and Method and the popup chart draw in the same tones as before, and the zone view's desert is brown.
- [ ] **Step 5: Commit** `git commit -am "Site: chart colours from tokens, distinct desert colour, header label"`.

### Task 6: Frosted map items, caption, popup cap, full acceptance

**Files:**
- Modify: `site/style.css` (glass on `.leaflet-bar`, `.leaflet-control-layers`, `.leaflet-control-attribution`, `.leaflet-popup-content-wrapper`, `.leaflet-popup-tip` and `.caption`; `.leaflet-popup-content { max-height: 280px; overflow-y: auto }`)
- Modify: `site/index.html` (a `<div class="caption" id="caption">` inside `#map`'s container, holding `<b data-t="caption_title">` and `<span data-t="caption_src">`)
- Modify: `site/app.js` (`T.*.caption_title` "Зудын эрсдэл, сум бүрээр" / "Dzud risk by soum"; `caption_src` "ERA5-Land · MODIS NDVI · ҮСХ" / "ERA5-Land · MODIS NDVI · NSO")

- [ ] **Step 1: Add the structure test** "caption present and translated": `id="caption"` exists, and both `T` languages contain the `caption_title` key. The test reads the `T` source text with a regex.
- [ ] **Step 2: Run** `node --test tests/site/`. Expected: FAIL on the caption.
- [ ] **Step 3: Implement.** The caption must not catch clicks (`pointer-events: none`).
- [ ] **Step 4: Run** `node --test tests/site/`. Expected: PASS. Then run the spec's whole acceptance list (1–9) and Review Focus 1–5 in the Browser pane, at 1440×860 and at 375×812:
  - every view × level;
  - search while on Results;
  - a Dornogovi popup and a Khövsgöl popup, each fully visible;
  - MN ⇄ EN after changing winter;
  - no console errors.

  Also run the pipeline check loop from the README. Expected: 28/28.
- [ ] **Step 5: Commit** `git commit -am "Site: frosted map items, caption, popup height cap"`. Then update README's "What the site shows" with one line on the tabs and the card, and commit that too.
