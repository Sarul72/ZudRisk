// ZudRisk map: soum dzud risk per hindcast winter over OpenStreetMap, labels in Mongolian or English.
const COLORS = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]; // ColorBrewer YlOrRd-5
const GREY = "#bbbbbb";
const KEYS = ["cold", "snow", "summer", "pressure"];

const T = {
  mn: {
    title: "Зудын эрсдэл", subtitle: "Сум бүрээр: өнгөрсөн өвлүүдийн ретро тооцоо ба 2026/27 оны урьдчилсан төлөв", winter: "Өвөл",
    legend: "Эрсдэлийн ангилал", validation: "Бодит хорогдолтой харьцуулалт",
    classes: ["Маш бага", "Бага", "Дунд", "Өндөр", "Маш өндөр"], none: "Тооцоогүй / мэдээлэл хүрэлцээгүй", ub: "Улаанбаатар: тооцоонд ороогүй",
    nodata: "Мэдээлэл хүрэлцээгүй",
    n: "Харьцуулсан сум", rho_soum: "Spearman ρ, сум", excess: "Spearman ρ, илүүдэл хорогдол",
    rho_aimag: "Spearman ρ, аймаг", top: "Эрсдэлийн дээд 20%-ийн хорогдлын дээд 20%-д орсон хувь",
    mort: "Хорогдол (аймгийн нийлбэр, УБ-гүй, хонин толгой)",
    aimag_only: "Энэ өвлийн сумын түвшний хорогдол Статистикийн хороонд байхгүй тул зөвхөн аймгаар харьцуулав.",
    pooled: "Бүх өвөл нийлүүлсэн", pooled_rho: "Spearman ρ, сум-өвөл", pooled_ex: "Spearman ρ, илүүдэл",
    validation_note: "Эрсдэлийн оноог дараа оны том малын хорогдол ÷ тухайн оны тооллого (хонин толгойд)-той харьцуулав. Илүүдэл хорогдол = тухайн сумын хоёр хэвийн өвлийн дунджаас давсан хэсэг. Жинг харьцуулахаас өмнө тогтоосон.",
    limits: "Хязгаарлалт",
    limits_text: "Дөрвөн үзүүлэлт: өвлийн хүйтэн ба цасны зузаан (Copernicus ERA5-Land — загварын үр дүн, хэмжилт биш), зуны бэлчээр (MODIS NDVI), малын нягт. Бүгдийг 2001–2020 оны дундажтай харьцуулна. 2009/10, 2013/14, 2015/16 нь энэ суурь үед өөрөө багтдаг тул тэдний z-оноо 2021 оноос хойших өвлүүдийнхээс бага зэрэг сулардаг. Цасыг v0.3-аас ERA5-Land-аас авна: шинэчлэгдэх хоцрогдол бага гэдгээр харьцуулалтаас өмнө сонгосон. NASA GLDAS-2.1-ийг зөвхөн харьцуулалтад үлдээсэн (docs/research/snow-comparison.md). Цастай өдөр ба цасны нягт нь зөвхөн харуулах зориулалттай, оноонд ороогүй, шалгагдаагүй. Хүйтнийг v0.4-өөс NASA POWER-оос биш ERA5-Land-аас авна: POWER 5–6 долоо хоног хоцордог. Аймгийн төвийн малын нягтыг аймгийн дунджаар авна: тэнд бүртгэлтэй мал аймгийн бэлчээрт бэлчдэг. Урьдчилсан төлөвт малын тооллогыг нийтлэгдсэний дараа (дараа оны 2-р сарын 1-нээс гэж үзэв) л ашиглана. Өвс тэжээлийн нөөц, малчдын бэлтгэл өгөгдөлд байхгүй, гэтэл эдгээр нь хорогдлын хэлбэлзлийн тал орчмыг тайлбарладаг (Nandintsetseg нар, 2018). Оноо нь жигнэсэн дундаж тул ганц аюул (жишээ нь зөвхөн их цас) хэт өндөр байсан ч бусад нь хэвийн бол оноо сулардаг. Энэ нь судалгааны ретро тооцоо бөгөөд сэрэмжлүүлэг биш.",
    sources: "Эх сурвалж",
    sources_text: "Суурь зураг © OpenStreetMap contributors (ODbL). Сумын хил: OCHA COD-AB, ҮСХ (CC BY-IGO). Агаарын температур, цас: Copernicus ERA5-Land (C3S, CC BY); цасны харьцуулалт: NASA GLDAS-2.1 Noah. Contains modified Copernicus Climate Change Service information (2026). NDVI: NASA MODIS MOD13C2. Мал, хорогдол: Үндэсний статистикийн хороо (1212.mn).",
    risk: "Эрсдэл", ind: { cold: "Хүйтэн", snow: "Цас", summer: "Зуны бэлчээр", pressure: "Ачаалал" },
    cold_c: "11–2 сарын дундаж", snow_cm: "Цасны хамгийн их сарын дундаж", ndvi: "7–8 сарын NDVI", su: "Хонин толгой / км²",
    missing: "Дутуу үзүүлэлт",
    snow_days: "Цастай өдөр", density: "Цасны хамгийн их нягт", unit_density: "кг/м³",
    months: { oct: "10-р сар", nov: "11-р сар", dec: "12-р сар", jan: "1-р сар", feb: "2-р сар", mar: "3-р сар" },
    outlook_opt: (m) => `төлөв (${m} хүртэл)`, not_observed: "ажиглагдаагүй",
    banner: "Өвөл үргэлжилж байна: энэ бол урьдчилсан төлөв, ажигласан өвөл биш. Хүйтэн ба цасны мэдээ сар бүр нэмэгдэнэ.",
    stage_validation: "Энэ шатны өмнөх өвлүүдийн шалгалт", stages: "Шат бүрийн нарийвчлал (өвлүүд нийлүүлсэн ρ)",
    stage_note: "Өмнөх зургаан өвлийг зөвхөн энэ шатанд гарсан байх мэдээгээр дахин тооцож, бодит хорогдолтой харьцуулав. Ганц үл хамаарал: 2001–2020 оны суурь нь 2009/10, 2013/14, 2015/16-аас хойших жилүүдийг агуулдаг.",
    level_soum: "Сум", level_aimag: "Аймаг", level: "Харах түвшин", aimags: "Аймгууд (эрсдэлээр)",
    aimag_risk: "Сумдын эрсдэлийг малын тоогоор жигнэсэн дундаж", soums_n: "сум", zoom_to: "Газрын зураг дээр харах",
    aimag_suffix: " (аймаг)", centre: " (аймгийн төв: аймгийн дундаж)",
    proxy: "Тогтоол 286: цагаан зуд ≥ 250, төмөр зуд ≥ 350 кг/м³. ERA5-Land-ын сумын сарын дундаж (цасны зузаанаар жигнэсэн) 2001–2024 онд хамгийн ихдээ 240 орчим хүрсэн тул z-ээр нь харьцуулна. Шалгагдаагүй орлуулагч, оноонд ороогүй.",
  },
  en: {
    title: "Dzud risk", subtitle: "Per soum: hindcasts of past winters and the 2026/27 outlook", winter: "Winter",
    legend: "Risk class", validation: "Against recorded losses",
    classes: ["Very low", "Low", "Medium", "High", "Very high"], none: "Not scored / insufficient data", ub: "Ulaanbaatar: not scored",
    nodata: "Insufficient data",
    n: "Soums compared", rho_soum: "Spearman ρ, soum", excess: "Spearman ρ, excess mortality",
    rho_aimag: "Spearman ρ, aimag", top: "Top-20% risk soums in top-20% losses",
    mort: "Mortality (aimag totals, excl. Ulaanbaatar, sheep units)",
    aimag_only: "NSO has no soum-level losses for this winter, so it is compared by aimag only.",
    pooled: "All winters pooled", pooled_rho: "Spearman ρ, soum-winters", pooled_ex: "Spearman ρ, excess",
    validation_note: "Scores compared with the next year's adult losses ÷ that year's census, in sheep units. Excess mortality = a soum's losses above its mean in the two normal winters. Weights were fixed before any comparison.",
    limits: "Limits",
    limits_text: "Four indicators: winter cold and snow depth (Copernicus ERA5-Land — model output, not observed), summer pasture (MODIS NDVI) and herd density, each against 2001–2020. 2009/10, 2013/14 and 2015/16 lie inside that baseline, so their z-scores are somewhat damped against winters from 2021 on. From v0.3 snow comes from ERA5-Land, chosen before any comparison because it is updated sooner. NASA GLDAS-2.1 is kept as a comparison only (docs/research/snow-comparison.md). Snow-cover days and snow density are shown, not scored, and are unvalidated. From v0.4 cold also comes from ERA5-Land rather than NASA POWER, which runs 5–6 weeks late. An aimag centre takes its aimag's herd density: the herds registered in the town graze the aimag. The outlook uses a livestock census only once published (taken as 1 February of the next year). Hay reserves and herder preparedness are not in the data, yet they explain about half of the variation in losses (Nandintsetseg et al. 2018). The score is a weighted mean, so one extreme hazard (deep snow alone, say) is diluted when the others are normal. A research hindcast, not a warning.",
    sources: "Sources",
    sources_text: "Base map © OpenStreetMap contributors (ODbL). Soum boundaries: OCHA COD-AB, NSO Mongolia (CC BY-IGO). Air temperature and snow: Copernicus ERA5-Land (C3S, CC BY); snow comparison: NASA GLDAS-2.1 Noah. Contains modified Copernicus Climate Change Service information (2026). NDVI: NASA MODIS MOD13C2. Livestock and losses: NSO Mongolia (1212.mn).",
    risk: "Risk", ind: { cold: "Cold", snow: "Snow", summer: "Summer pasture", pressure: "Pressure" },
    cold_c: "Nov–Feb mean", snow_cm: "Deepest monthly mean snow", ndvi: "Jul–Aug NDVI", su: "Sheep units / km²",
    missing: "Missing indicators",
    snow_days: "Snow-cover days", density: "Densest monthly snow", unit_density: "kg/m³",
    months: { oct: "Oct", nov: "Nov", dec: "Dec", jan: "Jan", feb: "Feb", mar: "Mar" },
    outlook_opt: (m) => `outlook (data to ${m})`, not_observed: "not observed yet",
    banner: "Winter under way: an outlook, not an observed winter. Cold and snow are added month by month.",
    stage_validation: "How this stage did on past winters", stages: "Skill by stage (ρ over pooled winters)",
    stage_note: "The six past winters re-scored with only the data this stage would have had, against their recorded losses. One exception: the 2001–2020 baseline post-dates 2009/10, 2013/14 and 2015/16.",
    level_soum: "Soum", level_aimag: "Aimag", level: "Map level", aimags: "Aimags (by risk)",
    aimag_risk: "Soum risk weighted by herd size", soums_n: "soums", zoom_to: "Show on the map",
    aimag_suffix: " (aimag)", centre: " (aimag centre: the aimag's density)",
    proxy: "Resolution 286: white dzud ≥ 250, iron dzud ≥ 350 kg/m³. ERA5-Land soum monthly means (weighted by snow depth) peaked near 240 in 2001–2024, so read the z. Unvalidated proxy, not scored.",
  },
};

let lang = "mn", layer = null, validation = null, pooled = null, winters = [], asof = null, outlook = null;
let level = "soum", shown = null, soumGeo = null, aimagGeo = null, aimagScores = {}, borders = null;
const isOutlook = () => shown === "outlook"; // the view on the map, not a choice whose data is still loading

const map = L.map("map", { minZoom: 4 }).setView([46.8, 103.5], 5);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const fmt = (v, d = 2) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));
const sel = document.getElementById("winter");

function style(f) {
  const c = f.properties.risk_class;
  return { color: "#555", weight: 0.4, fillOpacity: 0.78, fillColor: c === null ? GREY : COLORS[c] };
}

function aimagStyle(f) {
  const c = aimagScores[f.properties.pcode]?.risk_class ?? null;
  return { color: "#333", weight: 1, fillOpacity: 0.78, fillColor: c === null ? GREY : COLORS[c] };
}

function aimagName(p) {
  return lang === "mn" ? p.name_mn : p.name_en;
}

function aimagPopup(p) {
  const t = T[lang], a = aimagScores[p.pcode];
  if (!a || a.risk_class === null) return `<b>${esc(aimagName(p))}</b><br>${p.is_ub ? t.ub : t.nodata}`;
  const counts = a.counts.map((n, i) => `<i class="chip" style="background:${COLORS[i]}"></i>${esc(t.classes[i])}: ${n}`)
    .reverse().join("<br>");
  return `<b>${esc(aimagName(p))}</b><br>${t.risk}: <b>${t.classes[a.risk_class]}</b> (${fmt(a.risk, 4)})<br>
    <small>${t.aimag_risk}</small><br>${counts}<br><small>${a.n} ${t.soums_n}</small>`;
}

function popup(p) {
  const t = T[lang];
  const name = lang === "mn" ? `${p.name_mn}, ${p.aimag_mn}` : `${p.name_en}, ${p.aimag_en}`;
  if (p.risk_class === null) return `<b>${esc(name)}</b><br>${p.is_ub ? t.ub : t.nodata}`;
  const unseen = (k) => p.stage === "oct" && (k === "cold" || k === "snow"); // pre-winter: no winter month yet
  const z = KEYS.map((k) => `${t.ind[k]} z: ${unseen(k) ? t.not_observed : fmt(p[`z_${k}`])}`).join("<br>");
  const missing = KEYS.filter((k) => p[`z_${k}`] === null && !unseen(k)).map((k) => t.ind[k]);
  return `<b>${esc(name)}</b><br>${t.risk}: <b>${t.classes[p.risk_class]}</b> (${fmt(p.risk, 4)})<br>${z}<br>
    <small>${t.cold_c}: ${fmt(p.cold_c, 1)} °C · ${t.snow_cm}: ${fmt(p.snow_m === null ? null : p.snow_m * 100, 0)} cm ·
    ${t.ndvi}: ${fmt(p.ndvi, 2)} · ${t.su}: ${fmt(p.su_per_km2, 0)}${p.is_centre ? t.centre : ""}</small>
    <br><small>${t.snow_days}: ${fmt(p.snow_days, 0)} · ${t.density}: ${fmt(p.density_kgm3, 0)} ${t.unit_density} (z ${fmt(p.z_density)})
    <br><i>${t.proxy}</i></small>` +
    (missing.length ? `<br><i>${t.missing}: ${missing.join(", ")}</i>` : "");
}

function table(rows) {
  return rows.map(([k, x]) => `<tr><td>${esc(k)}</td><td>${esc(x)}</td></tr>`).join("");
}

function render() {
  const t = T[lang];
  document.documentElement.lang = lang;
  document.getElementById("lang").textContent = lang === "mn" ? "EN" : "МН";
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t[el.dataset.t]; });
  document.getElementById("legend").innerHTML =
    t.classes.map((_, i) => `<div><i style="background:${COLORS[4 - i]}"></i>${t.classes[4 - i]}</div>`).join("") +
    `<div><i style="background:${GREY}"></i>${t.none}</div>`;
  const outlookOpt = sel.querySelector('option[value="outlook"]');
  if (outlook && outlookOpt) outlookOpt.textContent = `${outlook.winter.replace("-", "/")} — ${t.outlook_opt(t.months[outlook.stage])}`;
  document.getElementById("banner").hidden = !isOutlook();
  document.getElementById("banner").textContent = t.banner;
  document.getElementById("validation_h").textContent = isOutlook() ? t.stage_validation : t.validation;
  if (asof) {
    document.getElementById("stages").innerHTML = Object.entries(asof).map(([k, s]) => {
      const row = `<td>${esc(t.months[k])}</td><td>${fmt(s.pooled.spearman)} (n=${esc(s.pooled.n)})</td>`;
      return isOutlook() && outlook && k === outlook.stage ? `<tr style="font-weight:600">${row}</tr>` : `<tr>${row}</tr>`;
    }).join("");
  }
  if (isOutlook() && validation) {
    const rows = Object.entries(validation.winters).map(([w, v]) => [w.replace("-", "/"),
      v.spearman_soum === null ? `${fmt(v.spearman_aimag)}${t.aimag_suffix}` : `${fmt(v.spearman_soum)} (n=${v.n})`]);
    document.getElementById("validation").innerHTML = table([...rows, [t.pooled_rho, `${fmt(validation.pooled.spearman)} (n=${validation.pooled.n})`]]);
    document.getElementById("unit_note").textContent = t.stage_note;
  } else if (validation) {
    const v = validation;
    document.getElementById("validation").innerHTML = table([
      [t.n, v.n], [t.rho_soum, fmt(v.spearman_soum)], [t.excess, fmt(v.excess_spearman_soum)],
      [t.rho_aimag, `${fmt(v.spearman_aimag)} (n=${v.n_aimag})`],
      [t.top, v.top_quintile_hit === null ? "–" : `${Math.round(v.top_quintile_hit * 100)}%`],
      [t.mort, `${fmt(v.mortality_pct, 1)}%`],
    ]);
    document.getElementById("unit_note").textContent = v.validation_unit === "aimag" ? t.aimag_only : "";
  }
  if (pooled) {
    document.getElementById("pooled").innerHTML = table([
      [t.pooled_rho, `${fmt(pooled.spearman)} (n=${pooled.n})`], [t.pooled_ex, `${fmt(pooled.spearman_excess)} (n=${pooled.n_excess})`],
    ]);
  }
  for (const b of document.querySelectorAll("[data-level]")) {
    b.textContent = t[`level_${b.dataset.level}`];
    b.setAttribute("aria-pressed", String(b.dataset.level === level));
  }
  document.getElementById("level").setAttribute("aria-label", t.level);
  if (aimagGeo) {
    const rank = (pc) => aimagScores[pc]?.risk ?? -Infinity;
    document.getElementById("aimags").innerHTML = aimagGeo.features.map((f) => f.properties)
      .sort((a, b) => rank(b.pcode) - rank(a.pcode))
      .map((p) => {
        const a = aimagScores[p.pcode], c = a?.risk_class ?? null;
        return `<tr tabindex="0" role="button" data-aimag="${esc(p.pcode)}" title="${esc(t.zoom_to)}">` +
          `<td><i class="chip" style="background:${c === null ? GREY : COLORS[c]}"></i>${esc(aimagName(p))}</td>` +
          `<td>${c === null ? "–" : esc(t.classes[c])} ${a?.risk == null ? "" : fmt(a.risk)}</td></tr>`;
      }).join("");
  }
  if (layer) layer.eachLayer((l) => l.setPopupContent(level === "aimag" ? aimagPopup(l.feature.properties) : popup(l.feature.properties)));
}

function draw() {
  if (layer) map.removeLayer(layer);
  if (borders) map.removeLayer(borders);
  borders = null;
  if (level === "aimag") {
    layer = L.geoJSON(aimagGeo, { style: aimagStyle, onEachFeature: (f, l) => l.bindPopup(aimagPopup(f.properties)) }).addTo(map);
  } else {
    layer = L.geoJSON(soumGeo, { style, onEachFeature: (f, l) => l.bindPopup(popup(f.properties)) }).addTo(map);
    borders = L.geoJSON(aimagGeo, { style: { color: "#222", weight: 1.6, fill: false }, interactive: false }).addTo(map);
  }
  render();
}

function zoomToAimag(pcode) {
  const f = aimagGeo.features.find((x) => x.properties.pcode === pcode);
  if (!f) return;
  map.fitBounds(L.geoJSON(f).getBounds());
  if (level === "aimag" && layer) layer.eachLayer((l) => { if (l.feature.properties.pcode === pcode) l.openPopup(); });
}

async function load(label) {
  const key = label === "outlook" ? outlook.winter : label;
  const [geo, v, a] = await Promise.all([
    fetch(label === "outlook" ? `data/outlook_${key}.geojson` : `data/risk_${key}.geojson`).then((r) => r.json()),
    label === "outlook" ? asof[outlook.stage] : fetch(`data/validation_${key}.json`).then((r) => r.json()),
    fetch(`data/aimag_${key}.json`).then((r) => (r.ok ? r.json() : {})), // missing: aimags grey, soums still drawn
  ]);
  if (label !== sel.value) return; // a later choice won the race; drawing this one would mislabel the map
  shown = label;
  validation = v;
  soumGeo = geo;
  aimagScores = a;
  draw();
}

document.getElementById("lang").addEventListener("click", () => { lang = lang === "mn" ? "en" : "mn"; render(); });
for (const b of document.querySelectorAll("[data-level]")) {
  b.addEventListener("click", () => { if (level !== b.dataset.level) { level = b.dataset.level; if (soumGeo) draw(); else render(); } });
}
const aimagTable = document.getElementById("aimags");
aimagTable.addEventListener("click", (e) => { const r = e.target.closest("[data-aimag]"); if (r) zoomToAimag(r.dataset.aimag); });
aimagTable.addEventListener("keydown", (e) => {
  const r = e.target.closest("[data-aimag]");
  if (r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); zoomToAimag(r.dataset.aimag); }
});
sel.addEventListener("change", () => load(sel.value).catch(fail));

function fail(e) {
  document.getElementById("validation").textContent = `Data failed to load: ${e}`;
  console.error(e);
}

Promise.all([
  fetch("data/winters.json").then((r) => r.json()),
  fetch("data/pooled.json").then((r) => r.json()),
  fetch("data/asof_validation.json").then((r) => r.json()),
  fetch("data/outlook.json").then((r) => (r.ok ? r.json() : null)),
  fetch("data/aimags.geojson").then((r) => r.json()),
]).then(async ([w, p, a, o, g]) => {
  aimagGeo = g;
  winters = w;
  pooled = p;
  asof = a;
  outlook = o;
  sel.innerHTML = (outlook ? '<option value="outlook"></option>' : "") +
    winters.map((x) => `<option value="${esc(x)}">${esc(x.replace("-", "/"))}</option>`).join("");
  sel.value = outlook ? "outlook" : winters[winters.length - 1];
  await load(sel.value);
  map.fitBounds(layer.getBounds());
}).catch(fail);
render();
