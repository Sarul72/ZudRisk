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
