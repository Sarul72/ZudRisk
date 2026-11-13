# Site redesign: clearer layout and a professional look

Date: 2026-11-14. Status: approved in conversation (layout A, frosted floating items, Esri light grey basemap, approach 2).

## Intent

ZudRisk will be shown to two groups:

- the judges of NASA Space Apps Challenge 2026, "earth trend detect";
- remote-sensing lecturers at the National University of Mongolia.

The owner will also use it in talks. Three people who tried it said it is "very confusing, disorganized, unclear what is where".

The data and the method are not the problem. The page puts everything into one 5,867 px left column of 12 sections, in a fixed order. The goal is that a first-time visitor understands what the site shows within 10–15 seconds. The site should also look professional enough to present. Nothing that works today may break.

## What a first-time visitor should see

The page opens on the 2026/27 outlook, as now. A card at the top of the panel says which winter and stage is shown. The same card has a button that jumps to winter 2009/10, a well-known dzud winter, so the method can be seen working. While 2009/10 is shown, the button returns to the outlook. This is choice C in the conversation.

## Goals

1. **Three tabs in the left panel.** Every existing section moves into one of them. No section is rewritten.

   | Tab (MN / EN) | Sections, by the `h2` key in `site/index.html` |
   |---|---|
   | Газрын зураг / Map | the status card (new), `legend` (scale row, legend, layer note), `zone_table`, `aimags` |
   | Үр дүн / Results | `validation_h`, `national`, `pooled`, `stages` |
   | Арга зүй / Method | a short introduction (new, text below), `model`, `model_by_winter`, `weights`, `limits`, `sources` |

2. **Status card.** It replaces the yellow banner and holds the 2009/10 button described above. The decree view's own caveat banner inside the legend stays as it is.

   What the card says (my call, see "Calls made" below):

   | State | Title (MN / EN) | Line (MN / EN) |
   |---|---|---|
   | Outlook, `oct` stage | "2026/27 өвлийн төлөв · 10-р сар" / "2026/27 outlook · October" | "Өвлийн цаг агаар хараахан ороогүй; 11-р сараас сар бүр шинэчлэгдэнэ." / "No winter weather is in yet; it is updated every month from November." |
   | Outlook, later stage | the same pattern with `T.months[stage]` | the existing `T.banner` |
   | Pending winter (2025/26) | "{winter} өвөл" / "Winter {winter}" | the existing `no_losses_yet` |
   | Any other winter | "{winter} өвөл · ажигласан" / "Winter {winter} · observed" | none |

   Each title builds the winter label from the selected winter. "2026/27" in the table is only an example.

   The button reads "2009/10-ын зудыг үзэх →" / "See the 2009/10 dzud →". While 2009/10 is shown, it reads "← Одоогийн төлөв рүү буцах" / "← Back to the current outlook".

3. **Map first.**
   - The map opens fitted to Mongolia (about 41.5–52.2° N, 87.7–119.9° E).
   - Panning is limited to a box around Mongolia (20–66° N, 60–150° E; widened from 28–60° N, 68–140° E in build, because at 375 px a northern popup's auto-pan reaches 66° N). `minZoom` stays 4.
   - The box must be larger than the map view at the fitted zoom, on both desktop and phone. Otherwise Leaflet undoes the popup's auto-pan, and a northern soum's popup is cut off.
   - The default basemap is Esri World Light Gray Canvas:
     - base: `https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`;
     - its reference labels: `.../World_Light_Gray_Reference/...`, in a pane above the soums and below popups, with `pointer-events: none`;
     - attribution: "Tiles &copy; Esri — Esri, HERE, Garmin, (c) OpenStreetMap contributors, and the GIS user community". This is the services' own `copyrightText`;
     - `maxZoom` 16.
   - The layer control stays. It holds the natural-zone overlay.
     - Its base layers become: light grey (default, base and labels together), OpenStreetMap, OpenTopoMap.
     - OSM stays one click away because it shows place names in Mongolian script.
   - The labels are English. This is accepted. Making our own labels was tried and rejected.
   - **Fallback (owner's choice A).** The Esri service is licensed under the Esri Master License Agreement. Keyless public use could not be confirmed, and the service is in "mature support". So the site switches to OpenStreetMap by itself when the Esri base tiles fail. The trigger: the first view's base tiles all error, with none loaded. After the switch, the layer control shows OSM as selected. One failed tile is not enough to switch.

4. **Frosted floating items.** The side panel stays solid white. Everything floating on the map gets a translucent white background (about 78 % opacity) with `backdrop-filter: blur(10px)`, a 10–12 px radius and a soft shadow:
   - the zoom buttons;
   - the layer control;
   - the attribution;
   - popups;
   - a new caption card at the map's bottom left.

   The caption card says "Зудын эрсдэл, сум бүрээр / Dzud risk by soum" over "ERA5-Land · MODIS NDVI · ҮСХ / NSO". It follows the language.

5. **Popups do not push Mongolia off screen.**
   - Popup content is capped at about 280 px high and scrolls inside.
   - After opening the popup of any soum, at least half of Mongolia's bounding box stays in view at 1440×860.

6. **One source of colour for the page chrome.**
   - All page colours (ink, muted text, lines, background, accent, glass) are CSS custom properties in one place.
   - The hard-coded chrome hexes in `app.js` read those properties. These are the chart axis and label greys, `#1d2433`, `#5b6475`, `#d9dde5`, `#8a93a6`, `#9aa1ae` and `#3b6fd8`.
   - The data palettes (`COLORS`, `CHANCE`, `VULN`, `GREEN`, `DECREE_COLORS`, `ZONE_COLORS`) stay JS constants with their ColorBrewer values. One exception: the natural zones' desert colour `#d95f0e` changes, because it reads as the same orange as the risk classes. The new value is any brown that a person can tell apart from every risk class.
   - The accent is a single blue (spike value `#2f6fd6`). It is used for:
     - pressed segmented buttons;
     - the active tab;
     - the status card's button;
     - focus rings.

7. **Header.** The title gets "ZudRisk" beside it and grows to 20 px. Controls keep their order and labels. The level buttons get a visible label "Түвшин / Level", as the view and winter selects already have.

8. **The CSS moves out of `index.html`** into `site/style.css`. Cache-busting query strings go on `style.css` and `app.js` (`?v=0.7.0`).

### Introduction text for the Method tab

Use this text verbatim. The owner may edit it later.

- **MN:** "Зуд гэдэг нь өвөл, хаврын хүнд нөхцөлд (их цас, хүйтэн, өмнөх зуны ган) мал их хэмжээгээр хорогдох үзэгдэл. ZudRisk нь Монголын сум бүрийн зудын эрсдэлийг хиймэл дагуулын болон цаг агаарын нээлттэй өгөгдлөөр (ERA5-Land, MODIS NDVI) ба ҮСХ-ны малын тоогоор тооцож, өнгөрсөн 25 өвлийн хорогдолтой тулгаж шалгадаг."
- **EN:** "A dzud is a winter or spring disaster in which deep snow, cold or a dry summer before kills many livestock. ZudRisk estimates the risk for every soum of Mongolia from open satellite and weather data (ERA5-Land, MODIS NDVI) and NSO livestock counts, and checks it against the losses of the past 25 winters."

## Non-goals

- Splitting `app.js` into modules, or any change to how it computes or loads data.
- Pipeline, data files or numbers.
- New map layers, a dark mode, our own place labels, or translated basemap labels.
- Changing what any table, chart or popup says. They only move, or their box changes. One exception: `sources_text` adds one sentence crediting the Esri basemap, in both languages.

## Anti-goals: a failure even if it looks better

- Any existing behaviour stops working. That covers:
  - the five views (risk, vulnerability, greenness, natural zone, Resolution 286);
  - the three levels;
  - the 27 winters and the outlook;
  - the chance/class colour toggle;
  - soum search, which zooms and opens the popup;
  - the aimag and zone table links, which zoom;
  - popups and their charts;
  - the MN/EN switch, which must also cover the new tab names, card and caption;
  - the natural-zone overlay;
  - the phone layout (≤ 760 px, 44 px touch targets).
- A basemap or font that needs an API key, an account, or a paid plan.
- Validation numbers hidden or harder to reach than now. They move to the Results tab, one click away.

## Constraints

- Static site on GitHub Pages: `site/index.html`, `site/app.js`, now plus `site/style.css`. No build step and no new JS libraries. Leaflet 1.9.4 stays.
- Element `id`s that `app.js` writes into stay the same, so the existing render functions keep working.
- The 28 pipeline `--check`s must still pass. They do not touch the site.

## Approaches considered

1. **Port the spike as-is.** A script moves sections into tabs after the page loads. This is fast but fragile, and the page structure would no longer be readable from `index.html`. Rejected.
2. **Restructure the markup and CSS, with small edits to `app.js`.** The tabs are written into `index.html`. The CSS moves to `style.css` with tokens. `app.js` changes only for the basemap, tab switching, the status card, popup size, and reading the colour tokens. All `id`s are kept. **Chosen**, because it changes little and leaves a clear structure.
3. **Rewrite the front end in modules.** This is the cleanest result, but the riskiest for "do not break", and it adds nothing the audience sees. Rejected.

The throwaway spike that the owner approved by eye is at `scratchpad/spike-site/spike.{css,js}`. It is a reference for the look only, not code to copy.

## Left to the builder

- The exact sizes, spacing and border tones within the look above.
- How the tab state is kept: plain JS. Optionally, remember the last tab in `localStorage`, wrapped in `try/catch`.
- The new desert brown.
- How the 2009/10 button finds "the outlook". It can use the first option of the winter select, or `outlook.json`'s winter.
- Whether the yellow banner element is reused as the card body or replaced.

## Calls made (by Claude, for the owner to check)

- The status card wording above. It is the first text a visitor reads.
- Esri stays the default basemap with an automatic OSM fallback. This was the owner's choice (A) once the licence question was raised.
- The pan box is widened from the first draft (36–56° N, 82–125° E) so that popups are never clipped.
- Sources credits Esri in one added sentence.

## Acceptance (checked in a browser, desktop 1440×860 and phone 375×812)

1. On load, the map is fitted to Mongolia. The light grey basemap shows English labels above the soums. The Map tab is open with the status card first.
2. All three tabs open and show their sections. Every number shown before the change still appears somewhere.
3. The card's button switches to 2009/10, and the button then reads "back". Pressing it again returns to the outlook.
4. Blocking `server.arcgisonline.com`, for example with a DevTools request block, loads the page on OSM with no errors visible to the user.
5. Every view × level combination draws. The chance/class toggle, search, the table zoom links, the zone overlay, and switching to the OSM and OpenTopoMap basemaps all work.
6. A popup on a southern soum (Dornogovi) and on a northern one (Khövsgöl, near 51° N) is fully visible. Each leaves at least half of Mongolia in view.
7. MN ⇄ EN switches every new string.
8. At 375 px wide, the tabs stay usable and touch targets are at least 44 px.
9. There are no console errors. All 28 pipeline `--check`s pass.
