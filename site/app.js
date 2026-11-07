// ZudRisk map: one winter's soum scores over OpenStreetMap, labels in Mongolian or English.
const WINTER = "2023-24";
const COLORS = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]; // ColorBrewer YlOrRd-5
const GREY = "#bbbbbb";

const T = {
  mn: {
    title: "Зудын эрсдэл", subtitle: "Сум бүрээр, 2023/24 оны өвөл (ретро тооцоо)",
    legend: "Эрсдэлийн ангилал", validation: "Бодит хорогдолтой харьцуулалт",
    classes: ["Маш бага", "Бага", "Дунд", "Өндөр", "Маш өндөр"], none: "Тооцоогүй (Улаанбаатар)",
    n: "Харьцуулсан сум", dropped: "Хасагдсан", rho_soum: "Spearman ρ, сум", rho_aimag: "Spearman ρ, аймаг",
    top: "Эрсдэлийн дээд 20%-ийн хорогдлын дээд 20%-д орсон хувь", mort: "Хорогдол, харьцуулсан сумд (УБ-гүй, хонин толгой)",
    validation_note: "Эрсдэлийн оноог 2024 оны том малын хорогдол ÷ 2023 оны мал тооллого (хонин толгойд)-той харьцуулав. Жинг харьцуулахаас өмнө тогтоосон.",
    limits: "Хязгаарлалт",
    limits_text: "Энэ хувилбар зөвхөн өвлийн хүйтэн (NASA POWER, 2001–2020 оны дундажтай харьцуулсан хазайлт) болон малын нягтыг ашиглана. Цасны зузаан, зуны бэлчээр (NDVI) v0.2-д нэмэгдэнэ. Өвс тэжээлийн нөөц, малчдын бэлтгэл өгөгдөлд байхгүй, гэтэл эдгээр нь малын хорогдлын хэлбэлзлийн тал орчмыг тайлбарладаг (Nandintsetseg нар, 2018). Оноо нь үзүүлэлтүүдийн жигнэсэн дундаж тул ганц аюул (жишээ нь зөвхөн их цас) хэт өндөр байсан ч бусад нь хэвийн бол оноо сулардаг. Энэ нь судалгааны ретро тооцоо бөгөөд сэрэмжлүүлэг биш.",
    sources: "Эх сурвалж",
    sources_text: "Суурь зураг © OpenStreetMap contributors (ODbL). Сумын хил: OCHA COD-AB, ҮСХ (CC BY-IGO). Агаарын температур: NASA POWER (MERRA-2). Мал, хорогдол: Үндэсний статистикийн хороо (1212.mn).",
    risk: "Эрсдэл", z_cold: "Хүйтний z", cold_c: "11–2 сарын дундаж", z_pressure: "Ачааллын z", su: "Хонин толгой / км²",
    ub: "Улаанбаатар: тооцоонд ороогүй",
  },
  en: {
    title: "Dzud risk", subtitle: "Per soum, winter 2023/24 (hindcast)",
    legend: "Risk class", validation: "Against recorded losses",
    classes: ["Very low", "Low", "Medium", "High", "Very high"], none: "Not scored (Ulaanbaatar)",
    n: "Soums compared", dropped: "Dropped", rho_soum: "Spearman ρ, soum", rho_aimag: "Spearman ρ, aimag",
    top: "Top-20% risk soums in top-20% losses", mort: "Mortality, compared soums (excl. Ulaanbaatar, sheep units)",
    validation_note: "Scores compared with 2024 adult losses ÷ 2023 census, in sheep units. Weights were fixed before this comparison.",
    limits: "Limits",
    limits_text: "This version uses winter cold only (NASA POWER, anomaly against 2001–2020) and herd density. Snow depth and summer pasture (NDVI) come in v0.2. Hay reserves and herder preparedness are not in the data, yet they explain about half of the variation in livestock losses (Nandintsetseg et al. 2018). The score is a weighted mean, so one extreme hazard (deep snow alone, say) is diluted when the others are normal. A research hindcast, not a warning.",
    sources: "Sources",
    sources_text: "Base map © OpenStreetMap contributors (ODbL). Soum boundaries: OCHA COD-AB, NSO Mongolia (CC BY-IGO). Air temperature: NASA POWER (MERRA-2). Livestock and losses: NSO Mongolia (1212.mn).",
    risk: "Risk", z_cold: "Cold z", cold_c: "Nov–Feb mean", z_pressure: "Pressure z", su: "Sheep units / km²",
    ub: "Ulaanbaatar: not scored",
  },
};

let lang = "mn", layer, validation;

const map = L.map("map", { minZoom: 4 }).setView([46.8, 103.5], 5);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const fmt = (v, d = 2) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));

function style(f) {
  const c = f.properties.risk_class;
  return { color: "#555", weight: 0.4, fillOpacity: 0.78, fillColor: c === null ? GREY : COLORS[c] };
}

function popup(p) {
  const t = T[lang];
  const name = lang === "mn" ? `${p.name_mn}, ${p.aimag_mn}` : `${p.name_en}, ${p.aimag_en}`;
  if (p.risk_class === null) return `<b>${esc(name)}</b><br>${t.ub}`;
  return `<b>${esc(name)}</b><br>${t.risk}: <b>${t.classes[p.risk_class]}</b> (${fmt(p.risk, 4)})<br>
    ${t.z_cold}: ${fmt(p.z_cold)} · ${t.cold_c}: ${fmt(p.cold_c, 1)} °C<br>
    ${t.z_pressure}: ${fmt(p.z_pressure)} · ${t.su}: ${fmt(p.su_per_km2, 0)}`;
}

function render() {
  const t = T[lang];
  document.documentElement.lang = lang;
  document.getElementById("lang").textContent = lang === "mn" ? "EN" : "МН";
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t[el.dataset.t]; });
  document.getElementById("legend").innerHTML =
    t.classes.map((c, i) => `<div><i style="background:${COLORS[4 - i]}"></i>${t.classes[4 - i]}</div>`).join("") +
    `<div><i style="background:${GREY}"></i>${t.none}</div>`;
  if (validation) {
    const v = validation;
    const rows = [[t.n, v.n], [t.dropped, v.n_dropped], [t.rho_soum, fmt(v.spearman_soum)],
      [t.rho_aimag, `${fmt(v.spearman_aimag)} (n=${v.n_aimag})`], [t.top, `${Math.round(v.top_quintile_hit * 100)}%`],
      [t.mort, `${fmt(v.mortality_pct_validated, 1)}%`]];
    document.getElementById("validation").innerHTML = rows.map(([k, x]) => `<tr><td>${k}</td><td>${x}</td></tr>`).join("");
  }
  if (layer) layer.eachLayer((l) => l.setPopupContent(popup(l.feature.properties)));
}

document.getElementById("lang").addEventListener("click", () => { lang = lang === "mn" ? "en" : "mn"; render(); });

Promise.all([
  fetch(`data/risk_${WINTER}.geojson`).then((r) => r.json()),
  fetch(`data/validation_${WINTER}.json`).then((r) => r.json()),
]).then(([geo, v]) => {
  validation = v;
  layer = L.geoJSON(geo, { style, onEachFeature: (f, l) => l.bindPopup(popup(f.properties)) }).addTo(map);
  map.fitBounds(layer.getBounds());
  render();
}).catch((e) => {
  document.getElementById("validation").textContent = `Data failed to load: ${e}`;
  console.error(e);
});
render();
