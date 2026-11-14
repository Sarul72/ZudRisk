// Screenshots of the live ZudRisk site for the pitch deck, through headless Edge and the Chrome DevTools Protocol.
// node docs/pitch/shots.mjs  ->  docs/pitch/img/*.png
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const SITE = "https://sarul72.github.io/ZudRisk/";
const OUT = new URL("./img/", import.meta.url);
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const edge = spawn(EDGE, ["--headless=new", "--remote-debugging-port=9333", `--user-data-dir=${mkdtempSync(join(tmpdir(), "zr-"))}`,
  "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let list;
for (let i = 0; i < 50 && !list; i++) { await sleep(300); try { list = await (await fetch("http://127.0.0.1:9333/json/list")).json(); } catch {} }
const page = list.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (expr) => (await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;

await cdp("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1000, deviceScaleFactor: 1.5, mobile: false });
await cdp("Page.enable");
await cdp("Page.navigate", { url: SITE });
await sleep(9000);
await js(`document.getElementById("lang").click()`); // English: the pitch is in English
await sleep(800);

async function shot(name, setup, what = "map") {
  await js(`(async () => { const s = (ms) => new Promise((r) => setTimeout(r, ms)); ${setup}; await s(4500); })()`);
  const box = await js(`(() => { const r = document.${what === "map" ? 'getElementById("map")' : "body"}.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; })()`);
  const res = await cdp("Page.captureScreenshot", { format: "png", clip: { ...box, scale: 1 } });
  writeFileSync(new URL(`${name}.png`, OUT), Buffer.from(res.result.data, "base64"));
  console.log(name, Math.round(box.width), "x", Math.round(box.height));
}
const winter = (w) => `const w = document.getElementById("winter"); w.value = "${w}"; w.dispatchEvent(new Event("change"))`;
const viewSel = (v) => `const v = document.getElementById("view"); v.value = "${v}"; v.dispatchEvent(new Event("change"))`;
const fit = `map.closePopup(); map.fitBounds([[41.5, 87.7], [52.2, 119.9]])`;

await shot("outlook", `${fit}`);
await shot("outlook_page", `${fit}`, "page");
await shot("dzud2010", `${winter("2009-10")}; await s(3500); ${fit}`);
await shot("dzud2010_page", `${fit}`, "page");
await shot("greenness", `${viewSel("green")}; await s(2500); ${fit}`);
await shot("popup2010", `${viewSel("risk")}; await s(2500); ${fit}; await s(1500);
  let hit = null, best = -1; layer.eachLayer((l) => { const p = l.feature.properties; if (p.risk != null && p.risk > best) { best = p.risk; hit = l; } });
  hit.openPopup()`);
ws.close();
edge.kill();
process.exit(0);
