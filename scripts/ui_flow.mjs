// Drives the Launchpad UI in a real headless Chrome over the DevTools Protocol.
// Covers the plan's Day 2 UI acceptance: paste README -> autofill -> upload ->
// review -> publish, then a buyer purchase and download.
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Works on any Windows box with Chrome or Edge. Override with CHROME_PATH.
const CHROME =
  process.env.CHROME_PATH ||
  [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].find((candidate) => fs.existsSync(candidate));
if (!CHROME) {
  console.error("No Chrome or Edge found. Set CHROME_PATH to the browser executable.");
  process.exit(2);
}

const SHOTS = process.env.LAUNCHPAD_SHOTS || path.join(os.tmpdir(), "launchpad-checks");
fs.mkdirSync(SHOTS, { recursive: true });
const PROFILE = path.join(SHOTS, "cdp-profile");
const SITE = "http://localhost:3000";
const API = process.env.LAUNCHPAD_API || "http://127.0.0.1:8000";
const PORT = Number(process.env.CDP_PORT || 9223);

// The ZIP the seller uploads. day2_check.ps1 builds the same file; build it here
// if this script runs on its own.
const FIXTURE_ZIP = path.join(SHOTS, "day2_project.zip");
if (!fs.existsSync(FIXTURE_ZIP)) {
  const payload = path.join(SHOTS, "ui_flow_payload");
  fs.mkdirSync(payload, { recursive: true });
  fs.writeFileSync(
    path.join(payload, "README.md"),
    "# Flashcard Buddy\n\nRun: python main.py\n"
  );
  fs.writeFileSync(path.join(payload, "main.py"), "print('hello from the ZIP')\n");
  spawnSync("powershell", [
    "-NoProfile",
    "-Command",
    `Compress-Archive -Path '${payload}\\*' -DestinationPath '${FIXTURE_ZIP}' -Force`,
  ]);
  if (!fs.existsSync(FIXTURE_ZIP)) {
    console.error(`Could not build the fixture ZIP at ${FIXTURE_ZIP} (this needs PowerShell).`);
    process.exit(2);
  }
}

let ok = 0;
let fail = 0;
function check(name, condition, detail = "") {
  if (condition) {
    ok += 1;
    console.log(`PASS  ${name}  ${detail}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${name}  ${detail}`);
  }
}

const chrome = spawn(
  CHROME,
  [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${PROFILE}`,
    `--remote-debugging-port=${PORT}`,
    "--window-size=1280,1000",
    "about:blank",
  ],
  { stdio: "ignore" }
);

async function waitForDevtools() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) return await res.json();
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("chrome devtools did not start");
}

const version = await waitForDevtools();
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, { once: true });
  ws.addEventListener("error", reject, { once: true });
});

let nextId = 1;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
});

function rpc(method, params = {}, sessionId) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}

const { targetId } = await rpc("Target.createTarget", { url: "about:blank" });
const { sessionId } = await rpc("Target.attachToTarget", { targetId, flatten: true });
await rpc("Page.enable", {}, sessionId);
await rpc("Runtime.enable", {}, sessionId);
await rpc("DOM.enable", {}, sessionId);

async function evaluate(expression) {
  const result = await rpc(
    "Runtime.evaluate",
    { expression, awaitPromise: true, returnByValue: true },
    sessionId
  );
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description || "evaluate failed");
  }
  return result.result.value;
}

async function navigate(url) {
  await rpc("Page.navigate", { url }, sessionId);
  await waitFor("document.readyState === 'complete'");
}

// Poll an in-page condition. Returns true/false, never throws on timeout.
async function waitFor(condition, timeout = 120000) {
  const expression = `(async () => {
    const until = Date.now() + ${timeout};
    while (Date.now() < until) {
      try { if (${condition}) return true; } catch (e) {}
      await new Promise((r) => setTimeout(r, 300));
    }
    return false;
  })()`;
  return evaluate(expression);
}

async function shot(name) {
  const { data } = await rpc("Page.captureScreenshot", { format: "png" }, sessionId);
  fs.writeFileSync(path.join(SHOTS, `cdp_${name}.png`), Buffer.from(data, "base64"));
}

async function setField(selector, value) {
  return evaluate(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return "missing";
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return el.value.slice(0, 40);
  })()`);
}

async function clickButton(text) {
  return evaluate(`(() => {
    const wanted = ${JSON.stringify(text)}.toLowerCase();
    const el = [...document.querySelectorAll("button")].find((b) => b.textContent.trim().toLowerCase().includes(wanted));
    if (!el) return "missing";
    if (el.disabled) return "disabled";
    el.click();
    return "clicked";
  })()`);
}

// --- sign in the demo seller, then walk the whole listing flow ---------------

const login = await fetch(`${API}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "ananya@example.com", password: "launchpad123" }),
}).then((r) => r.json());
const seller = await fetch(`${API}/auth/me`, {
  headers: { Authorization: `Bearer ${login.access_token}` },
}).then((r) => r.json());

await navigate(`${SITE}/login`);
await evaluate(
  `localStorage.setItem("launchpad_token", ${JSON.stringify(login.access_token)}); localStorage.setItem("launchpad_user", ${JSON.stringify(JSON.stringify(seller))}); "done"`
);

await navigate(`${SITE}/sell/new`);
check("sell/new opens the form when signed in", await waitFor(`document.querySelector("textarea")`), "textarea present");
check("header shows the signed-in seller", await waitFor(`document.body.innerText.includes(${JSON.stringify(seller.name)})`), seller.name);

const readme = `# Flashcard Buddy

Turns a folder of markdown notes into flashcards. Python and FastAPI, SQLite for storage.

## Setup
1. pip install -r requirements.txt
2. uvicorn main:app --reload

## Licence
MIT
`;
await setField("textarea", readme);
check("README pasted into the form", (await evaluate(`document.querySelector("textarea").value.length`)) > 100, "chars>100");

check("autofill button clicked", (await clickButton("Fill from my README")) === "clicked", "clicked");
const filled = await waitFor(`document.querySelectorAll("input.input")[0] && document.querySelectorAll("input.input")[0].value.length > 3`, 180000);
check("A1 autofill filled the title field", filled, await evaluate(`document.querySelectorAll("input.input")[0]?.value || ""`));
check("autofill note tells the seller to check the fields", await waitFor(`document.body.innerText.includes("Read every field")`), "note shown");
await shot("sell_autofilled");

await setField(`input[type="number"]`, "259");
check("price typed in", (await evaluate(`document.querySelector('input[type="number"]').value`)) === "259", "259");
check("save draft clicked", (await clickButton("Save draft")) === "clicked", "clicked");
check("draft saved and the ZIP panel unlocks", await waitFor(`document.body.innerText.includes("ZIP only, up to 25 MB")`), "unlocked");

// upload the ZIP through the real file input
const { root } = await rpc("DOM.getDocument", {}, sessionId);
const { nodeId } = await rpc(
  "DOM.querySelector",
  { nodeId: root.nodeId, selector: `input[type="file"]` },
  sessionId
);
check("file input present after saving", nodeId > 0, `nodeId=${nodeId}`);
await rpc(
  "DOM.setFileInputFiles",
  { files: [FIXTURE_ZIP], nodeId },
  sessionId
);
check("ZIP attached in the UI", await waitFor(`document.body.innerText.includes("day2_project.zip uploaded")`, 60000), "upload note shown");

check("pre-review panel explains the check and that it gates nothing", await waitFor(`document.body.innerText.includes("does not decide whether you can publish")`), "found");

check("check quality clicked", (await clickButton("Check quality")) === "clicked", "clicked");
const scored = await waitFor(`document.querySelector(".stamp-score") && document.querySelector(".missing li")`, 180000);
check("A2 review panel shows a score and missing items", scored, await evaluate(`document.querySelector(".stamp-score")?.innerText || ""`));
check("review panel labels the score as run on this machine", await evaluate(`document.body.innerText.includes("ran on this machine")`), "found");
await shot("sell_reviewed");

check("publish clicked", (await clickButton("Publish")) === "clicked", "clicked");
check("listing published from the UI", await waitFor(`document.body.innerText.includes("Published. It is on the board now.")`), "ok note shown");
check("step strip marks all four steps done", (await evaluate(`document.querySelectorAll('.step[data-state="done"]').length`)) === 4, "4 done");
await shot("sell_published");

// --- the buyer side ---------------------------------------------------------

const listingId = await evaluate(`(() => {
  const link = [...document.querySelectorAll("a")].find((a) => a.href.includes("/projects/") && a.textContent.trim().length > 3);
  return link ? link.getAttribute("href") : "";
})()`);
check("published listing links to its page", listingId.startsWith("/projects/"), listingId);

await navigate(`${SITE}${listingId}`);
check("detail page renders for a buyer", await waitFor(`document.body.innerText.includes("What you get")`), "loaded");
check("buyer sees the sign-in gate while signed in as the seller", await waitFor(`document.body.innerText.includes("You are the seller")`), "seller view");
check("seller sees a download button for their own ZIP", await waitFor(`[...document.querySelectorAll("button")].some((b) => b.textContent.includes("Download ZIP"))`), "found");
await shot("detail_seller");

// sign the buyer in and buy through the UI
const buyerEmail = `ui.buyer.${Date.now()}@example.com`;
const buyer = await fetch(`${API}/auth/register`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: buyerEmail, name: "UI Buyer", password: "launchpad123" }),
}).then((r) => r.json());
const buyerUser = await fetch(`${API}/auth/me`, {
  headers: { Authorization: `Bearer ${buyer.access_token}` },
}).then((r) => r.json());

await evaluate(
  `localStorage.setItem("launchpad_token", ${JSON.stringify(buyer.access_token)}); localStorage.setItem("launchpad_user", ${JSON.stringify(JSON.stringify(buyerUser))}); "done"`
);
await navigate(`${SITE}${listingId}`);
check("buyer sees the buy button", await waitFor(`[...document.querySelectorAll("button")].some((b) => b.textContent.includes("Buy for"))`), "found");

check("ask box question typed", (await setField(`.ask input.input`, "How do I run it?")) !== "missing", "typed");
check("ask clicked", (await clickButton("Ask")) === "clicked", "clicked");
const answered = await waitFor(`document.querySelector(".grounded-note")`, 180000);
check("A3 answer appears with a grounding note", answered, await evaluate(`document.querySelector(".grounded-note")?.innerText || ""`));
check("grounded answer is marked as in the listing", await evaluate(`document.querySelector(".grounded-note")?.dataset.grounded === "true"`), "grounded=true");
await shot("detail_ask");

check("buy clicked", (await clickButton("Buy for")) === "clicked", "clicked");
check("test checkout reports success", await waitFor(`document.body.innerText.includes("Paid in test mode")`, 60000), "paid");
check("download button replaces the buy button", await waitFor(`[...document.querySelectorAll("button")].some((b) => b.textContent.includes("Download ZIP"))`), "found");
await shot("detail_bought");

await navigate(`${SITE}/dashboard`);
check("dashboard lists the buyer's purchase as paid", await waitFor(`document.body.innerText.includes("My purchases") && document.body.innerText.includes("paid")`, 60000), "paid row");
await shot("dashboard_buyer");

// back to the seller: their own dashboard must show the listing
await evaluate(
  `localStorage.setItem("launchpad_token", ${JSON.stringify(login.access_token)}); localStorage.setItem("launchpad_user", ${JSON.stringify(JSON.stringify(seller))}); "done"`
);
await navigate(`${SITE}/dashboard`);
check("seller dashboard lists the published listing with its score", await waitFor(`document.body.innerText.includes("My listings") && document.body.innerText.includes("Published") && document.body.innerText.includes("/100")`, 60000), "listing row");
await shot("dashboard_seller");

await navigate(`${SITE}/`);
check(
  "board shows the new listing with its stamp and price",
  await waitFor(`document.body.innerText.includes("₹259") && document.querySelectorAll(".stamp").length > 0`, 60000),
  "visible"
);
await shot("board_after");

console.log(`\nRESULT: ${ok} passed, ${fail} failed`);
ws.close();
chrome.kill();
process.exit(fail === 0 ? 0 : 1);
