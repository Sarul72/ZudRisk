// Render docs/pitch/preview.html (served on :8770) to one PNG per slide and a PDF backup, through headless Edge.
// node docs/pitch/render.mjs  ->  docs/pitch/render/slide-N.png, docs/pitch/zudrisk-pitch.pdf
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const OUT = new URL("./render/", import.meta.url);
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const edge = spawn(EDGE, ["--headless=new", "--remote-debugging-port=9334", `--user-data-dir=${mkdtempSync(join(tmpdir(), "zr-"))}`,
  "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let list;
for (let i = 0; i < 50 && !list; i++) { await sleep(300); try { list = await (await fetch("http://127.0.0.1:9334/json/list")).json(); } catch {} }
const ws = new WebSocket(list.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (e) => (await cdp("Runtime.evaluate", { expression: e, returnByValue: true })).result?.result?.value;

await cdp("Emulation.setDeviceMetricsOverride", { width: 1400, height: 800, deviceScaleFactor: 1, mobile: false });
await cdp("Page.navigate", { url: "http://localhost:8770/preview.html" });
await sleep(3000);
const boxes = await js(`[...document.querySelectorAll("section")].map((s) => { const r = s.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; })`);
for (const [i, b] of boxes.entries()) {
  const res = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { ...b, scale: 1 } });
  writeFileSync(new URL(`slide-${i + 1}.png`, OUT), Buffer.from(res.result.data, "base64"));
}
const pdf = await cdp("Page.printToPDF", { preferCSSPageSize: true, printBackground: true });
writeFileSync(new URL("../zudrisk-pitch.pdf", OUT), Buffer.from(pdf.result.data, "base64"));
console.log(boxes.length, "slides rendered");
ws.close();
edge.kill();
process.exit(0);
