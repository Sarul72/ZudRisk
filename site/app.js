// ZudRisk map: soum dzud risk per hindcast winter, the learned vulnerability layer and the greenness trend,
// over OpenStreetMap or OpenTopoMap, labels in Mongolian or English. Charts are hand-made SVG.
const COLORS = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]; // ColorBrewer YlOrRd-5
const VULN = ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"]; // ColorBrewer Purples-5
const GREEN = ["#a6611a", "#f5f5f5", "#c7e9c0", "#74c476", "#238b45"]; // browning, then ColorBrewer Greens
const VULN_CUTS = [0.1, 0.2, 0.3, 0.4];
const GREEN_CUTS = [0, 0.01, 0.02, 0.04];
const RISK_CUTS = [-1, -0.5, 0.5, 1]; // pipeline/score.py CUTS
const GREY = "#bbbbbb";
const KEYS = ["cold", "snow", "summer", "pressure"];

const T = {
  mn: {
    title: "Зудын эрсдэл", subtitle: "Сум бүрээр: 15 өвлийн ретро тооцоо, 2026/27 оны төлөв, эмзэг байдал, ногоорлын чиг хандлага", winter: "Өвөл",
    view: "Давхарга", views: { risk: "Зудын эрсдэл (сонгосон өвөл)", vuln: "Эмзэг байдал (сургасан загвар)", green: "Ногоорлын чиг хандлага (цөлжилт)" },
    search: "Сум хайх", legend: "Тайлбар", validation: "Бодит хорогдолтой харьцуулалт",
    classes: ["Маш бага", "Бага", "Дунд", "Өндөр", "Маш өндөр"], none: "Тооцоогүй / мэдээлэл хүрэлцээгүй",
    ub: "Улаанбаатар: бүртгэлтэй мал байхгүй тул тооцоогүй", ub_density: " (Улаанбаатарын дундаж)",
    nodata: "Мэдээлэл хүрэлцээгүй",
    n: "Харьцуулсан сум", rho_soum: "Spearman ρ, сум", excess: "Spearman ρ, илүүдэл хорогдол",
    rho_aimag: "Spearman ρ, аймаг", top: "Эрсдэлийн дээд 20%-ийн хорогдлын дээд 20%-д орсон хувь",
    mort: "Хорогдол (аймгийн нийлбэр, УБ-гүй, хонин толгой)",
    aimag_only: "Энэ өвлийн сумын түвшний хорогдол Статистикийн хороонд байхгүй тул зөвхөн аймгаар харьцуулав.",
    pooled: "Нийлүүлсэн шалгалт", pooled_rho: "Spearman ρ, урьдчилан тогтоосон өвлүүд", pooled_ex: "Spearman ρ, илүүдэл",
    every: "Spearman ρ, бүх 14 өвөл (урьдчилан тогтоогоогүй)",
    validation_note: "Эрсдэлийн оноог дараа оны том малын хорогдол ÷ тухайн оны тооллого (хонин толгойд)-той харьцуулав. Илүүдэл хорогдол = тухайн сумын хоёр хэвийн өвлийн дунджаас давсан хэсэг. Жинг харьцуулахаас өмнө тогтоосон.",
    national: "Хорогдол өвөл бүрээр (аймгийн нийлбэр, УБ-гүй)",
    limits: "Хязгаарлалт",
    limits_text: "Дөрвөн үзүүлэлт: өвлийн хүйтэн ба цасны зузаан (Copernicus ERA5-Land — загварын үр дүн, хэмжилт биш), зуны бэлчээр (MODIS NDVI), малын нягт. Бүгдийг 2001–2020 оны дундажтай харьцуулна. 2009/10, 2013/14, 2015/16 нь энэ суурь үед өөрөө багтдаг тул тэдний z-оноо 2021 оноос хойших өвлүүдийнхээс бага зэрэг сулардаг. Цасыг v0.3-аас ERA5-Land-аас авна: шинэчлэгдэх хоцрогдол бага гэдгээр харьцуулалтаас өмнө сонгосон. NASA GLDAS-2.1-ийг зөвхөн харьцуулалтад үлдээсэн (docs/research/snow-comparison.md). Цастай өдөр ба цасны нягт нь зөвхөн харуулах зориулалттай, оноонд ороогүй, шалгагдаагүй. Хүйтнийг v0.4-өөс NASA POWER-оос биш ERA5-Land-аас авна: POWER 5–6 долоо хоног хоцордог. Аймгийн төвийн малын нягтыг аймгийн дунджаар авна: тэнд бүртгэлтэй мал аймгийн бэлчээрт бэлчдэг. Улаанбаатарын малтай зургаан дүүрэг хотын нийт нягтыг мөн ийм байдлаар авна; мал бүртгэлгүй гурван дүүргийг тооцоогүй: мал байхгүй бол зудын эрсдэл ч байхгүй. Урьдчилсан төлөвт малын тооллогыг нийтлэгдсэний дараа (дараа оны 2-р сарын 1-нээс гэж үзэв) л ашиглана. Өвс тэжээлийн нөөц, малчдын бэлтгэл өгөгдөлд байхгүй, гэтэл эдгээр нь хорогдлын хэлбэлзлийн тал орчмыг тайлбарладаг (Nandintsetseg нар, 2018). Оноо нь жигнэсэн дундаж тул ганц аюул (жишээ нь зөвхөн их цас) хэт өндөр байсан ч бусад нь хэвийн бол оноо сулардаг. Энэ нь судалгааны ретро тооцоо бөгөөд сэрэмжлүүлэг биш.",
    sources: "Эх сурвалж",
    sources_text: "Суурь зураг © OpenStreetMap contributors (ODbL); топограф: OpenTopoMap (CC-BY-SA), SRTM. Сумын хил: OCHA COD-AB, ҮСХ (CC BY-IGO). Агаарын температур, цас: Copernicus ERA5-Land (C3S, CC BY); цасны харьцуулалт: NASA GLDAS-2.1 Noah. Contains modified Copernicus Climate Change Service information (2026). NDVI: NASA MODIS MOD13C2. Мал, хорогдол: Үндэсний статистикийн хороо (1212.mn).",
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
    hist_caption: "Хорогдол (багана, хамгийн ихийг дээр нь) ба эрсдэлийн ангилал (зурвас) өвөл бүрээр",
    vuln: "Эмзэг байдал", vuln_unit: "хорогдол ≥5% болох магадлал",
    vuln_legend: "Хорогдол ≥5% болох магадлал, 20 өвлийн дундаж", vuln_classes: ["< 10%", "10–20%", "20–30%", "30–40%", "≥ 40%"],
    vuln_note: (m) => `Загвар нь ${m.train[0].replace("-", "/")}–${m.train[m.train.length - 1].replace("-", "/")} оны ${m.train.length} өвлийн сум-өвөл бүрээс хорогдол 5%-иас давах эсэхийг сурсан (ridge логистик регресс). Эмзэг байдал = ${m.replay[0].replace("-", "/")}–${m.replay[1].replace("-", "/")} оны 20 өвлийн цаг агаарыг ${m.census} оны малын тоо, бэлчээрийн одоогийн чиг хандлага дээр давтан тооцоход гарах дундаж магадлал. Урьдчилсан таамаг биш, судалгааны давхарга.`,
    green: "Ногоорлын чиг", per_decade: "/10 жил",
    green_legend: (g) => `NDVI-ийн өөрчлөлт 10 жилд, 7–8 сар, ${g.from}–${g.through}`,
    green_classes: ["Буурсан (< 0)", "Бараг өөрчлөгдөөгүй (0–0.01)", "Бага зэрэг ногоорсон (0.01–0.02)", "Ногоорсон (0.02–0.04)", "Их ногоорсон (≥ 0.04)"],
    green_note: "Theil–Sen налуу (10-аас цөөн зун бол тооцоогүй). Цөлжилтийн албан ёсны зураг биш: NDVI нь хур тунадас, бэлчээрлэлт, ургамлын бүрхэвчийн өөрчлөлтийг ялгадаггүй.",
    layer_none: "Мэдээлэл байхгүй / мал бүртгэлгүй",
    model: "Сургасан загвар", model_rows: ["Spearman ρ (нэг өвлийг хассан)", "AUC (хорогдол ≥5%)"], fixed: "Тогтмол жин", learned: "Загвар",
    model_verdict: (better) => better
      ? "Нэг өвлийг хасаж бусдаар нь сургахад загвар тогтмол жинтэй онооноос илүү сайн эрэмбэлсэн."
      : "Нэг өвлийг хасаж бусдаар нь сургахад тогтмол жинтэй оноо загвараас илүү сайн эрэмбэлсэн: загвар нь газрын зургийн эрсдэлийг орлохгүй, зөвхөн эмзэг байдлын давхаргад ашиглагдана. Ridge-ийн торгуулийг (λ = 1) тааруулаагүй.",
    model_by_winter: "Өвөл бүрийн ρ: тогтмол жин ба загвар", weights: "Загварын жин (стандартчилсан)",
    feat: { z_cold: "Хүйтэн z", z_snow: "Цас z", z_summer: "Зуны бэлчээр z", z_density: "Цасны нягт z", z_pressure: "Ачаалал z",
      greenness_trend: "Ногоорлын чиг", herd_growth_5y: "Малын 5 жилийн өсөлт", past_mortality: "Өмнөх хорогдол" },
  },
  en: {
    title: "Dzud risk", subtitle: "Per soum: hindcasts of 15 winters, the 2026/27 outlook, vulnerability and the greenness trend", winter: "Winter",
    view: "Layer", views: { risk: "Dzud risk (chosen winter)", vuln: "Vulnerability (learned model)", green: "Greenness trend (desertification)" },
    search: "Find a soum", legend: "Legend", validation: "Against recorded losses",
    classes: ["Very low", "Low", "Medium", "High", "Very high"], none: "Not scored / insufficient data",
    ub: "Ulaanbaatar: no registered herd, so not scored", ub_density: " (Ulaanbaatar's density)",
    nodata: "Insufficient data",
    n: "Soums compared", rho_soum: "Spearman ρ, soum", excess: "Spearman ρ, excess mortality",
    rho_aimag: "Spearman ρ, aimag", top: "Top-20% risk soums in top-20% losses",
    mort: "Mortality (aimag totals, excl. Ulaanbaatar, sheep units)",
    aimag_only: "NSO has no soum-level losses for this winter, so it is compared by aimag only.",
    pooled: "Pooled test", pooled_rho: "Spearman ρ, pre-registered winters", pooled_ex: "Spearman ρ, excess",
    every: "Spearman ρ, all 14 winters (not pre-registered)",
    validation_note: "Scores compared with the next year's adult losses ÷ that year's census, in sheep units. Excess mortality = a soum's losses above its mean in the two normal winters. Weights were fixed before any comparison.",
    national: "Losses by winter (aimag totals, excl. Ulaanbaatar)",
    limits: "Limits",
    limits_text: "Four indicators: winter cold and snow depth (Copernicus ERA5-Land — model output, not observed), summer pasture (MODIS NDVI) and herd density, each against 2001–2020. 2009/10, 2013/14 and 2015/16 lie inside that baseline, so their z-scores are somewhat damped against winters from 2021 on. From v0.3 snow comes from ERA5-Land, chosen before any comparison because it is updated sooner. NASA GLDAS-2.1 is kept as a comparison only (docs/research/snow-comparison.md). Snow-cover days and snow density are shown, not scored, and are unvalidated. From v0.4 cold also comes from ERA5-Land rather than NASA POWER, which runs 5–6 weeks late. An aimag centre takes its aimag's herd density: the herds registered in the town graze the aimag. Ulaanbaatar's six districts with herds take the city's density the same way; the three with no registered herd are not scored: no herd, no dzud risk. The outlook uses a livestock census only once published (taken as 1 February of the next year). Hay reserves and herder preparedness are not in the data, yet they explain about half of the variation in losses (Nandintsetseg et al. 2018). The score is a weighted mean, so one extreme hazard (deep snow alone, say) is diluted when the others are normal. A research hindcast, not a warning.",
    sources: "Sources",
    sources_text: "Base map © OpenStreetMap contributors (ODbL); topographic: OpenTopoMap (CC-BY-SA), SRTM. Soum boundaries: OCHA COD-AB, NSO Mongolia (CC BY-IGO). Air temperature and snow: Copernicus ERA5-Land (C3S, CC BY); snow comparison: NASA GLDAS-2.1 Noah. Contains modified Copernicus Climate Change Service information (2026). NDVI: NASA MODIS MOD13C2. Livestock and losses: NSO Mongolia (1212.mn).",
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
    hist_caption: "Losses (bars, the largest marked above) and risk class (strip) by winter",
    vuln: "Vulnerability", vuln_unit: "chance of losing ≥5%",
    vuln_legend: "Chance of losing ≥5% of the herd, mean over 20 winters", vuln_classes: ["< 10%", "10–20%", "20–30%", "30–40%", "≥ 40%"],
    vuln_note: (m) => `The model learned from ${m.train.length} winters, ${m.train[0].replace("-", "/")}–${m.train[m.train.length - 1].replace("-", "/")}, which soum-winters lost 5% of the herd or more (ridge logistic regression). Vulnerability = the mean chance when the weather of the 20 winters ${m.replay[0].replace("-", "/")}–${m.replay[1].replace("-", "/")} is replayed on the ${m.census} herds and today's pasture trend. A research layer, not a forecast.`,
    green: "Greenness trend", per_decade: "/decade",
    green_legend: (g) => `Change in Jul–Aug NDVI per decade, ${g.from}–${g.through}`,
    green_classes: ["Browning (< 0)", "Little change (0–0.01)", "Slight greening (0.01–0.02)", "Greening (0.02–0.04)", "Strong greening (≥ 0.04)"],
    green_note: "Theil–Sen slope (no trend under 10 summers). Not the official desertification map: NDVI cannot tell rain from grazing or a change in what grows.",
    layer_none: "No data / no registered herd",
    model: "Learned model", model_rows: ["Spearman ρ (one winter held out)", "AUC (losses ≥5%)"], fixed: "Fixed weights", learned: "Model",
    model_verdict: (better) => better
      ? "Held out one winter at a time, the model ranked losses better than the fixed-weight score."
      : "Held out one winter at a time, the fixed-weight score ranked losses better than the model: the model does not replace the map's risk and is used only for the vulnerability layer. The ridge penalty (λ = 1) was not tuned.",
    model_by_winter: "ρ by winter: fixed weights and model", weights: "Model weights (standardised)",
    feat: { z_cold: "Cold z", z_snow: "Snow z", z_summer: "Summer pasture z", z_density: "Snow density z", z_pressure: "Pressure z",
      greenness_trend: "Greenness trend", herd_growth_5y: "Herd growth, 5 years", past_mortality: "Past losses" },
  },
};

let lang = "mn", layer = null, validation = null, pooled = null, winters = [], asof = null, outlook = null;
let level = "soum", view = "risk", shown = null, soumGeo = null, aimagGeo = null, aimagScores = {}, borders = null;
let model = null, greenness = null, hist = null, byName = {};
const isOutlook = () => shown === "outlook"; // the view on the map, not a choice whose data is still loading

const map = L.map("map", { minZoom: 4 }).setView([46.8, 103.5], 5);
const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | ' +
    'Map style &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
});
L.control.layers({ OpenStreetMap: osm, OpenTopoMap: topo }, null, { position: "topright" }).addTo(map);

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const fmt = (v, d = 2) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));
const bin = (v, cuts) => cuts.filter((c) => v >= c).length;
const sel = document.getElementById("winter");
const $ = (id) => document.getElementById(id);

function fillOf(p) {
  if (view === "vuln") { const v = model?.vulnerability[p.pcode]; return v == null ? GREY : VULN[bin(v, VULN_CUTS)]; }
  if (view === "green") { const v = greenness?.per_decade[p.pcode]; return v == null ? GREY : GREEN[bin(v, GREEN_CUTS)]; }
  return p.risk_class === null ? GREY : COLORS[p.risk_class];
}

function style(f) {
  return { color: "#555", weight: 0.4, fillOpacity: 0.78, fillColor: fillOf(f.properties) };
}

function aimagStyle(f) {
  const c = aimagScores[f.properties.pcode]?.risk_class ?? null;
  return { color: "#333", weight: 1, fillOpacity: 0.78, fillColor: c === null ? GREY : COLORS[c] };
}

function aimagName(p) {
  return lang === "mn" ? p.name_mn : p.name_en;
}

function soumName(p) {
  return lang === "mn" ? `${p.name_mn}, ${p.aimag_mn}` : `${p.name_en}, ${p.aimag_en}`;
}

// Mortality bars over a risk-class strip, one column per hindcast winter; the chosen winter is drawn dark.
function histChart(h) {
  if (!hist || !h) return "";
  const t = T[lang], n = hist.winters.length, W = 280, top = 12, mh = 46, bw = W / n, idx = hist.winters.indexOf(shown);
  const ms = h.mort.filter((v) => v != null), mx = Math.max(0.05, ...ms);
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} 92" width="${W}" role="img" aria-label="${esc(t.hist_caption)}">`;
  s += `<text x="0" y="9" font-size="9" fill="#5b6475">${Math.round(mx * 100)}%</text>`;
  s += `<line x1="0" x2="${W}" y1="${top + mh}" y2="${top + mh}" stroke="#d9dde5"/>`;
  hist.winters.forEach((w, i) => {
    const m = h.mort[i], r = h.risk[i], x = i * bw;
    if (m != null) {
      const bh = Math.max(1, (m / mx) * mh);
      s += `<rect x="${x + 1}" y="${top + mh - bh}" width="${bw - 2}" height="${bh}" fill="${i === idx ? "#1d2433" : "#8a93a6"}"><title>${esc(w.replace("-", "/"))}: ${fmt(m * 100, 1)}%</title></rect>`;
    }
    s += `<rect x="${x + 1}" y="${top + mh + 4}" width="${bw - 2}" height="10" fill="${r == null ? GREY : COLORS[bin(r, RISK_CUTS)]}"` +
      `${i === idx ? ' stroke="#1d2433" stroke-width="1.5"' : ""}><title>${esc(w.replace("-", "/"))}: ${r == null ? "–" : fmt(r, 3)}</title></rect>`;
    if (i % 2 === 0) s += `<text x="${x + bw / 2}" y="88" font-size="9" text-anchor="middle" fill="#5b6475">'${w.slice(2, 4)}</text>`;
  });
  return `${s}</svg><br><small>${esc(t.hist_caption)}</small>`;
}

// Horizontal bars: rows [{label, values, hi}] against series colours; values printed at the right.
function hbars(rows, colors, { d = 2, unit = "", aria = "" } = {}) {
  const W = 300, LW = 56, VW = 72, bh = 7, rh = colors.length * (bh + 1) + 5;
  const vals = rows.flatMap((r) => r.values.filter((v) => v != null));
  const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals) || 1;
  const x = (v) => LW + ((v - lo) / (hi - lo)) * (W - LW - VW);
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${rows.length * rh + 4}" width="100%" role="img" aria-label="${esc(aria)}">`;
  s += `<line x1="${x(0)}" x2="${x(0)}" y1="0" y2="${rows.length * rh + 2}" stroke="#9aa1ae"/>`;
  rows.forEach((r, i) => {
    const y = i * rh + 3, w = r.hi ? 700 : 400;
    s += `<text x="${LW - 4}" y="${y + rh / 2}" font-size="10" text-anchor="end" font-weight="${w}" fill="#1d2433">${esc(r.label)}</text>`;
    r.values.forEach((v, j) => {
      if (v == null) return;
      s += `<rect x="${Math.min(x(0), x(v))}" y="${y + j * (bh + 1)}" width="${Math.max(1, Math.abs(x(v) - x(0)))}" height="${bh}" fill="${colors[j]}"/>`;
    });
    s += `<text x="${W - VW + 4}" y="${y + rh / 2}" font-size="10" font-weight="${w}" fill="#1d2433">${esc(r.values.map((v) => fmt(v, d) + (v == null ? "" : unit)).join(" / "))}</text>`;
  });
  return `${s}</svg>`;
}

function extraLines(p) {
  const t = T[lang], v = model?.vulnerability[p.pcode], g = greenness?.per_decade[p.pcode];
  return `<br>${t.vuln}: <b>${v == null ? "–" : `${Math.round(v * 100)}%`}</b> <small>(${t.vuln_unit})</small>` +
    `<br>${t.green}: <b>${g == null ? "–" : (g >= 0 ? "+" : "") + fmt(g, 3)}</b> NDVI${t.per_decade}`;
}

function aimagPopup(p) {
  const t = T[lang], a = aimagScores[p.pcode];
  const chart = `<br>${histChart(hist?.aimag[p.pcode])}`;
  if (!a || a.risk_class === null) return `<b>${esc(aimagName(p))}</b><br>${t.nodata}${chart}`;
  const counts = a.counts.map((n, i) => `<i class="chip" style="background:${COLORS[i]}"></i>${esc(t.classes[i])}: ${esc(n)}`)
    .reverse().join("<br>");
  return `<b>${esc(aimagName(p))}</b><br>${t.risk}: <b>${t.classes[a.risk_class]}</b> (${fmt(a.risk, 4)})<br>
    <small>${t.aimag_risk}</small><br>${counts}<br><small>${esc(a.n)} ${t.soums_n}</small>${chart}`;
}

function popup(p) {
  const t = T[lang], chart = `<br>${histChart(hist?.soum[p.pcode])}`;
  if (p.risk_class === null) return `<b>${esc(soumName(p))}</b><br>${p.is_ub ? t.ub : t.nodata}${extraLines(p)}${chart}`;
  const unseen = (k) => p.stage === "oct" && (k === "cold" || k === "snow"); // pre-winter: no winter month yet
  const z = KEYS.map((k) => `${t.ind[k]} z: ${unseen(k) ? t.not_observed : fmt(p[`z_${k}`])}`).join("<br>");
  const missing = KEYS.filter((k) => p[`z_${k}`] === null && !unseen(k)).map((k) => t.ind[k]);
  return `<b>${esc(soumName(p))}</b><br>${t.risk}: <b>${t.classes[p.risk_class]}</b> (${fmt(p.risk, 4)})<br>${z}<br>
    <small>${t.cold_c}: ${fmt(p.cold_c, 1)} °C · ${t.snow_cm}: ${fmt(p.snow_m === null ? null : p.snow_m * 100, 0)} cm ·
    ${t.ndvi}: ${fmt(p.ndvi, 2)} · ${t.su}: ${fmt(p.su_per_km2, 0)}${p.is_centre ? t.centre : p.is_ub ? t.ub_density : ""}</small>
    <br><small>${t.snow_days}: ${fmt(p.snow_days, 0)} · ${t.density}: ${fmt(p.density_kgm3, 0)} ${t.unit_density} (z ${fmt(p.z_density)})
    <br><i>${t.proxy}</i></small>` +
    (missing.length ? `<br><i>${t.missing}: ${missing.join(", ")}</i>` : "") + extraLines(p) + chart;
}

function table(rows) {
  return rows.map(([k, x]) => `<tr><td>${esc(k)}</td><td>${esc(x)}</td></tr>`).join("");
}

function legendRows(colors, labels) {
  return labels.map((_, i) => `<div><i style="background:${colors[4 - i]}"></i>${esc(labels[4 - i])}</div>`).join("");
}

function renderLegend(t) {
  let html, note = "";
  if (view === "vuln" && model) {
    html = `<p class="note">${esc(t.vuln_legend)}</p>${legendRows(VULN, t.vuln_classes)}<div><i style="background:${GREY}"></i>${esc(t.layer_none)}</div>`;
    note = `${t.vuln_note(model)} ${t.model_verdict(model.pooled.rho_model > model.pooled.rho_fixed)}`;
  } else if (view === "green" && greenness) {
    html = `<p class="note">${esc(t.green_legend(greenness))}</p>${legendRows(GREEN, t.green_classes)}<div><i style="background:${GREY}"></i>${esc(t.nodata)}</div>`;
    note = t.green_note;
  } else {
    html = legendRows(COLORS, t.classes) + `<div><i style="background:${GREY}"></i>${esc(t.none)}</div>`;
  }
  $("legend").innerHTML = html;
  $("layer_note").textContent = note;
}

function renderModel(t) {
  if (!model) return;
  const p = model.pooled;
  $("model_table").innerHTML = `<tr><td></td><td>${esc(t.fixed)} / ${esc(t.learned)}</td></tr>` +
    table([[t.model_rows[0], `${fmt(p.rho_fixed, 3)} / ${fmt(p.rho_model, 3)}`], [t.model_rows[1], `${fmt(p.auc_fixed, 3)} / ${fmt(p.auc_model, 3)}`]]);
  $("model_note").textContent = t.model_verdict(p.rho_model > p.rho_fixed);
  $("model_chart").innerHTML = hbars(Object.entries(model.lowo).map(([w, v]) => ({ label: w.replace("-", "/"), values: [v.rho_fixed, v.rho_model], hi: w === shown })),
    ["#8a93a6", "#d95f02"], { aria: t.model_by_winter }) +
    `<div class="note"><i class="chip" style="background:#8a93a6"></i>${esc(t.fixed)} <i class="chip" style="background:#d95f02;margin-left:8px"></i>${esc(t.learned)}</div>`;
  $("weights").innerHTML = table(model.features.map((f) => [t.feat[f], fmt(model.weights[f], 2)]));
}

function render() {
  const t = T[lang];
  document.documentElement.lang = lang;
  $("lang").textContent = lang === "mn" ? "EN" : "МН";
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t[el.dataset.t]; });
  $("search").placeholder = t.search;
  $("search").setAttribute("aria-label", t.search);
  for (const o of $("view").options) o.textContent = t.views[o.value];
  renderLegend(t);
  const outlookOpt = sel.querySelector('option[value="outlook"]');
  if (outlook && outlookOpt) outlookOpt.textContent = `${outlook.winter.replace("-", "/")} — ${t.outlook_opt(t.months[outlook.stage])}`;
  $("banner").hidden = !isOutlook();
  $("banner").textContent = t.banner;
  $("validation_h").textContent = isOutlook() ? t.stage_validation : t.validation;
  if (asof) {
    $("stages").innerHTML = hbars(Object.entries(asof).map(([k, s]) => ({ label: t.months[k], values: [s.pooled.spearman],
      hi: isOutlook() && outlook && k === outlook.stage })), ["#3b6fd8"], { aria: t.stages });
  }
  if (isOutlook() && validation) {
    const rows = Object.entries(validation.winters).map(([w, v]) => [w.replace("-", "/"),
      v.spearman_soum === null ? `${fmt(v.spearman_aimag)}${t.aimag_suffix}` : `${fmt(v.spearman_soum)} (n=${v.n})`]);
    $("validation").innerHTML = table([...rows, [t.pooled_rho, `${fmt(validation.pooled.spearman)} (n=${validation.pooled.n})`]]);
    $("unit_note").textContent = t.stage_note;
  } else if (validation) {
    const v = validation;
    $("validation").innerHTML = table([
      [t.n, v.n], [t.rho_soum, fmt(v.spearman_soum)], [t.excess, fmt(v.excess_spearman_soum)],
      [t.rho_aimag, `${fmt(v.spearman_aimag)} (n=${v.n_aimag})`],
      [t.top, v.top_quintile_hit === null ? "–" : `${Math.round(v.top_quintile_hit * 100)}%`],
      [t.mort, `${fmt(v.mortality_pct, 1)}%`],
    ]);
    $("unit_note").textContent = v.validation_unit === "aimag" ? t.aimag_only : "";
  }
  if (pooled) {
    $("pooled").innerHTML = table([
      [t.pooled_rho, `${fmt(pooled.spearman)} (n=${pooled.n})`], [t.pooled_ex, `${fmt(pooled.spearman_excess)} (n=${pooled.n_excess})`],
      ...(pooled.every_winter ? [[t.every, `${fmt(pooled.every_winter.spearman)} (n=${pooled.every_winter.n})`]] : []),
    ]);
  }
  if (hist) {
    $("national_chart").innerHTML = hbars(hist.winters.map((w, i) => ({ label: w.replace("-", "/"), values: [hist.national_pct[i]], hi: w === shown })),
      ["#bd0026"], { d: 1, unit: "%", aria: t.national });
  }
  renderModel(t);
  for (const b of document.querySelectorAll("[data-level]")) {
    b.textContent = t[`level_${b.dataset.level}`];
    b.setAttribute("aria-pressed", String(b.dataset.level === level && view === "risk"));
    b.disabled = view !== "risk"; // vulnerability and greenness are per soum
  }
  $("level").setAttribute("aria-label", t.level);
  if (aimagGeo) {
    const rank = (pc) => aimagScores[pc]?.risk ?? -Infinity;
    $("aimags").innerHTML = aimagGeo.features.map((f) => f.properties)
      .sort((a, b) => rank(b.pcode) - rank(a.pcode))
      .map((p) => {
        const a = aimagScores[p.pcode], c = a?.risk_class ?? null;
        return `<tr><td><button type="button" class="link" data-aimag="${esc(p.pcode)}" title="${esc(t.zoom_to)}">` +
          `<i class="chip" style="background:${c === null ? GREY : COLORS[c]}"></i>${esc(aimagName(p))}</button></td>` +
          `<td>${c === null ? "–" : esc(t.classes[c])} ${a?.risk == null ? "" : fmt(a.risk)}</td></tr>`;
      }).join("");
  }
  if (soumGeo) {
    byName = {};
    $("soums").innerHTML = soumGeo.features.map((f) => soumName(f.properties)).sort()
      .map((n) => `<option value="${esc(n)}"></option>`).join("");
    for (const f of soumGeo.features) byName[soumName(f.properties)] = f.properties.pcode;
  }
  if (layer) {
    const aimagLevel = level === "aimag" && view === "risk";
    layer.eachLayer((l) => {
      const p = l.feature.properties;
      l.setPopupContent(aimagLevel ? aimagPopup(p) : popup(p));
      l.setTooltipContent(aimagLevel ? aimagName(p) : soumName(p));
    });
  }
}

function draw() {
  if (layer) map.removeLayer(layer);
  if (borders) map.removeLayer(borders);
  borders = null;
  const tip = { sticky: true, direction: "top", opacity: 0.9 };
  if (level === "aimag" && view === "risk") {
    layer = L.geoJSON(aimagGeo, { style: aimagStyle, onEachFeature: (f, l) => l.bindPopup(aimagPopup(f.properties), { maxWidth: 320 }).bindTooltip(aimagName(f.properties), tip) }).addTo(map);
  } else {
    layer = L.geoJSON(soumGeo, { style, onEachFeature: (f, l) => l.bindPopup(popup(f.properties), { maxWidth: 320 }).bindTooltip(soumName(f.properties), tip) }).addTo(map);
    borders = L.geoJSON(aimagGeo, { style: { color: "#222", weight: 1.6, fill: false }, interactive: false }).addTo(map);
  }
  render();
}

function zoomToAimag(pcode) {
  const f = aimagGeo.features.find((x) => x.properties.pcode === pcode);
  if (!f) return;
  map.fitBounds(L.geoJSON(f).getBounds());
  if (level === "aimag" && view === "risk" && layer) layer.eachLayer((l) => { if (l.feature.properties.pcode === pcode) l.openPopup(); });
}

function findSoum() {
  const pcode = byName[$("search").value];
  if (!pcode) return;
  if (level === "aimag" && view === "risk") { level = "soum"; draw(); }
  layer.eachLayer((l) => {
    if (l.feature.properties.pcode === pcode) { map.fitBounds(l.getBounds(), { maxZoom: 9 }); l.openPopup(); }
  });
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

$("lang").addEventListener("click", () => { lang = lang === "mn" ? "en" : "mn"; render(); });
for (const b of document.querySelectorAll("[data-level]")) {
  b.addEventListener("click", () => { if (level !== b.dataset.level) { level = b.dataset.level; if (soumGeo) draw(); else render(); } });
}
$("view").addEventListener("change", (e) => { view = e.target.value; if (soumGeo) draw(); else render(); });
$("search").addEventListener("change", findSoum);
$("aimags").addEventListener("click", (e) => { const b = e.target.closest("[data-aimag]"); if (b) zoomToAimag(b.dataset.aimag); });
sel.addEventListener("change", () => load(sel.value).catch(fail));

function fail(e) {
  $("validation").textContent = `Data failed to load: ${e}`;
  console.error(e);
}

const optional = (url) => fetch(url).then((r) => (r.ok ? r.json() : null)); // a missing extra layer leaves the risk map working

Promise.all([
  fetch("data/winters.json").then((r) => r.json()),
  fetch("data/pooled.json").then((r) => r.json()),
  fetch("data/asof_validation.json").then((r) => r.json()),
  optional("data/outlook.json"),
  fetch("data/aimags.geojson").then((r) => r.json()),
  optional("data/model.json"),
  optional("data/greenness.json"),
  optional("data/history.json"),
]).then(async ([w, p, a, o, g, m, gr, h]) => {
  aimagGeo = g;
  winters = w;
  pooled = p;
  asof = a;
  outlook = o;
  model = m;
  greenness = gr;
  hist = h;
  for (const opt of $("view").options) opt.disabled = (opt.value === "vuln" && !model) || (opt.value === "green" && !greenness);
  sel.innerHTML = (outlook ? '<option value="outlook"></option>' : "") +
    winters.map((x) => `<option value="${esc(x)}">${esc(x.replace("-", "/"))}</option>`).join("");
  sel.value = outlook ? "outlook" : winters[winters.length - 1];
  await load(sel.value);
  map.fitBounds(layer.getBounds());
}).catch(fail);
render();
