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
