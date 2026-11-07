// ZudRisk map: soum dzud risk per hindcast winter over OpenStreetMap, labels in Mongolian or English.
const COLORS = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]; // ColorBrewer YlOrRd-5
const GREY = "#bbbbbb";
const KEYS = ["cold", "snow", "summer", "pressure"];

const T = {
  mn: {
    title: "Зудын эрсдэл", subtitle: "Сум бүрээр, өнгөрсөн өвлүүдийн ретро тооцоо", winter: "Өвөл",
    legend: "Эрсдэлийн ангилал", validation: "Бодит хорогдолтой харьцуулалт",
    classes: ["Маш бага", "Бага", "Дунд", "Өндөр", "Маш өндөр"], none: "Тооцоогүй", ub: "Улаанбаатар: тооцоонд ороогүй",
    nodata: "Мэдээлэл хүрэлцээгүй",
    n: "Харьцуулсан сум", rho_soum: "Spearman ρ, сум", excess: "Spearman ρ, илүүдэл хорогдол",
    rho_aimag: "Spearman ρ, аймаг", top: "Эрсдэлийн дээд 20%-ийн хорогдлын дээд 20%-д орсон хувь",
    mort: "Хорогдол (аймгийн нийлбэр, УБ-гүй, хонин толгой)",
    aimag_only: "Энэ өвлийн сумын түвшний хорогдол Статистикийн хороонд байхгүй тул зөвхөн аймгаар харьцуулав.",
    pooled: "Бүх өвөл нийлүүлсэн", pooled_rho: "Spearman ρ, сум-өвөл", pooled_ex: "Spearman ρ, илүүдэл",
    validation_note: "Эрсдэлийн оноог дараа оны том малын хорогдол ÷ тухайн оны тооллого (хонин толгойд)-той харьцуулав. Илүүдэл хорогдол = тухайн сумын хоёр хэвийн өвлийн дунджаас давсан хэсэг. Жинг харьцуулахаас өмнө тогтоосон.",
    limits: "Хязгаарлалт",
    limits_text: "Дөрвөн үзүүлэлт: өвлийн хүйтэн (NASA POWER), цасны зузаан (NASA GLDAS — загварын үр дүн, хэмжилт биш), зуны бэлчээр (MODIS NDVI), малын нягт. Бүгдийг 2001–2020 оны дундажтай харьцуулна. 2009/10, 2013/14, 2015/16 нь энэ суурь үед өөрөө багтдаг тул тэдний z-оноо 2021 оноос хойших өвлүүдийнхээс бага зэрэг сулардаг. 2009/10 оны цас бараг бүх суманд хязгаартаа (z = 3) хүрсэн тул тэр өвлийн газрын зурагт цасны орон зайн ялгаа бараг байхгүй. Өвс тэжээлийн нөөц, малчдын бэлтгэл өгөгдөлд байхгүй, гэтэл эдгээр нь хорогдлын хэлбэлзлийн тал орчмыг тайлбарладаг (Nandintsetseg нар, 2018). Оноо нь жигнэсэн дундаж тул ганц аюул (жишээ нь зөвхөн их цас) хэт өндөр байсан ч бусад нь хэвийн бол оноо сулардаг. Энэ нь судалгааны ретро тооцоо бөгөөд сэрэмжлүүлэг биш.",
    sources: "Эх сурвалж",
    sources_text: "Суурь зураг © OpenStreetMap contributors (ODbL). Сумын хил: OCHA COD-AB, ҮСХ (CC BY-IGO). Агаарын температур: NASA POWER (MERRA-2). Цас: NASA GLDAS-2.1 Noah. NDVI: NASA MODIS MOD13C2. Мал, хорогдол: Үндэсний статистикийн хороо (1212.mn).",
    risk: "Эрсдэл", ind: { cold: "Хүйтэн", snow: "Цас", summer: "Зуны бэлчээр", pressure: "Ачаалал" },
    cold_c: "11–2 сарын дундаж", snow_cm: "Цасны хамгийн их сарын дундаж", ndvi: "7–8 сарын NDVI", su: "Хонин толгой / км²",
    missing: "Дутуу үзүүлэлт",
  },
  en: {
    title: "Dzud risk", subtitle: "Per soum, hindcasts of past winters", winter: "Winter",
    legend: "Risk class", validation: "Against recorded losses",
    classes: ["Very low", "Low", "Medium", "High", "Very high"], none: "Not scored", ub: "Ulaanbaatar: not scored",
    nodata: "Insufficient data",
    n: "Soums compared", rho_soum: "Spearman ρ, soum", excess: "Spearman ρ, excess mortality",
    rho_aimag: "Spearman ρ, aimag", top: "Top-20% risk soums in top-20% losses",
    mort: "Mortality (aimag totals, excl. Ulaanbaatar, sheep units)",
    aimag_only: "NSO has no soum-level losses for this winter, so it is compared by aimag only.",
    pooled: "All winters pooled", pooled_rho: "Spearman ρ, soum-winters", pooled_ex: "Spearman ρ, excess",
    validation_note: "Scores compared with the next year's adult losses ÷ that year's census, in sheep units. Excess mortality = a soum's losses above its mean in the two normal winters. Weights were fixed before any comparison.",
    limits: "Limits",
    limits_text: "Four indicators: winter cold (NASA POWER), snow depth (NASA GLDAS — model output, not observed), summer pasture (MODIS NDVI) and herd density, each against 2001–2020. 2009/10, 2013/14 and 2015/16 lie inside that baseline, so their z-scores are somewhat damped against winters from 2021 on. In 2009/10 snow hit the cap (z = 3) in almost every soum, so that winter's map shows almost no spatial contrast in snow. Hay reserves and herder preparedness are not in the data, yet they explain about half of the variation in losses (Nandintsetseg et al. 2018). The score is a weighted mean, so one extreme hazard (deep snow alone, say) is diluted when the others are normal. A research hindcast, not a warning.",
    sources: "Sources",
    sources_text: "Base map © OpenStreetMap contributors (ODbL). Soum boundaries: OCHA COD-AB, NSO Mongolia (CC BY-IGO). Air temperature: NASA POWER (MERRA-2). Snow: NASA GLDAS-2.1 Noah. NDVI: NASA MODIS MOD13C2. Livestock and losses: NSO Mongolia (1212.mn).",
    risk: "Risk", ind: { cold: "Cold", snow: "Snow", summer: "Summer pasture", pressure: "Pressure" },
    cold_c: "Nov–Feb mean", snow_cm: "Deepest monthly mean snow", ndvi: "Jul–Aug NDVI", su: "Sheep units / km²",
    missing: "Missing indicators",
  },
};

let lang = "mn", layer = null, validation = null, pooled = null, winters = [];

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

function popup(p) {
  const t = T[lang];
  const name = lang === "mn" ? `${p.name_mn}, ${p.aimag_mn}` : `${p.name_en}, ${p.aimag_en}`;
  if (p.risk_class === null) return `<b>${esc(name)}</b><br>${p.is_ub ? t.ub : t.nodata}`;
  const z = KEYS.map((k) => `${t.ind[k]} z: ${fmt(p[`z_${k}`])}`).join("<br>");
  const missing = KEYS.filter((k) => p[`z_${k}`] === null).map((k) => t.ind[k]);
  return `<b>${esc(name)}</b><br>${t.risk}: <b>${t.classes[p.risk_class]}</b> (${fmt(p.risk, 4)})<br>${z}<br>
    <small>${t.cold_c}: ${fmt(p.cold_c, 1)} °C · ${t.snow_cm}: ${fmt(p.snow_m === null ? null : p.snow_m * 100, 0)} cm ·
    ${t.ndvi}: ${fmt(p.ndvi, 2)} · ${t.su}: ${fmt(p.su_per_km2, 0)}</small>` +
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
  if (validation) {
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
  if (layer) layer.eachLayer((l) => l.setPopupContent(popup(l.feature.properties)));
}

async function load(label) {
  const [geo, v] = await Promise.all([
    fetch(`data/risk_${label}.geojson`).then((r) => r.json()),
    fetch(`data/validation_${label}.json`).then((r) => r.json()),
  ]);
  if (label !== sel.value) return; // a later choice won the race; drawing this one would mislabel the map
  validation = v;
  if (layer) map.removeLayer(layer);
  layer = L.geoJSON(geo, { style, onEachFeature: (f, l) => l.bindPopup(popup(f.properties)) }).addTo(map);
  render();
}

document.getElementById("lang").addEventListener("click", () => { lang = lang === "mn" ? "en" : "mn"; render(); });
sel.addEventListener("change", () => load(sel.value).catch(fail));

function fail(e) {
  document.getElementById("validation").textContent = `Data failed to load: ${e}`;
  console.error(e);
}

Promise.all([
  fetch("data/winters.json").then((r) => r.json()),
  fetch("data/pooled.json").then((r) => r.json()),
]).then(async ([w, p]) => {
  winters = w;
  pooled = p;
  sel.innerHTML = winters.map((x) => `<option value="${esc(x)}">${esc(x.replace("-", "/"))}</option>`).join("");
  sel.value = winters[winters.length - 1];
  await load(sel.value);
  map.fitBounds(layer.getBounds());
}).catch(fail);
render();
