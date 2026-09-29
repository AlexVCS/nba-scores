// Mockups for #189 "Ask" natural-language search. Overlays static HTML on the live design-1 pages.
// Needs the dev servers running (pnpm dev + uvicorn). Data below is real 2025-26 data from the local API.
// Behaviour follows docs/ask-search.md. Patterns borrowed from Mobbin examples are noted per scene.
// Setup and limitations: see README.md in this folder.
import {createRequire} from "node:module";
import {fileURLToPath} from "node:url";
import path from "node:path";

// playwright-core is not an app dependency. Install it anywhere and point ASK_MOCKUP_TOOLS at that folder
// (see README.md), or install it where Node can resolve it from this file.
const tools = process.env.ASK_MOCKUP_TOOLS;
const require = createRequire(tools ? path.join(path.resolve(tools), "noop.js") : import.meta.url);
const {chromium} = require("playwright-core");

const OUT = process.env.ASK_MOCKUP_OUT ?? path.dirname(fileURLToPath(import.meta.url));
const BASE_URL = process.env.ASK_MOCKUP_BASE_URL ?? "http://localhost:5173";
// Defaults to the Chromium that `npx playwright-core install chromium` downloads; override for a local Chrome.
const b = await chromium.launch(process.env.ASK_MOCKUP_CHROMIUM ? {executablePath: process.env.ASK_MOCKUP_CHROMIUM} : {});

const I = {
  search: `<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>`,
  eye: `<path d="M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0"/><circle cx="12" cy="12" r="3"/>`,
  eyeOff: `<path d="M10.73 5.08a10.74 10.74 0 0 1 11.2 6.57 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-1.44 2.49"/><path d="M14.08 14.16a3 3 0 0 1-4.24-4.24"/><path d="M17.48 17.5a10.75 10.75 0 0 1-15.42-5.15 1 1 0 0 1 0-.7 10.75 10.75 0 0 1 4.45-5.14"/><path d="m2 2 20 20"/>`,
  arrow: `<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>`,
  enter: `<polyline points="9 10 4 15 9 20"/><path d="M20 4v7a4 4 0 0 1-4 4H4"/>`,
  help: `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>`,
  xc: `<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>`,
  clock: `<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>`,
  shield: `<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>`,
  trophy: `<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>`,
  cal: `<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>`,
};
const ic = (k, s = 16, extra = "") => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex:none;${extra}">${I[k]}</svg>`;

const CSS = `
  .ak *{box-sizing:border-box}
  .ak{font-family:Poppins,sans-serif;color:var(--hw-ink)}
  .ak-cap{font:800 10px/1 Poppins;letter-spacing:.12em;text-transform:uppercase;color:var(--hw-muted)}
  .ak-ov{position:fixed;inset:0;z-index:100;background:rgb(10 8 4 / 58%);backdrop-filter:blur(2px);display:flex;justify-content:center;align-items:flex-start;padding-top:64px}
  .ak-pal{width:min(760px,92vw);background:var(--hw-surface);border-radius:14px;box-shadow:var(--hw-shadow-card-hover);overflow:hidden}
  .ak.mob .ak-ov{padding:0;align-items:stretch}
  .ak.mob .ak-pal{width:100%;border-radius:0;display:flex;flex-direction:column}
  .ak-in{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:4px solid var(--hw-accent)}
  .ak.mob .ak-in{padding:12px 14px 10px;gap:12px}
  .ak-field{flex:1;min-width:0;display:flex;align-items:center;gap:8px;min-height:40px;padding:0 10px;border-radius:10px;background:var(--hw-surface-muted);border:1px solid var(--hw-line)}
  .ak-q{flex:1;min-width:0;font:600 17px/1.3 Poppins;color:var(--hw-ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .ak.mob .ak-q{font-size:15px}
  .ak-q.ph{color:var(--hw-muted);font-weight:500}
  .ak-caret{display:inline-block;width:2px;height:1.1em;background:var(--hw-accent-ink);vertical-align:-3px;margin-left:1px}
  .ak-cancel{font:700 14px Poppins;color:var(--hw-accent-ink)}
  .ak-kbd{display:inline-flex;align-items:center;font:700 10px/1 Poppins;letter-spacing:.06em;padding:5px 7px;border-radius:6px;border:1px solid var(--hw-line);color:var(--hw-muted);background:var(--hw-surface-muted);text-transform:uppercase}
  .ak-badge{display:inline-flex;align-items:center;min-height:22px;padding:0 9px;border-radius:999px;background:var(--hw-accent);color:var(--hw-accent-contrast);font:800 9px/1 Poppins;letter-spacing:.12em;text-transform:uppercase}
  .ak-sc{display:inline-flex;align-items:center;gap:6px;min-height:30px;padding:0 12px;border-radius:999px;border:1px solid var(--hw-line);font:700 12px/1 Poppins;color:var(--hw-muted);white-space:nowrap}
  .ak-body{padding:18px 20px 20px}
  .ak.mob .ak-body{padding:14px 14px 18px;flex:1;overflow:hidden}
  .ak-foot{display:flex;align-items:center;gap:14px;padding:11px 20px;border-top:1px solid var(--hw-line);background:var(--hw-surface-muted);font:500 11px/1.4 Poppins;color:var(--hw-muted)}
  .ak.mob .ak-foot{padding:12px 14px;flex-wrap:wrap;row-gap:8px}
  .ak-read{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-bottom:16px}
  .ak-tok{display:inline-flex;align-items:center;gap:7px;min-height:30px;padding:0 10px;border-radius:8px;border:1px solid var(--hw-line);background:var(--hw-surface-muted);font:700 12px/1 Poppins;color:var(--hw-ink);white-space:nowrap}
  .ak-tok i{font:800 9px/1 Poppins;font-style:normal;letter-spacing:.12em;text-transform:uppercase;color:var(--hw-muted)}
  .ak-tok small{font:500 11px/1 Poppins;color:var(--hw-muted)}
  .ak-tok.warn{border-color:var(--hw-accent);border-style:dashed;background:transparent}
  .ak-tok.warn i{color:var(--hw-accent-ink)}
  .ak-edit{font:700 11px/1 Poppins;color:var(--hw-accent-ink);text-decoration:underline;text-underline-offset:3px;margin-left:4px}
  .ak-card{border:1px solid var(--hw-line);border-radius:12px;background:var(--hw-surface);overflow:hidden}
  .ak-card + .ak-card{margin-top:12px}
  .ak-row{display:flex;align-items:center;gap:12px;padding:12px 14px;border-top:1px solid var(--hw-line)}
  .ak-row:first-child{border-top:0}
  .ak-red{display:inline-block;height:.9em;border-radius:4px;vertical-align:-1px;background:repeating-linear-gradient(-45deg,var(--hw-line) 0 4px,var(--hw-surface-muted) 4px 8px);border:1px solid var(--hw-line)}
  .ak-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:36px;padding:0 13px;border-radius:9px;border:1px solid var(--hw-line);background:var(--hw-surface);color:var(--hw-ink);font:800 10px/1 Poppins;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap}
  .ak-btn.pri{background:var(--hw-accent);border-color:var(--hw-accent);color:var(--hw-accent-contrast)}
  .ak-btn.ink{background:#131313;border-color:#131313;color:#fff}
  .ak-btn.ink svg{color:var(--hw-accent)}
  .ak-btn.sm{min-height:30px;padding:0 10px;font-size:9px}
  .ak-tri{display:inline-grid;place-items:center;min-width:42px;height:26px;padding:0 6px;border-radius:6px;background:var(--hw-surface-muted);border:1px solid var(--hw-line);font:800 11px/1 Poppins;letter-spacing:.04em;color:var(--hw-ink)}
  .ak-sug{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:9px;font:600 14px/1.3 Poppins;color:var(--hw-ink)}
  .ak-sug.on{background:var(--hw-surface-muted);box-shadow:inset 3px 0 0 var(--hw-accent)}
  .ak-sug .ak-cap{width:92px;flex:none}
  .ak-sug .meta{font:500 12px Poppins;color:var(--hw-muted);white-space:nowrap}
  .ak-grp{margin:14px 12px 6px}
  .ak-grp:first-child{margin-top:2px}
  .ak-note{display:flex;gap:8px;align-items:flex-start;font:500 11px/1.45 Poppins;color:var(--hw-muted)}
  .ak-cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .ak-cards article{zoom:.6;animation:none!important;opacity:1!important;transform:none!important}
  .ak-cards figure{visibility:hidden}
  .ak-next{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
  .ak-next span{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 12px;border-radius:999px;border:1px solid var(--hw-line);font:600 12px Poppins;color:var(--hw-ink);background:var(--hw-surface)}
  .ak-kb{background:#d1d3d9;padding:8px 3px 30px;display:grid;gap:11px}
  .ak-kb div{display:flex;justify-content:center;gap:6px}
  .ak-kb b{flex:0 0 32px;height:42px;border-radius:5px;background:#fff;box-shadow:0 1px 0 #898a8d;display:grid;place-items:center;font:400 21px -apple-system,system-ui;color:#000}
  .ak-kb b.w{flex:0 0 44px;background:#abafb9;font-size:15px}
  .ak-kb b.sp{flex:1 1 auto;max-width:190px;font-size:15px}
  .ak-kb b.go{flex:0 0 88px;background:#0a84ff;color:#fff;font-size:15px}
`;

async function open(vp, {dark = false, path = "/design-1/?date=2026-02-05"} = {}) {
  const ctx = await b.newContext({viewport: vp, deviceScaleFactor: 2});
  const p = await ctx.newPage();
  await p.goto(BASE_URL + path);
  await p.waitForTimeout(2500);
  const got = p.getByRole("button", {name: "Got it"}); if (await got.count()) await got.first().click();
  if (dark) { await p.getByRole("button", {name: "Switch to dark mode"}).first().click(); await p.waitForTimeout(600); }
  await p.addStyleTag({content: CSS});
  // Hide the design switcher pill and the floating view counter so they don't sit over the overlay.
  await p.evaluate(() => {
    document.querySelectorAll("body *").forEach(e => { const s = getComputedStyle(e); if (s.position === "fixed" && !e.closest(".ak")) e.style.display = "none"; });
  });
  return p;
}

// Adds the "Ask" entry point to the header preference bar.
async function entry(p, mob) {
  await p.evaluate(({mob, search}) => {
    const bar = document.querySelector("header > div");
    bar.style.justifyContent = "space-between";
    const el = document.createElement("div");
    el.className = "ak";
    el.innerHTML = mob
      ? `<span class="ak-btn" style="min-height:44px;gap:8px;font-size:11px;box-shadow:var(--hw-shadow-small)">${search} Ask</span>`
      : `<div style="display:flex;align-items:center;gap:10px;width:380px;min-height:44px;padding:0 8px 0 14px;border-radius:10px;border:1px solid var(--hw-line);background:var(--hw-surface);box-shadow:var(--hw-shadow-small);color:var(--hw-muted);font:500 13px Poppins">${search}<span style="flex:1">Ask about a game, stat, or series</span><span class="ak-kbd">⌘ K</span></div>`;
    bar.prepend(el);
  }, {mob, search: ic("search", 16)});
}

const KB = `<div class="ak-kb">${["qwertyuiop", "asdfghjkl"].map(r => `<div>${[...r].map(k => `<b>${k}</b>`).join("")}</div>`).join("")}
  <div><b class="w">⇧</b>${[..."zxcvbnm"].map(k => `<b>${k}</b>`).join("")}<b class="w">⌫</b></div>
  <div><b class="w">123</b><b class="sp">space</b><b class="go">search</b></div></div>`;

async function palette(p, {mob = false, query, placeholder = false, body, foot, keyboard = false}) {
  await p.evaluate(({mob, query, placeholder, body, foot, keyboard, KB, searchIc, xcIc}) => {
    const src = getComputedStyle(document.querySelector("header"));
    const wrap = document.createElement("div");
    wrap.className = "ak" + (mob ? " mob" : "");
    for (const k of ["--hw-page","--hw-surface","--hw-surface-muted","--hw-ink","--hw-muted","--hw-accent","--hw-accent-ink","--hw-accent-contrast","--hw-line","--hw-shadow-card","--hw-shadow-small","--hw-shadow-card-hover"]) wrap.style.setProperty(k, src.getPropertyValue(k));
    const q = `<div class="ak-q ${placeholder ? "ph" : ""}">${query}${placeholder ? "" : `<span class="ak-caret"></span>`}</div>`;
    // Mobile uses the iOS search pattern (field with clear button + Cancel), desktop a command palette row.
    const input = mob
      ? `<div class="ak-in"><div class="ak-field"><span style="color:var(--hw-muted)">${searchIc}</span>${q}${placeholder ? "" : `<span style="color:var(--hw-muted)">${xcIc}</span>`}</div><span class="ak-cancel">Cancel</span></div>`
      : `<div class="ak-in"><span style="color:var(--hw-accent-ink)">${searchIc}</span>${q}<span class="ak-kbd">esc</span></div>`;
    wrap.innerHTML = `<div class="ak-ov"><div class="ak-pal">${input}
      <div class="ak-body">${body}</div>
      ${foot ? `<div class="ak-foot">${foot}</div>` : ""}${keyboard ? KB : ""}</div></div>`;
    document.body.appendChild(wrap);
  }, {mob, query, placeholder, body, foot, keyboard, KB, searchIc: ic("search", mob ? 17 : 20), xcIc: ic("xc", 17)});
  await p.waitForTimeout(250);
}

const red = (w) => `<span class="ak-red" style="width:${w}px"></span>`;
const reveal = (label = "Reveal", sm = true) => `<span class="ak-btn ink ${sm ? "sm" : ""}">${ic("eye", 13)} ${label}</span>`;
const tok = (label, value, sub = "", cls = "") => `<span class="ak-tok ${cls}"><i>${label}</i>${value}${sub ? ` <small>${sub}</small>` : ""}</span>`;
// The detected request type is a badge on the interpretation, not a filter the user sets.
const readAs = (type, toks, mob) => `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span class="ak-cap">Reading this as</span><span class="ak-badge">${type}</span></div><div class="ak-read">${toks.join("")}${mob ? "" : `<span class="ak-edit">Not right? Rephrase</span>`}</div>`;
const hidden = `<span style="display:flex;align-items:center;gap:6px;white-space:nowrap">${ic("eyeOff", 13)} Results stay hidden until you reveal them</span>`;
// AI disclosure (Gemini / Spotify). The model only reads the question; Python computes the answer.
const answerFoot = (mob) => `<span style="display:flex;align-items:center;gap:6px">${ic("shield", 13)} ${mob ? "AI reads your question · numbers from NBA.com" : "AI reads your question. Numbers come straight from NBA.com."}</span>`;
const keys = (...pairs) => `<span style="display:flex;align-items:center;gap:6px;white-space:nowrap">${pairs.map(([k, l], i) => `<span class="ak-kbd" ${i ? `style="margin-left:8px"` : ""}>${k}</span> ${l}`).join(" ")}</span>`;
const sug = (cap, q, {on = false, meta = "", icon = ""} = {}) => `<div class="ak-sug ${on ? "on" : ""}">${icon ? `<span style="color:var(--hw-muted);display:flex">${icon}</span>` : `<span class="ak-cap">${cap}</span>`}<span style="flex:1">${q}</span>${meta ? `<span class="meta">${meta}</span>` : ""}${on ? `<span class="ak-kbd">${ic("enter", 11)}</span>` : ""}</div>`;
// Every example is a complete question that passes validation on its own (explicit year, supported request type).
const EX = {
  stats: "How many points did James Harden score on March 9, 2026?",
  series: "Did the Pistons beat the Magic in the 2026 first round?",
  post: "How did the Knicks do in the 2026 playoffs?",
};

// 01a / 01b. Entry points in the header
{
  const p = await open({width: 1440, height: 1000});
  await entry(p, false);
  await p.screenshot({path: `${OUT}/01a-desktop-header-entry.png`, clip: {x: 100, y: 0, width: 1240, height: 260}});
  await p.context().close();
  const m = await open({width: 390, height: 844});
  await entry(m, true);
  await m.screenshot({path: `${OUT}/01b-mobile-header-entry.png`, clip: {x: 0, y: 0, width: 390, height: 240}});
  await m.context().close();
}

// 01. Desktop empty state: recent questions (Basecamp), examples, key hints (Front)
{
  const p = await open({width: 1440, height: 1000});
  await entry(p, false);
  await palette(p, {query: "Ask about a game, stat, or series", placeholder: true,
    body: `<div class="ak-cap ak-grp">Recent</div>
      ${sug("", "Knicks games last week", {on: true, icon: ic("clock", 15), meta: "Asked Mon"})}
      ${sug("", "Who won the 2026 NBA Finals?", {icon: ic("clock", 15), meta: "Asked Sep 12"})}
      <div class="ak-cap ak-grp">Try asking</div>
      ${sug("Stats", EX.stats)}
      ${sug("Series", EX.series)}
      ${sug("Postseason", EX.post)}
      <div style="margin:14px 12px 0;padding-top:14px;border-top:1px solid var(--hw-line)" class="ak-note">${ic("help", 14, "margin-top:1px")}<span>Ask about games on a date or within a week, one player’s stats in one game, or a playoff series. Include the year. Career totals and all-time comparisons aren’t supported.</span></div>`,
    foot: `${hidden}<span style="flex:1"></span>${keys(["↑↓", "navigate"], [ic("enter", 10), "ask"], ["esc", "close"])}`});
  await p.screenshot({path: `${OUT}/01-desktop-ask-empty.png`});
  await p.context().close();
}

// 01c. Desktop typeahead for a short name. Direct matches come first and the top one is selected, so Enter opens a
// page without a model call. Question-shaped input would select the Ask row instead.
// Spoiler rule: only first-round series are offered, because later-round rows reveal how far a team advanced.
// (Notion "Search all sources with AI" row + grouped result sections)
{
  const p = await open({width: 1440, height: 1000});
  await entry(p, false);
  const box = (icon, accent) => `<span style="display:grid;place-items:center;width:26px;height:26px;border-radius:7px;${accent ? "background:var(--hw-accent);color:var(--hw-accent-contrast)" : "background:var(--hw-surface-muted);border:1px solid var(--hw-line);color:var(--hw-ink)"}">${icon}</span>`;
  const go = (icon, title, sub, kind, on) => `<div class="ak-sug ${on ? "on" : ""}">${box(icon)}<span style="flex:1">${title} <span style="font:500 12px Poppins;color:var(--hw-muted)">${sub}</span></span><span class="meta">${kind}</span>${on ? `<span class="ak-kbd">${ic("enter", 11)}</span>` : ""}</div>`;
  const ask = (q) => `<div class="ak-sug">${box(ic("search", 13), true)}<span style="flex:1"><span style="color:var(--hw-muted);font-weight:500">Ask </span>“${q}”</span></div>`;
  await palette(p, {query: "knicks",
    body: `<div class="ak-cap ak-grp">Games</div>
      ${go(ic("cal", 14), "NYK @ BOS", "Sun, Feb 8, 2026", "Boxscore", true)}
      ${go(ic("cal", 14), "NYK @ DET", "Fri, Feb 6, 2026", "Boxscore")}
      <div class="ak-cap ak-grp">Playoff series</div>
      ${go(ic("trophy", 14), "2026 East First Round", "NYK vs ATL", "Series")}
      <div class="ak-cap ak-grp">Ask</div>
      ${ask("Knicks games last week")}${ask("How did the Knicks do in the 2026 playoffs?")}`,
    foot: `<span style="display:flex;align-items:center;gap:6px">${ic("help", 13)} Games and series open directly. Ask rows answer a question.</span><span style="flex:1"></span>${keys(["↑↓", "navigate"], [ic("enter", 10), "open"])}`});
  await p.screenshot({path: `${OUT}/01c-desktop-typeahead.png`});
  await p.context().close();
}

// 02. Desktop: single-stat answer. Only the asked stat is shown (after its reveal); the final score has its own reveal.
{
  const p = await open({width: 1440, height: 1000});
  await entry(p, false);
  await palette(p, {query: "how many points did harden score on march 9 2026",
    body: readAs("Player stat", [tok("Player", "James Harden", "CLE"), tok("Game", "PHI @ CLE", "Mon, Mar 9, 2026"), tok("Stat", "Points")]) + `
      <div class="ak-card">
        <div style="padding:18px 18px 16px;display:flex;align-items:flex-end;justify-content:space-between;gap:16px">
          <div><div class="ak-cap" style="margin-bottom:10px">James Harden · PHI @ CLE</div>
            <div style="display:flex;align-items:baseline;gap:12px"><span style="font:800 56px/0.9 Poppins;letter-spacing:-.02em">21</span><span style="font:700 17px Poppins;color:var(--hw-muted)">points</span></div></div>
          <span class="ak-edit" style="display:flex;align-items:center;gap:5px;text-decoration:none;color:var(--hw-muted)">${ic("eyeOff", 13)} Hide</span>
        </div>
        <div class="ak-row" style="background:var(--hw-surface-muted)">
          <span class="ak-cap" style="width:92px">Final score</span>
          <span class="ak-tri">PHI</span>${red(34)}<span style="color:var(--hw-muted)">–</span>${red(34)}<span class="ak-tri">CLE</span>
          <span style="flex:1"></span>${reveal("Reveal score")}</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:14px"><span class="ak-btn pri">Open boxscore ${ic("arrow", 13)}</span><span class="ak-btn">Game details</span></div>
      <div class="ak-cap" style="margin-top:18px">Ask next</div>
      <div class="ak-next"><span>${ic("search", 12)} How many assists did James Harden have on March 9, 2026?</span><span>${ic("search", 12)} Cavaliers games from March 9 to March 15, 2026</span></div>`,
    foot: answerFoot()});
  await p.screenshot({path: `${OUT}/02-desktop-stat-answer.png`});
  await p.context().close();
}

// 03. Desktop: game search with a relative date resolved to the previous calendar week (asked Wed, Feb 11).
// Results reuse the scores page's game card, cloned from the page behind the overlay.
{
  const p = await open({width: 1440, height: 1000});
  await entry(p, false);
  await palette(p, {query: "knicks games last week",
    body: readAs("Games", [tok("Team", "New York Knicks"), tok("Dates", "Last week", "Mon, Feb 2 – Sun, Feb 8, 2026 · ET")]) + `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <span style="font:800 15px Poppins">4 games</span>${reveal("Reveal all 4 scores", false)}</div>
      <div class="ak-cards"></div>`,
    foot: answerFoot()});
  await p.evaluate(() => {
    const games = [["Tue, Feb 3", "NYK", "Knicks", "WAS", "Wizards"], ["Wed, Feb 4", "DEN", "Nuggets", "NYK", "Knicks"], ["Fri, Feb 6", "NYK", "Knicks", "DET", "Pistons"], ["Sun, Feb 8", "NYK", "Knicks", "BOS", "Celtics"]];
    const src = document.querySelector("main article") || document.querySelector("article");
    const grid = document.querySelector(".ak-cards");
    for (const [date, a, an, h, hn] of games) {
      const cell = document.createElement("div");
      cell.innerHTML = `<div class="ak-cap" style="margin:0 2px 6px;color:var(--hw-ink)">${date}</div>`;
      const card = src.cloneNode(true);
      const sides = card.querySelectorAll("strong.block");
      const names = [...card.querySelectorAll("strong.block + small")];
      sides[0].textContent = a; sides[1].textContent = h; names[0].textContent = an; names[1].textContent = hn;
      card.querySelector("footer a:last-child")?.remove();
      cell.appendChild(card);
      grid.appendChild(cell);
    }
  });
  await p.waitForTimeout(300);
  await p.screenshot({path: `${OUT}/03-desktop-games-last-week.png`});
  await p.context().close();
}

// 04. Desktop dark: needs clarification. Only players who actually played that night are offered.
{
  const p = await open({width: 1440, height: 1000}, {dark: true});
  await entry(p, false);
  const jalens = [["Jalen Duren", "DET", "C", "WAS @ DET"], ["Jalen Suggs", "ORL", "G", "BKN @ ORL"], ["Jalen Johnson", "ATL", "F", "UTA @ ATL"], ["Jalen Smith", "CHI", "C", "CHI @ TOR"]];
  const cards = jalens.map(([n, t, pos, m], i) => `<div class="ak-card" style="margin:0;padding:14px;display:flex;align-items:center;gap:12px;${i === 0 ? "box-shadow:inset 0 0 0 2px var(--hw-accent);border-color:var(--hw-accent)" : ""}">
      <span class="ak-tri" style="height:40px;min-width:48px">${t}</span>
      <div style="flex:1;min-width:0"><div style="font:800 14px/1.2 Poppins">${n} <span style="font:700 10px Poppins;color:var(--hw-muted)">${pos}</span></div><div class="ak-cap" style="margin-top:6px">${m}</div></div>
      <span class="ak-kbd">${i + 1}</span></div>`).join("");
  await palette(p, {query: "how did jalen do last night",
    body: readAs("Player stat", [tok("Player", "Jalen", "4 matches", "warn"), tok("Date", "Last night", "Thu, Feb 5, 2026 · ET"), tok("Stat", "Full line")]) + `
      <div style="font:800 20px/1.2 Poppins;margin-bottom:4px">Which Jalen?</div>
      <div style="font:500 13px Poppins;color:var(--hw-muted);margin-bottom:14px">Four Jalens played on Thursday, Feb 5.</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">${cards}</div>
      <div class="ak-note" style="margin-top:14px">${ic("help", 13, "margin-top:1px")}<span>Looking for Jalen Brunson or Jalen Williams? The Knicks and Thunder didn’t play that night. Try “How many points did Jalen Brunson score on February 4, 2026?”</span></div>`,
    foot: `${hidden}<span style="flex:1"></span><span style="display:flex;align-items:center;gap:6px;white-space:nowrap">Press <span class="ak-kbd">1</span>–<span class="ak-kbd">4</span> to pick</span>`});
  await p.screenshot({path: `${OUT}/04-desktop-dark-which-jalen.png`});
  await p.context().close();
}

// 05a. Mobile empty state with keyboard: iOS search field + Cancel (Revolut, Trust Wallet), recent chips (Stoic),
// horizontally scrolling example cards above the keyboard (MLS Sidekick)
{
  const p = await open({width: 390, height: 844});
  const card = (cap, q) => `<div class="ak-card" style="flex:0 0 230px;margin:0;padding:12px 14px"><div class="ak-cap" style="margin-bottom:8px">${cap}</div><div style="font:600 13px/1.35 Poppins">${q}</div></div>`;
  await palette(p, {mob: true, query: "Ask about a game, stat, or series", placeholder: true, keyboard: true,
    body: `<div class="ak-cap" style="margin:4px 0 10px">Recent</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <span class="ak-sc" style="color:var(--hw-ink)">${ic("clock", 13)} Knicks games last week</span>
        <span class="ak-sc" style="color:var(--hw-ink)">${ic("clock", 13)} Who won the 2026 NBA Finals?</span></div>
      <div class="ak-cap" style="margin:22px 0 10px">Try asking</div>
      <div style="display:flex;gap:10px;margin-right:-14px;overflow:hidden">
        ${card("Stats", EX.stats)}${card("Series", EX.series)}</div>
      <div class="ak-note" style="margin-top:18px">${ic("eyeOff", 13, "margin-top:1px")}<span>Results stay hidden until you reveal them.</span></div>`});
  await p.screenshot({path: `${OUT}/05a-mobile-ask-empty-keyboard.png`});
  await p.context().close();
}

// 05. Mobile: the question itself asks for a result, so the whole answer is hidden behind one reveal.
{
  const p = await open({width: 390, height: 844});
  const team = (t, name) => `<div class="ak-row" style="padding:14px"><span class="ak-tri" style="height:34px;min-width:48px">${t}</span><span style="flex:1;font:800 14px Poppins">${name}</span>${red(22)}</div>`;
  await palette(p, {mob: true, query: "did the pistons beat the magic in the 2026 first round",
    body: readAs("Series", [tok("Series", "DET vs ORL"), tok("Round", "2026 First Round")], true) + `
      <div class="ak-card">
        <div style="padding:14px 14px 12px;border-bottom:1px solid var(--hw-line)"><div class="ak-cap">East · First Round · 2026</div>
          <div style="font:800 17px/1.25 Poppins;margin-top:8px">This answer is a result</div>
          <div style="font:500 12px/1.45 Poppins;color:var(--hw-muted);margin-top:4px">The winner, the series score, and how many games it went are hidden.</div></div>
        ${team("DET", "Detroit Pistons")}${team("ORL", "Orlando Magic")}
        <div class="ak-row" style="padding:14px;background:var(--hw-surface-muted)"><span class="ak-cap" style="flex:1">Games played</span>${red(22)}</div>
      </div>
      <div style="display:grid;gap:8px;margin-top:14px"><span class="ak-btn ink" style="min-height:46px">${ic("eye", 13)} Reveal answer</span><span class="ak-btn" style="min-height:46px">Open series ${ic("arrow", 13)}</span></div>`,
    foot: answerFoot(true)});
  await p.screenshot({path: `${OUT}/05-mobile-series-hidden.png`});
  await p.context().close();
}

// 06. Mobile: postseason summary with scores revealed. Winner bold, loser muted (Apple Sports).
{
  const p = await open({width: 390, height: 844});
  const rounds = [["First Round", "ATL", 2], ["East Semis", "PHI", 0], ["East Finals", "CLE", 0], ["NBA Finals", "SAS", 1]];
  const rows = rounds.map(([r, opp, l]) => `<div class="ak-row" style="padding:12px 14px"><span class="ak-cap" style="width:84px;color:var(--hw-ink)">${r}</span><span style="flex:1"></span>
    <span style="display:flex;align-items:center;gap:8px;font:800 17px Poppins;font-variant-numeric:tabular-nums"><span style="font-size:12px">NYK</span>4<span style="font-weight:500;color:var(--hw-muted)">–</span><span style="color:var(--hw-muted);opacity:.7">${l}</span><span style="font-size:12px;color:var(--hw-muted)">${opp}</span></span></div>`).join("");
  await palette(p, {mob: true, query: "how did the knicks do in the 2026 playoffs",
    body: readAs("Postseason", [tok("Team", "New York Knicks"), tok("Season", "2026 Playoffs")], true) + `
      <div class="ak-card">
        <div style="padding:16px 14px;border-bottom:4px solid var(--hw-accent)"><div class="ak-cap">Knicks · 2026 Postseason</div>
          <div style="font:800 24px/1.1 Poppins;margin-top:10px;text-transform:uppercase">Won the NBA Finals</div>
          <div style="display:flex;gap:22px;margin-top:12px">
            <div><div style="font:800 22px Poppins">16-3</div><div class="ak-cap" style="margin-top:4px">Record</div></div>
            <div><div style="font:800 22px Poppins">4 of 4</div><div class="ak-cap" style="margin-top:4px">Series won</div></div></div></div>
        ${rows}</div>
      <div style="display:grid;gap:8px;margin-top:14px"><span class="ak-btn pri" style="min-height:46px">Open 2026 bracket ${ic("arrow", 13)}</span></div>`,
    foot: `<span style="display:flex;align-items:center;gap:6px">${ic("eye", 13)} Scores are revealed · <span class="ak-edit" style="margin:0">Hide</span></span>`});
  await p.screenshot({path: `${OUT}/06-mobile-postseason-revealed.png`});
  await p.context().close();
}

// 07. Mobile dark: unsupported question. Two examples per the spec; diagnostics copy matches the 7-day, hash-only log.
{
  const p = await open({width: 390, height: 844}, {dark: true});
  const can = [["Stats", EX.stats], ["Series", EX.series]];
  await palette(p, {mob: true, query: "who has the most career points ever",
    body: `<div class="ak-card" style="padding:18px 16px">
        <span style="display:inline-grid;place-items:center;width:40px;height:40px;border-radius:10px;background:var(--hw-surface-muted);color:var(--hw-accent-ink)">${ic("help", 20)}</span>
        <div style="font:800 19px/1.2 Poppins;margin-top:14px">Can’t answer that one yet</div>
        <div style="font:500 13px/1.5 Poppins;color:var(--hw-muted);margin-top:6px">Career totals and all-time comparisons aren’t supported. Ask about games in one week, a player’s stats in one game, or a playoff series.</div></div>
      <div class="ak-cap" style="margin:20px 2px 8px">Try one of these</div>
      <div class="ak-card">${can.map(([c, q]) => `<div class="ak-row" style="padding:13px 14px"><span class="ak-cap" style="width:52px">${c}</span><span style="flex:1;font:600 13px/1.35 Poppins">${q}</span><span style="color:var(--hw-muted)">${ic("arrow", 14)}</span></div>`).join("")}</div>
      <div class="ak-note" style="margin-top:14px"><span>We keep an anonymous note of the question type, not your words, for up to 7 days to decide what to support next.</span></div>`});
  await p.screenshot({path: `${OUT}/07-mobile-dark-unsupported.png`});
  await p.context().close();
}

await b.close();
