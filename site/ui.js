/* Small pure decisions of the page, kept apart from app.js so Node can test them (tests/site/ui.test.js).
   A classic script: the browser gets window.ZRui, Node gets module.exports. */
(function () {
  // which tab of the side panel each section (its h2 key: data-t, or the id) sits in
  const TAB_OF = {
    legend: "map", zone_table: "map", aimags: "map",
    validation_h: "res", national: "res", pooled: "res", stages: "res",
    model: "how", model_by_winter: "how", weights: "how", limits: "how", sources: "how",
  };
  const TABS = ["map", "res", "how"];

  /** Wires the [data-tab-btn] buttons under root to its section.pane[data-tab]; opens the stored tab, else "map". */
  function initTabs(root, store) {
    const buttons = [...root.querySelectorAll("[data-tab-btn]")];
    const panes = [...root.querySelectorAll("section.pane[data-tab]")];
    const show = (tab) => {
      for (const b of buttons) b.setAttribute("aria-selected", String(b.dataset.tabBtn === tab));
      for (const p of panes) p.hidden = p.dataset.tab !== tab;
      try { store?.setItem("zudrisk.tab", tab); } catch { /* private window: the tab is not remembered */ }
    };
    for (const b of buttons) b.addEventListener("click", () => show(b.dataset.tabBtn));
    let first = "map";
    try { const t = store?.getItem("zudrisk.tab"); if (TABS.includes(t)) first = t; } catch { /* ignore */ }
    show(first);
  }

  const label = (w) => w.replace("-", "/");
  const SHOWCASE = "2009-10"; // a well-known dzud winter, one click from the first screen

  /** What the status card says for what the map shows, and where its button goes ("outlook", a winter, or null). */
  function statusCard(t, s) {
    const outlook = s.shown === "outlook";
    const title = outlook ? t.card_outlook(label(s.outlookWinter), t.months[s.stage])
      : s.pending ? t.card_winter(label(s.shown)) : t.card_observed(label(s.shown));
    const line = outlook ? (s.stage === "oct" ? t.card_oct_line : t.banner) : s.pending ? t.no_losses_yet : null;
    const back = s.shown === SHOWCASE;
    return { title, line, button: back ? t.card_back : t.card_go, target: back ? (s.outlookWinter ? "outlook" : null) : SHOWCASE };
  }

  /** After the light grey basemap's first view settles: switch to OSM only if not one of its tiles loaded. */
  const shouldFallback = (loaded, errored) => loaded === 0 && errored > 0;

  const ui = { TAB_OF, TABS, initTabs, statusCard, shouldFallback };
  if (typeof module !== "undefined" && module.exports) module.exports = ui;
  else window.ZRui = ui;
})();
