// Regenerates the NBA Scorez lockup so it matches the Playoffz lockup exactly:
// same badge box, same cap height, same baseline, same slant, same stroke weight,
// same palette. Measured targets come from public/images/playoffz.png.
import {readFileSync, writeFileSync} from "node:fs";

// --- Playoffz geometry, measured in its own 808x309 viewBox ---------------
const PZ = {
  boxH: 309,
  badge: {x: 28.12, y: 25.96, w: 89.92, h: 220.01},
  wordmark: {left: 140.59, capTop: 24.41, capBottom: 250.60},
  marginLeft: 28.12,
  marginRight: 18.43,
  slantDeg: 6.04,
  stemRatio: 0.1241, // stem width / cap height
};

// --- Scorez wordmark, in its own glyph units -----------------------------
const GLYPH_CAP = 712;      // glyph em box cap height
const SRC_XSCALE = 0.20807106;
const SRC_YSCALE = 0.31353591;
const CONDENSE = SRC_XSCALE / SRC_YSCALE; // bake into path data so glyph space is uniform

// Fake-bold: uniform outline stroke that thickens stems AND crossbars equally.
// Solve (stem + w) / (cap + w) = target stem ratio.
const SRC_STEM_RATIO = 0.0986; // measured on the rendered source wordmark
const stem0 = SRC_STEM_RATIO * GLYPH_CAP;
const strokeW = (PZ.stemRatio * GLYPH_CAP - stem0) / (1 - PZ.stemRatio);

// Round-glyph overshoot and the stroke both push past the nominal cap box, so the
// first pass rendered 1.9% tall and slightly off to the right. These constants fold
// the measured error back in; re-measure and re-derive them if the source art changes.
const CAP_CORRECTION = 0.98126;
const BADGE_LEFT_CORRECTION = -0.62;
const WORDMARK_LEFT_CORRECTION = 1.23;

const capWithStroke = GLYPH_CAP + strokeW;
const S = ((PZ.wordmark.capBottom - PZ.wordmark.capTop) / capWithStroke) * CAP_CORRECTION;
const C = S * Math.tan((PZ.slantDeg * Math.PI) / 180);

// Ink offsets from the transform origin, measured on the uncorrected first pass and
// rescaled by the same correction.
const INK_BELOW_ORIGIN = 5.05 * CAP_CORRECTION;
const INK_RIGHT_OF_ORIGIN = 6.745 * CAP_CORRECTION - WORDMARK_LEFT_CORRECTION;
const INK_WIDTH = 787.95 + 8 * strokeW * S; // 8 gaps reopened by the stroke

// --- Path data: scale every x coordinate by the condense factor -----------
const NUM = /-?\d*\.?\d+(?:e[-+]?\d+)?/giy;
function scaleX(d, k) {
  const out = [];
  let i = 0;
  const readNums = (n) => {
    const vals = [];
    while (vals.length < n) {
      NUM.lastIndex = i;
      while (i < d.length && /[\s,]/.test(d[i])) i++;
      NUM.lastIndex = i;
      const m = NUM.exec(d);
      if (!m) throw new Error(`expected number at ${i} in ${d.slice(i, i + 20)}`);
      vals.push(parseFloat(m[0]));
      i = NUM.lastIndex;
    }
    return vals;
  };
  const fmt = (v) => (Math.round(v * 1e4) / 1e4).toString();
  while (i < d.length) {
    const c = d[i];
    if (/[\s,]/.test(c)) { i++; continue; }
    if (!/[A-Za-z]/.test(c)) throw new Error(`unexpected token '${c}' at ${i}`);
    if (/[a-z]/.test(c) && c !== "z") throw new Error(`relative command '${c}' unsupported`);
    i++;
    if (c === "Z" || c === "z") { out.push("Z"); continue; }
    // absolute commands only, in the arity we know this file uses
    const arity = {M: 2, L: 2, H: 1, V: 1, Q: 4, C: 6, T: 2, S: 4}[c];
    if (arity === undefined) throw new Error(`unsupported command '${c}'`);
    // A command letter may be followed by repeated coordinate sets. Extra pairs after
    // a moveto are implicit linetos, not further movetos -- emitting M would split the
    // subpath and break the fill (this is what mangled the "A" on the first pass).
    let cmd = c;
    do {
      const v = readNums(arity);
      if (c === "H") v[0] *= k;
      else if (c === "V") { /* y only */ }
      else for (let j = 0; j < arity; j += 2) v[j] *= k;
      out.push(cmd + v.map(fmt).join(" "));
      if (cmd === "M") cmd = "L";
      NUM.lastIndex = i;
      let j = i;
      while (j < d.length && /[\s,]/.test(d[j])) j++;
      if (j >= d.length || /[A-Za-z]/.test(d[j])) break;
      i = j;
    } while (true);
  }
  return out.join("");
}

function build(srcPath, outPath, {wordmarkFill, playerFill}) {
  let svg = readFileSync(srcPath, "utf8");

  // 1. Rewrite every wordmark glyph path into uniform glyph space.
  const gStart = svg.indexOf("<g fill=");
  const gEnd = svg.indexOf("</g>", gStart) + 4;
  let group = svg.slice(gStart, gEnd);

  group = group.replace(/ d="([^"]*)"/g, (_, d) => ` d="${scaleX(d, CONDENSE)}"`);
  // The outline stroke grows each glyph by half its width on both sides, which eats
  // `strokeW` out of every gap. Add it back to each successive advance so the face
  // keeps its designed tracking instead of tightening as it gets heavier.
  let glyphIndex = 0;
  group = group.replace(/transform="translate\(([\d.-]+)\s+([\d.-]+)\)"/g,
    (_, tx, ty) => {
      const advance = parseFloat(tx) * CONDENSE + glyphIndex * strokeW;
      glyphIndex += 1;
      return `transform="translate(${advance.toFixed(4)} ${ty})"`;
    });

  // 2. Reposition: cap bottom on the Playoffz baseline, left edge on its left edge.
  //    Stroke straddles the outline, so pull in by half a stroke on each side.
  const F = PZ.wordmark.capBottom - INK_BELOW_ORIGIN;
  const E = PZ.wordmark.left - INK_RIGHT_OF_ORIGIN;

  group = group.replace(/transform="matrix\([^)]*\)"/,
    `transform="matrix(${S.toFixed(8)} 0 ${C.toFixed(8)} ${(-S).toFixed(8)} ${E.toFixed(4)} ${F.toFixed(4)})"`);
  group = group.replace(/<g fill="[^"]*"/,
    `<g fill="${wordmarkFill}" stroke="${wordmarkFill}" stroke-width="${strokeW.toFixed(3)}" ` +
    `stroke-linejoin="round" stroke-linecap="round"`);

  svg = svg.slice(0, gStart) + group + svg.slice(gEnd);

  // 3. Badge: same box as the Playoffz badge, aspect preserved by `meet`.
  const badgeAspect = 392.099 / 951.063;
  const bh = PZ.badge.h;
  const bw = bh * badgeAspect;
  svg = svg.replace(/<svg x="[\d.]+" y="[\d.]+" width="[\d.]+" height="[\d.]+"/,
    `<svg x="${(PZ.badge.x + BADGE_LEFT_CORRECTION).toFixed(4)}" y="${PZ.badge.y}" ` +
    `width="${bw.toFixed(4)}" height="${bh}"`);

  // 5. Trim the box to the Playoffz right margin so both logos sit identically
  //    inside their frames at any rendered height.
  const boxW = Math.round(PZ.wordmark.left + INK_WIDTH + PZ.marginRight);
  svg = svg.replace(/viewBox="0 0 \d+ \d+"/, `viewBox="0 0 ${boxW} ${PZ.boxH}"`);
  svg = svg.replace(/ width="[\d.]+px" height="[\d.]+px"/, ` width="${boxW}px" height="${PZ.boxH}px"`);

  // 4. Palette: the Playoffz blue and red, one blue for badge and wordmark.
  svg = svg.replace(/#1e4388/g, "#254d97").replace(/#c8202f/g, "#bc2530");
  svg = svg.replace(/fill="#fff"/g, `fill="${playerFill}"`);

  writeFileSync(outPath, svg);
  return svg;
}

const geom = {S, C, strokeW, condense: CONDENSE};
console.log("stroke-width (glyph units):", strokeW.toFixed(3));
console.log("uniform scale S:", S.toFixed(6), " shear C:", C.toFixed(6));
build("public/images/nba-scorez-with-borderless-official-logo.svg",
      "public/images/nba-scorez-lockup.svg", {wordmarkFill: "#254d97", playerFill: "#ffffff"});
build("public/images/nba-scorez-dark-with-borderless-official-logo.svg",
      "public/images/nba-scorez-lockup-dark.svg", {wordmarkFill: "#ffffff", playerFill: "#ffffff"});
console.log("wrote public/images/nba-scorez-lockup{,-dark}.svg");
