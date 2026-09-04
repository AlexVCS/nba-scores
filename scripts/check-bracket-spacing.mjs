/** Browser regression against the running preview and local API.
 * PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/check-bracket-spacing.mjs <preview-playoffs-url> [output-directory]
 * Requires Chromium installed by Playwright. Outputs live response fixtures and measurements.
 */
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.argv[2];
if (!base) throw new Error('Pass the full local preview playoffs URL.');
const fixtureDirectory = process.env.BRACKET_FIXTURES || new URL('./fixtures/bracket-spacing/', import.meta.url).pathname;
const output = resolve(process.argv[3] || '/tmp/nba-bracket-spacing');
await mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true});
const page = await browser.newPage();
const fixtures = new Map();
await page.route('**/playoffs/series?*', async route => {
  const season = new URL(route.request().url()).searchParams.get('season');
  if (!fixtures.has(season)) {
    if (fixtureDirectory) {
      try { fixtures.set(season, await readFile(resolve(fixtureDirectory, `${season}.json`), 'utf8')); } catch { /* Fetch seasons absent from the fixture directory. */ }
    }
    const response = fixtures.has(season) ? null : await route.fetch();
    if (response && !response.ok()) throw new Error(`API ${season}: ${response.status()}`);
    if (response) fixtures.set(season, await response.text());
    await writeFile(`${output}/${season}.json`, fixtures.get(season));
  }
  await route.fulfill({status: 200, contentType: 'application/json', body: fixtures.get(season)});
});
const measurements = [];
async function settle() {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.waitForTimeout(80);
}
async function open(season, width, theme, globalResults = false, enlarged = false) {
  await page.setViewportSize({width, height: 1000});
  await page.evaluate(({theme, globalResults}) => {
    localStorage.clear();
    localStorage.setItem('theme', theme);
    localStorage.setItem('nba-scorez:design-1:show-all-results', String(globalResults));
  }, {theme, globalResults});
  const url = new URL(base); url.searchParams.set('season', season);
  await page.goto(url.href);
  await page.waitForFunction(() => [...document.querySelectorAll('a[aria-label*="View series details"], .mobile-series-card')].some(el => el.getBoundingClientRect().width > 0));
  if (enlarged) await page.addStyleTag({content: 'html {font-size: 24px !important}'});
  await settle();
}
async function measure(context) {
  await settle();
  const result = await page.evaluate(() => {
    const visible = el => el.getBoundingClientRect().width > 0 && !el.closest('[aria-hidden="true"], [inert]');
    const rounds = [...document.querySelectorAll('.hw-bracket-round')].filter(visible).map(round => {
      const heading = [...round.children].find(el => parseFloat(getComputedStyle(el).borderBottomWidth) >= 3);
      const slots = [...round.querySelectorAll('.hw-bracket-slot')].filter(visible);
      const boxes = slots.map(el => el.getBoundingClientRect()).sort((a,b) => a.top-b.top);
      const connectors = [...round.querySelectorAll('.hw-bracket-slot > span[aria-hidden]')].map(el => {
        const line = el.getBoundingClientRect(), slot = el.parentElement.getBoundingClientRect();
        return Math.abs(line.top - (slot.top + slot.height / 2));
      });
      const junctions = [...round.querySelectorAll('.hw-bracket-slots > span[aria-hidden]')].map(el => {
        const box = el.getBoundingClientRect();
        const grid = el.parentElement;
        const css = getComputedStyle(grid), lineCss = getComputedStyle(el);
        const tracks = css.gridTemplateRows.split(' ').map(parseFloat), gap = parseFloat(css.rowGap);
        const start = Number(lineCss.gridRowStart)-1, end = Number(lineCss.gridRowEnd)-2;
        const centers = tracks.map((height, index) => grid.getBoundingClientRect().top + tracks.slice(0,index).reduce((a,b)=>a+b,0) + gap*index + height/2);
        return Math.max(Math.abs(box.top-centers[start]), Math.abs(box.bottom-centers[end]));
      });
      return {gridTop: round.querySelector('.hw-bracket-slots')?.getBoundingClientRect().top, label: round.querySelector('h2,h3')?.textContent, exact: round.classList.contains('hw-bracket-round--exact'), gap: boxes.length && heading ? boxes[0].top-heading.getBoundingClientRect().bottom : null, cardGaps: boxes.slice(1).map((box,index)=>box.top-boxes[index].bottom), heights: boxes.map(box=>box.height), centers: boxes.map(box=>box.top+box.height/2), connectorError: Math.max(0,...connectors,...junctions)};
    });
    const exactTops = rounds.filter(round => round.exact).map(round => round.gridTop);
    return {rounds, gridAlignmentError: exactTops.length ? Math.max(...exactTops)-Math.min(...exactTops) : 0, overflow: document.documentElement.scrollWidth-innerWidth};
  });
  measurements.push({...context,...result});
  return result;
}
const controls = process.env.SWEEP_ONLY ? [] : process.env.BRACKET_SEASONS?.split(',') || ['1977-78','1952-53','1962-63','1974-75','1983-84','2001-02','1949-50','1953-54','2002-03','2025-26'];
await page.goto(new URL(base).origin);
try {
  for (const [width, theme, globalResults] of (process.env.SKIP_SWEEP ? [] : [[1600,'light',true],[1440,'dark',false]])) {
    for (let year=1946;year<=2025;year++) {
      const season=`${year}-${String((year+1)%100).padStart(2,'0')}`;
      await open(season,width,theme,globalResults);
      await measure({season,width,theme,state:globalResults?'global':'hidden',sweep:true});
    }
    await writeFile(`${output}/measurements.json`,JSON.stringify(measurements,null,2)+'\n');
    console.log(`Completed 80-season sweep: ${width}, ${theme}, ${globalResults?'global':'hidden'}`);
  }
  for (const season of controls) for (const width of [1440,1600,2048]) for (const theme of ['light','dark']) {
    await open(season,width,theme);
    await measure({season,width,theme,state:'hidden'});
    for(let stage=1;stage<=6;stage++) {
      const button = page.locator('button[aria-label^="Reveal "]:visible').first();
      if(!await button.count()) break;
      await button.click();
      await measure({season,width,theme,state:`round-${stage}`});
    }
    let button=page.getByRole('button',{name:'Hide all results',exact:true}).last();
    if(await button.count()) await button.click();
    await measure({season,width,theme,state:'hide-all'});
    button=page.getByRole('button',{name:'Show all results',exact:true}).last();
    if(await button.count()) await button.click();
    await measure({season,width,theme,state:'show-all'});
    await page.locator('button[data-rac][aria-label="Show all results"]').click();
    await measure({season,width,theme,state:'global-toggle-on'});
    await page.locator('button[data-rac][aria-label="Show all results"]').click();
    await measure({season,width,theme,state:'global-toggle-off'});
  }
  for (const width of [1439,390]) for (const theme of ['light','dark']) {
    await open('1952-53',width,theme);
    await measure({season:'1952-53',width,theme,state:'mobile'});
  }
  for (const season of ['1952-53','2025-26']) {
    await open(season,1440,'dark',false,true);
    await measure({season,width:1440,theme:'dark',state:'150%-text'});
  }
  await open('1952-53',2048,'dark');
  await page.screenshot({path:`${output}/1952-53-dark-hidden.png`,fullPage:true});
} finally {
  await browser.close();
  await writeFile(`${output}/measurements.json`,JSON.stringify(measurements,null,2)+'\n');
}
const stabilityFailures = [];
for (const measurement of measurements.filter(item => item.state.startsWith('round-') || ['show-all', 'hide-all'].includes(item.state))) {
  const baseline = measurements.find(item => !item.sweep && item.state === 'hidden' && item.season === measurement.season && item.width === measurement.width && item.theme === measurement.theme);
  measurement.rounds.forEach((round, index) => {
    const before = baseline?.rounds[index];
    if (round.exact && before && round.centers.some((center, slot) => Math.abs((center-round.gridTop)-(before.centers[slot]-before.gridTop)) > 1)) {
      stabilityFailures.push({season:measurement.season,width:measurement.width,state:measurement.state,reason:'slot moved when revealed',round});
    }
  });
}
const failures=measurements.flatMap(measurement=>[
  ...(measurement.gridAlignmentError>1?[{...measurement,reason:'cross-column grid misalignment'}]:[]),
  ...(measurement.overflow>0.5?[{...measurement,reason:'page overflow'}]:[]),
  ...measurement.rounds.filter(round=>(round.gap!==null&&round.gap<15.5)||round.cardGaps.some(gap=>gap<15.5)||round.connectorError>1).map(round=>({season:measurement.season,width:measurement.width,state:measurement.state,round}))
]);
failures.push(...stabilityFailures);
await writeFile(`${output}/failures.json`,JSON.stringify(failures,null,2)+'\n');
console.log(`${measurements.length} browser states; ${failures.length} failures; ${output}`);
if(failures.length) process.exitCode=1;
