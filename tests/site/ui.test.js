// Pure decisions of the page (site/ui.js): run `node --test "tests/site/*.test.js"`.
const test = require("node:test"), assert = require("node:assert/strict");
const ui = require("../../site/ui.js");

test("tabs: each section key has its tab", () => {
  assert.equal(ui.TAB_OF.validation_h, "res");
  assert.equal(ui.TAB_OF.sources, "how");
  assert.equal(ui.TAB_OF.legend, "map");
});

const T = { months: { oct: "10-р сар", nov: "11-р сар" }, banner: "B", no_losses_yet: "N",
  card_outlook: (w, m) => `${w} өвлийн төлөв · ${m}`, card_oct_line: "Өвлийн цаг агаар хараахан ороогүй; 11-р сараас сар бүр шинэчлэгдэнэ.",
  card_winter: (w) => `${w} өвөл`, card_observed: (w) => `${w} өвөл · ажигласан`,
  card_go: "2009/10-ын зудыг үзэх →", card_back: "← Одоогийн төлөв рүү буцах" };

test("status card says what is shown", () => {
  assert.deepEqual(ui.statusCard(T, { shown: "outlook", outlookWinter: "2026-27", stage: "oct", pending: false }),
    { title: "2026/27 өвлийн төлөв · 10-р сар", line: T.card_oct_line, button: T.card_go, target: "2009-10" });
  assert.equal(ui.statusCard(T, { shown: "outlook", outlookWinter: "2026-27", stage: "nov", pending: false }).line, "B");
  assert.deepEqual(ui.statusCard(T, { shown: "2025-26", outlookWinter: "2026-27", stage: "oct", pending: true }),
    { title: "2025/26 өвөл", line: "N", button: T.card_go, target: "2009-10" });
  assert.deepEqual(ui.statusCard(T, { shown: "2009-10", outlookWinter: "2026-27", stage: "oct", pending: false }),
    { title: "2009/10 өвөл · ажигласан", line: null, button: T.card_back, target: "outlook" });
});

test("status card without an outlook offers no way back", () => {
  assert.equal(ui.statusCard(T, { shown: "2009-10", outlookWinter: null, stage: null, pending: false }).target, null);
});

test("basemap falls back to OSM only when every first tile failed", () => {
  assert.equal(ui.shouldFallback(0, 6), true);
  assert.equal(ui.shouldFallback(1, 5), false);
  assert.equal(ui.shouldFallback(0, 0), false); // slow, not dead: nothing settled yet
});
