// Screenshots of the live Mongolia Hazard Watch site for the pitch deck, through headless Edge and the Chrome DevTools Protocol.
// node docs/pitch/shots_hazard.mjs  ->  docs/pitch/img/*.png
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const SITE = "https://sigma0sanaa.github.io/hazard/";
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
const click = (re) => `[...document.querySelectorAll("button")].find((b) => ${re}.test(b.innerText.trim()))?.click()`;
await js(click("/^EN$/"));
await sleep(1500);
async function shot(name, setup, wait = 9000) {
  await js(setup);
  await sleep(wait);
  const res = await cdp("Page.captureScreenshot", { format: "png" });
  writeFileSync(new URL(`${name}.png`, OUT), Buffer.from(res.result.data, "base64"));
  console.log(name);
}
await shot("hz_combined", click("/^Combined$/"));
await shot("hz_flood", click("/^Flood$/"));
await shot("hz_fire", click("/^Wildfire$/"));
ws.close();
edge.kill();
process.exit(0);
