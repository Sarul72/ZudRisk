// Pure decisions of the page (site/ui.js): run `node --test "tests/site/*.test.js"`.
const test = require("node:test"), assert = require("node:assert/strict");
const ui = require("../../site/ui.js");

test("tabs: each section key has its tab", () => {
  assert.equal(ui.TAB_OF.validation_h, "res");
  assert.equal(ui.TAB_OF.sources, "how");
  assert.equal(ui.TAB_OF.legend, "map");
});
