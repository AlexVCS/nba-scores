/** Archived UI verification: requires the removed search UI to be restored.
 * Run against Vite: PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/verify-ask-search.mjs stage1|stage2 [url]
 * BROWSER=webkit selects desktop WebKit. API responses are deterministic browser fixtures.
 */
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
const playwright = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const stage = process.argv[2] || 'stage2';
const base = process.argv[3] || 'http://localhost:5173';
const browserName = process.env.BROWSER || 'chromium';
const output = `/tmp/nba-ask-search-${stage}-${browserName}`;
await mkdir(output, {recursive: true});
const browser = await playwright[browserName].launch({headless: true, ...(browserName === 'chromium' ? {channel:'chrome'} : {})});
const page = await browser.newPage({viewport: {width: 1100, height: 900}});
const records = [];
const pageErrors = [];
page.on('pageerror', error => pageErrors.push(error.message));
const stat = {kind:'statistic',title:'Jayson Tatum',title_spoiler:true,fields:[{label:'Points',value:31,spoiler:true},{label:'Assists',value:11,spoiler:true}],links:[{label:'View date',path:'/?date=2024-06-17',spoiler:false}],teams:[{id:1610612738,tricode:'BOS',name:'Boston Celtics'}],context:'Game 5 · 2024 NBA Finals'};
const game = {kind:'game',title:'NBA game',title_spoiler:false,fields:[{label:'Date',value:'2024-01-02',spoiler:false}],links:[],game:{gameId:'0022300464',gameCode:'20240102/BOSOKC',gameStatus:3,gameStatusText:'Final',gameLabel:'',gameSubLabel:'',gameTimeUTC:'2024-01-03T01:00:00Z',ifNecessary:false,seriesGameNumber:'',seriesText:'',awayTeam:{teamId:1610612738,teamTricode:'BOS',teamName:'Celtics',score:123},homeTeam:{teamId:1610612760,teamTricode:'OKC',teamName:'Thunder',score:127}}};
const answer = {status:'ok',items:[stat,game],interpretation:['2024 NBA Finals']};
let pending = [];
await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.pathname === '/ask') {
    const question = route.request().postDataJSON().question;
    if (question.startsWith('delayed')) {pending.push(route); return;}
    await route.fulfill({headers:{'access-control-allow-origin':'*'},json:answer});
  } else if (url.port === '8000') await route.fulfill({headers:{'access-control-allow-origin':'*'},json:{games:[],game_days:['2024-01-02']}});
  else await route.continue();
});
const input = () => page.getByLabel('Ask about NBA games and statistics', {exact:true});
const results = () => page.getByRole('list',{name:'Search results'});
const root = () => page.getByRole('search',{name:'Basketball search'}).locator('xpath=../..');
async function settle() {await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));}
async function open(design,theme,width=1100,height=900,reveal=true) {
  await page.setViewportSize({width,height});
  await page.goto(base);
  await page.waitForLoadState('networkidle');
  await page.evaluate(({theme,reveal})=>{localStorage.clear();localStorage.setItem('theme',theme);localStorage.setItem('nba-scorez:design-1:show-all-results',String(reveal));localStorage.setItem('nba-scorez:design-1:spoiler-onboarding:v1:dismissed','true');},{theme,reveal});
  await page.goto(`${base}/${design}?date=2024-01-02`);
  if(design==='design-1' && await input().count()===0) await openDialog();
  await input().waitFor();
  if(stage==='stage2') {assert.equal(await input().getAttribute('type'),'text');assert.equal(await input().getAttribute('inputmode'),'search');assert.equal(await input().getAttribute('enterkeyhint'),'search');}
}
async function openDialog() {
  const trigger=page.getByRole('button',{name:'Search',exact:true});
  await trigger.focus();await trigger.press('Enter');
  await page.locator('dialog[open]').waitFor();
  await settle();
  assert(await input().evaluate(el=>el===document.activeElement),'Input focused on opening');
}
async function search(question='fixture results') {await input().fill(question);await input().press('Enter');await results().waitFor();await settle();}
async function verifyLayout(context,forcedWidth) {
  if(forcedWidth) await root().evaluate((el,width)=>{el.style.width=`${width}px`;el.style.maxWidth='none';el.style.paddingLeft='0';el.style.paddingRight='0';},forcedWidth);
  await settle();
  const measurement = await root().evaluate(el=>{
    const style=getComputedStyle(el), td=el.querySelector('td[data-label]'), article=el.querySelector('article'), list=el.querySelector('ul[aria-label="Search results"]');
    return {width:el.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),containerType:style.containerType,tableDisplay:getComputedStyle(el.querySelector('table')).display,label:getComputedStyle(td,'::before').content,gameWidth:article.getBoundingClientRect().width,resultWidth:list.getBoundingClientRect().width,ink:getComputedStyle(el.querySelector('input')).color,accent:style.getPropertyValue('--ask-accent'),surface:style.getPropertyValue('--ask-surface'),rowAlignment:getComputedStyle(el.querySelector('tbody th')).textAlign,teamRule:el.querySelector('li[style]')?.style.getPropertyValue('--ask-team-rule')};
  });
  assert.equal(measurement.containerType,'inline-size');
  assert.equal(measurement.rowAlignment,'left','Table row label left aligned');
  assert.equal(measurement.tableDisplay,measurement.width<600?'block':'table',JSON.stringify({...context,...measurement}));
  if(measurement.width<600) assert.equal(measurement.label,'"Points"');
  assert(Math.abs(measurement.gameWidth-measurement.resultWidth)<3,`Game full width: ${JSON.stringify(measurement)}`);
  assert(measurement.teamRule,'Dynamic team rule retained');
  records.push({...context,...measurement});
}
try {
  for(const design of ['original','design-1']) for(const theme of ['light','dark']) {
    await open(design,theme);await search();
    for(const width of [599,600,601]) await verifyLayout({design,theme,forcedWidth:width},width);
    if(stage==='stage2' && design==='design-1') {
      await page.keyboard.press('Escape');await openDialog();await results().getByRole('table').waitFor();assert.equal(await page.getByRole('button',{name:'Reveal result',exact:true}).count(),0,'Global reveal respected after reopening');
    }
    await page.waitForTimeout(550);
    await page.screenshot({path:`${output}/${design}-${theme}.png`,fullPage:true});
    await page.emulateMedia({reducedMotion:'reduce'});
    await input().fill('delayed reduced motion');await input().press('Enter');
    await page.getByText('Searching basketball records',{exact:true}).waitFor();
    const animations=await root().locator('.animate-pulse').evaluateAll(els=>els.map(el=>getComputedStyle(el).animationName));
    assert(animations.length>0);assert(animations.every(name=>name==='none'));
    await page.getByRole('button',{name:'Clear search',exact:true}).click();
    for(const route of pending.splice(0)) await route.fulfill({headers:{'access-control-allow-origin':'*'},json:answer}).catch(()=>{});
    await page.emulateMedia({reducedMotion:'no-preference'});
  }
  if(stage==='stage1') for(const design of ['original','design-1']) for(const width of [640,667]) {
    await open(design,'light',width,375);await search();await verifyLayout({design,theme:'light',viewport:[width,375]});
  }
  if(stage==='stage2') {
    for(const [width,height] of [[640,960],[667,375],[768,1024],[1100,900],[390,844]]) {
      await open('design-1','dark',width,height);await search();await verifyLayout({design:'design-1',theme:'dark',viewport:[width,height]});
      const dimensions=await page.locator('dialog').evaluate(el=>({width:el.getBoundingClientRect().width,padding:getComputedStyle(el).paddingLeft,overflow:getComputedStyle(document.documentElement).overflow}));
      assert(dimensions.width<=768);assert.equal(dimensions.overflow,'hidden');
      const scrolling=await page.locator('dialog').evaluate(el=>[el,...el.querySelectorAll('*')].filter(node=>getComputedStyle(node).overflowY==='auto').map(node=>({paddingLeft:getComputedStyle(node).paddingLeft,paddingRight:getComputedStyle(node).paddingRight,overscroll:getComputedStyle(node).overscrollBehaviorY})));
      assert(scrolling.some(style=>style.overscroll==='contain'),'Inner scrolling contains overscroll');
      if(width>=640) assert(scrolling.some(style=>style.paddingLeft==='24px'&&style.paddingRight==='24px'),'Desktop scrolling content has 24px horizontal padding');
      records.push({viewport:[width,height],dialog:dimensions});
      await page.waitForTimeout(550);
    await page.screenshot({path:`${output}/dialog-${width}x${height}.png`,fullPage:true});
    }
    await open('design-1','light',1100,900,false);await search();
    await page.getByRole('button',{name:'Reveal result',exact:true}).first().click();
    await page.keyboard.press('Escape');await page.locator('dialog[open]').waitFor({state:'hidden'});
    assert(await page.getByRole('button',{name:'Search',exact:true}).evaluate(el=>el===document.activeElement),'Native focus restoration');
    assert.equal(await input().count(),0,'Contents unmount on close');
    await openDialog();assert.equal(await input().inputValue(),'fixture results');assert.equal(await results().getByRole('heading').count(),0,'Local spoiler reveal reset');
    await input().fill('delayed close');await input().press('Enter');await page.getByText('Searching basketball records',{exact:true}).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(pending.length,1);
    await openDialog();await page.getByText('Searching basketball records',{exact:true}).waitFor();assert.equal(await input().inputValue(),'delayed close');await page.keyboard.press('Escape');
    await pending.shift().fulfill({headers:{'access-control-allow-origin':'*'},json:answer});await openDialog();await results().waitFor();assert.equal(await input().inputValue(),'delayed close');
    const box=await page.locator('dialog').boundingBox();
    await page.mouse.move(2,2);await page.mouse.down();await page.mouse.move(box.x+30,box.y+30);await page.mouse.up();assert(await page.locator('dialog').evaluate(el=>el.open),'Outside-to-inside drag retained dialog');
    await page.mouse.move(box.x+30,box.y+30);await page.mouse.down();await page.mouse.move(2,2);await page.mouse.up();assert(await page.locator('dialog').evaluate(el=>el.open),'Inside-to-outside drag retained dialog');
    await page.mouse.click(2,2);await page.locator('dialog[open]').waitFor({state:'hidden'});await openDialog();
    await page.getByRole('button',{name:'Reveal result',exact:true}).first().click();
    await page.getByRole('link',{name:'View date',exact:true}).click();
    await page.waitForURL('**/design-1?date=2024-06-17');await page.locator('dialog[open]').waitFor({state:'hidden'});
    await openDialog();assert.equal(await input().inputValue(),'delayed close');
    await page.keyboard.press('Escape');
    await page.getByRole('link',{name:'View Original Scorez design',exact:true}).click();
    await page.waitForURL('**/original?date=2024-06-17');assert.equal(await input().inputValue(),'delayed close');await results().waitFor();
    await input().fill('shared original query');await input().press('Enter');await results().waitFor();
    await page.getByRole('link',{name:'View Gold on Hardwood design',exact:true}).click();await openDialog();
    assert.equal(await input().inputValue(),'shared original query');await results().waitFor();
    await page.getByRole('button',{name:'Clear search',exact:true}).click();assert.equal(await input().inputValue(),'');assert.equal(await results().count(),0);
    await input().fill('delayed clear');await input().press('Enter');await page.getByText('Searching basketball records',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Clear search',exact:true}).click();
    for(const route of pending.splice(0)) await route.fulfill({headers:{'access-control-allow-origin':'*'},json:answer}).catch(()=>{});
    await settle();assert.equal(await results().count(),0);assert.equal(await input().inputValue(),'');
    await page.getByRole('button',{name:'Close search',exact:true}).click();
    await page.getByRole('button',{name:'Search',exact:true}).click();await settle();assert(await input().evaluate(el=>el===document.activeElement),'Mouse opening focuses input');
    records.push({nativeDialog:'focus, Escape, persistence, in-flight completion, spoiler reset, backdrop drags, query-only navigation, clearing passed'});
  }
  assert.deepEqual(pageErrors,[],'No uncaught app errors');
  console.log(`${stage}: ${records.length} checks passed in ${browserName}; artifacts ${output}`);
} finally {
  await writeFile(`${output}/measurements.json`,JSON.stringify(records,null,2)+'\n');
  await browser.close();
}
