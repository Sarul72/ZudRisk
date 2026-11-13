// Structure of the static site (site/index.html, site/style.css, site/app.js), read as text: run `node --test tests/site/`.
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
  for (const id of ["level", "view", "winter", "search", "soums", "lang", "banner", "scale_row", "scale_l", "scale", "legend",
    "layer_note", "zones", "zone_note", "aimags", "validation_h", "validation", "unit_note", "national_chart", "pooled", "stages",
    "model_table", "model_note", "model_chart", "weights", "map"])
    assert.equal((html.match(new RegExp(`id="${id}"`, "g")) || []).length, 1, id);
});

test("each section sits in its tab", () => {
  const { TAB_OF } = require("../../site/ui.js");
  const h2s = [...html.matchAll(/<h2 (?:data-t="([^"]+)"|id="([^"]+)")/g)];
  assert.equal(h2s.length, 12, "all twelve sections are still there");
  for (const m of h2s) {
    const key = m[1] || m[2];
    const before = html.slice(0, m.index);
    const pane = [...before.matchAll(/<section class="pane" data-tab="(\w+)"/g)].pop();
    assert.ok(pane, `${key} is inside a pane`);
    assert.equal(pane[1], TAB_OF[key], key);
  }
});

test("no chrome hex in app.js, and a desert colour apart from the risk colours", () => {
  const js = fs.readFileSync("site/app.js", "utf8");
  for (const hex of ["#1d2433", "#5b6475", "#d9dde5", "#8a93a6", "#9aa1ae", "#3b6fd8"])
    assert.ok(!js.includes(hex), `${hex} still hard-coded`);
  const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const palette = (name) => JSON.parse(js.match(new RegExp(String.raw`const ${name} = (\[[^\]]*\])`))[1]);
  const desert = js.match(/desert: "(#[0-9a-fA-F]{6})"/)[1];
  for (const c of [...palette("COLORS"), ...palette("CHANCE")]) {
    const d = Math.hypot(...rgb(desert).map((v, i) => v - rgb(c)[i]));
    assert.ok(d > 60, `desert ${desert} too close to ${c} (${d.toFixed(0)})`);
  }
});

test("caption on the map, in both languages, and capped popups", () => {
  assert.match(html, /id="caption"/);
  const js = fs.readFileSync("site/app.js", "utf8");
  assert.equal((js.match(/caption_title: "/g) || []).length, 2, "caption_title in MN and EN");
  assert.equal((js.match(/caption_src: "/g) || []).length, 2, "caption_src in MN and EN");
  const css = fs.readFileSync("site/style.css", "utf8");
  assert.match(css, /\.leaflet-popup-content\s*\{[^}]*max-height:\s*280px/);
  assert.match(css, /backdrop-filter/);
});

test("plain words: no 'retro', greenness not called desertification outright, the chance says what may happen", () => {
  const js = fs.readFileSync("site/app.js", "utf8");
  for (const bad of ["ретро", "(цөлжилт)", "Нийлүүлсэн шалгалт", "11–2 сарын дундаж", "Хорогдол ≥5% болох магадлал",
    "(desertification)", "Pooled test", "Chance of losses ≥5%"])
    assert.ok(!js.includes(bad), `still says: ${bad}`);
  assert.ok(js.includes("Малын 5% ба түүнээс дээш нь хорогдох магадлал"), "MN chance names the event");
  assert.ok(js.includes("Chance that 5% or more of the herd dies"), "EN chance names the event");
  assert.equal((js.match(/res_q: "/g) || []).length, 2, "the Results tab opens with its question, MN and EN");
  assert.match(html, /data-t="res_q"/);
});
