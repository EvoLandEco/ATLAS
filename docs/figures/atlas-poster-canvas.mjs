/**
 * ATLAS poster: Canvas paths, particles, lighting and editable text.
 * Install: npm install @napi-rs/canvas
 * Render: node atlas-poster-canvas.mjs [output.png|output.pdf] [width]
 * Transparent globe: node atlas-poster-canvas.mjs globe.png 3072 --globe
 * Requires Node.js 20+ and the macOS Avenir and Avenir Next system fonts.
 * Artboard: 1024 × 1536. Default PNG: 2048 × 3072.
 * PDF: 12 × 18 inches at 640 ppi, rendered from 7680 × 11520 pixels.
 * Width arguments are in pixels. No bitmap input.
 * Globe connections are decorative and do not represent observations.
 */
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const { createCanvas, Path2D, GlobalFonts, PDFDocument } = createRequire(import.meta.url)('@napi-rs/canvas');
const output = process.argv[2] ?? fileURLToPath(new URL('./atlas-poster-canvas.png', import.meta.url));
const isPDF = output.toLowerCase().endsWith('.pdf');
const globeOnly = process.argv.includes('--globe');
assert(!globeOnly || !isPDF, 'The transparent globe requires PNG output.');
const width = Number(process.argv[3] ?? (isPDF ? 7680 : 2048));
assert(Number.isInteger(width) && width >= 512 && width <= 8192 && width % 2 === 0,
  'Width must be an even integer from 512 through 8192.');
assert(!isPDF || width >= 7200, 'A 12 inch PDF requires at least 7200 pixels for 600 ppi.');
assert(globeOnly || (GlobalFonts.has('Avenir') && GlobalFonts.has('Avenir Next')), 'Install the Avenir and Avenir Next fonts.');
const scale = width / 1024, height = width * 3 / 2;
const canvas = createCanvas(width, height), hero = createCanvas(width, height);
const base = canvas.getContext('2d');
let ctx = base;
base.scale(scale, scale);
const TAU = 2 * Math.PI, cx = 512, cy = 740, radius = 307;
const cyan = [163, 237, 242], gold = [255, 224, 169], white = [250, 253, 242];
const rgba = (rgb, alpha) => `rgba(${rgb.join(',')},${alpha})`;
let seed = 19092026;
function random() {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed / 4294967296;
}
function glow(x, y, rx, ry, rgb, opacity) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(rx, ry);
  const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
  gradient.addColorStop(0, rgba(rgb, opacity));
  gradient.addColorStop(0.15, rgba(rgb, opacity * 0.69));
  gradient.addColorStop(0.45, rgba(rgb, opacity * 0.23));
  gradient.addColorStop(1, rgba(rgb, 0));
  ctx.fillStyle = gradient;
  ctx.fillRect(-1, -1, 2, 2);
  ctx.restore();
}
function stroke(path, color, weight = 1, dash = []) {
  ctx.lineCap = 'round';
  ctx.strokeStyle = color;
  ctx.lineWidth = weight;
  ctx.setLineDash(dash);
  ctx.stroke(typeof path === 'string' ? new Path2D(path) : path);
  ctx.setLineDash([]);
}
function ellipse(x, y, rx, ry, rotation = 0) {
  const path = new Path2D();
  path.ellipse(x, y, rx, ry, rotation, 0, TAU);
  return path;
}
function litPath(path, rgb, alpha = 0.65, weight = 0.8) {
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  stroke(path, rgba(rgb, alpha * 0.025), weight + 9);
  stroke(path, rgba(rgb, alpha * 0.10), weight + 2.4);
  stroke(path, rgba(rgb, alpha), weight);
  ctx.restore();
}
function star(x, y, size, rgb, strength = 1, rays = false) {
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  glow(x, y, size * 12, size * 12, rgb, 0.32 * strength);
  glow(x, y, size * 4, size * 4, rgb, 0.78 * strength);
  if (rays) {
    glow(x, y, size * 7, size * 0.45, rgb, strength * 0.56);
    glow(x, y, size * 0.45, size * 7, rgb, strength * 0.56);
  }
  ctx.fillStyle = rgba(rgb, strength);
  ctx.beginPath();
  ctx.arc(x, y, size, 0, TAU);
  ctx.fill();
  ctx.fillStyle = rgba(white, strength);
  ctx.beginPath();
  ctx.arc(x, y, size * 0.82, 0, TAU);
  ctx.fill();
  ctx.restore();
}

// Visible text bounds are measured in the reference image.
const textBounds = [];
function text(value, box, { bold = false, color = '#f5f5f2' } = {}) {
  const [left, top, right, bottom] = box;
  const family = bold ? 'Avenir Next' : 'Avenir', weight = bold ? 700 : 400;
  ctx.textAlign = 'left';
  ctx.letterSpacing = '0px';
  ctx.font = `${weight} 100px "${family}"`;
  let m = ctx.measureText(value);
  const size = 100 * (bottom - top) / (m.actualBoundingBoxAscent + m.actualBoundingBoxDescent);
  ctx.font = `${weight} ${size}px "${family}"`;
  m = ctx.measureText(value);
  const tracking = (right - left - m.actualBoundingBoxLeft - m.actualBoundingBoxRight) / (value.length - 1);
  ctx.letterSpacing = `${tracking}px`;
  assert(Number.isFinite(tracking), `Invalid tracking: ${value}`);
  assert(left >= 40 && right <= 984 && top >= 20 && bottom <= 1510, `Text exceeds the artboard: ${value}`);
  ctx.fillStyle = color;
  ctx.fillText(value, left + m.actualBoundingBoxLeft, top + m.actualBoundingBoxAscent);
  textBounds.push(box);
}

if (!globeOnly) {
ctx.fillStyle = '#00131b';
ctx.fillRect(0, 0, 1024, 1536);
glow(514, -25, 730, 610, [41, 114, 125], 0.62);
glow(509, 667, 550, 730, [27, 96, 111], 0.39);
glow(512, 434, 300, 280, [14, 90, 104], 0.22);
glow(505, 1030, 560, 445, [11, 88, 105], 0.50);
glow(505, 1500, 590, 250, [13, 76, 96], 0.23);
}

// The circular glass body sits inside independent, wider orbital paths.
ctx = hero.getContext('2d');
ctx.scale(scale, scale);
glow(cx, cy, 422, 433, [57, 152, 169], 0.15);
ctx.save();
ctx.clip(ellipse(cx, cy, radius, radius));
const shell = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
shell.addColorStop(0, 'rgba(12,42,50,0.03)');
shell.addColorStop(0.72, 'rgba(59,158,181,0.025)');
shell.addColorStop(0.91, 'rgba(74,172,191,0.13)');
shell.addColorStop(0.98, 'rgba(143,231,240,0.27)');
shell.addColorStop(1, 'rgba(177,248,250,0.13)');
ctx.fillStyle = shell;
ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);

// A fixed seed keeps the suspended particles reproducible.
for (let i = 0; i < 1900; i++) {
  const angle = random() * TAU, z = random() * 2 - 1;
  const r = Math.cbrt(random()) * radius, ring = Math.sqrt(1 - z * z) * r;
  const x = cx + Math.cos(angle) * ring, y = cy + Math.sin(angle) * ring;
  const rgb = random() < 0.30 ? gold : cyan, focus = random();
  const size = focus < 0.17 ? 1.7 + random() * 2.5 : 0.35 + random() * 0.90;
  const opacity = (0.16 + random() ** 2 * 0.70) * (0.65 + 0.35 * (z + 1) / 2);
  if (focus < 0.21) glow(x, y, size * 2.9, size * 2.9, rgb, opacity);
  else {
    ctx.fillStyle = rgba(rgb, opacity);
    ctx.beginPath();
    ctx.arc(x, y, size, 0, TAU);
    ctx.fill();
  }
}
ctx.restore();

for (const [x, y, rx, ry, rotation, opacity] of [
  [512, 713, 350, 43, -0.015, 0.22], [512, 740, 325, 307, 0.027, 0.43],
  [512, 741, 336, 306, -0.050, 0.18], [512, 741, 311, 307, 0.0, 0.49],
]) litPath(ellipse(x, y, rx, ry, rotation), cyan, opacity, 0.74);

const meridians = [
  'M512 433 C327 435 181 590 207 754 C220 937 368 1046 512 1047 C655 1048 824 903 815 752 C809 574 686 435 512 433',
  'M512 433 C382 448 284 584 284 752 C284 910 386 1037 512 1047 C641 1035 738 908 739 752 C740 586 642 447 512 433',
  'M512 433 C426 447 352 591 355 771 C358 935 432 1043 512 1047 C592 1042 644 914 638 747 C634 587 582 446 512 433',
  'M512 433 C296 468 227 665 268 835 C302 970 420 1045 512 1047 C690 1042 808 884 797 698 C785 549 648 437 512 433',
  'M512 433 C306 498 240 740 356 910 C414 1005 481 1043 512 1047 C586 1046 699 969 751 817 C796 686 708 492 512 433',
];
for (const [i, path] of meridians.entries())
  litPath(path, i === 3 ? gold : cyan, i === 0 ? 0.86 : 0.62, i === 0 ? 1.2 : 0.78);
for (const path of [
  'M308 555 C407 457 634 468 752 561', 'M226 624 C374 543 659 540 790 623',
  'M209 751 C358 668 671 666 816 751', 'M207 751 C355 816 657 818 815 752',
  'M239 841 C379 902 650 906 790 845', 'M302 983 C416 1021 609 1028 718 974',
]) litPath(path, cyan, 0.32, 0.65);
litPath('M207 751 C355 816 657 818 815 752', gold, 0.77, 0.80);

// Transparent ribbons carry specular highlights through the inner sphere.
const ribbons = [
  ['M289 751 C356 696 655 694 738 774 C803 839 681 870 572 875 C407 880 285 831 289 751 Z',
   'M289 751 C356 698 655 696 738 777 C779 824 688 859 581 865 C424 872 299 825 289 751 Z'],
  ['M510 433 C381 461 294 609 291 749 C286 880 397 1023 512 1047 C362 997 263 880 270 742 C275 594 372 464 510 433 Z',
   'M512 433 C383 464 290 612 282 750 C280 884 394 1021 512 1047'],
  ['M512 1047 C658 1021 803 894 802 752 C805 606 703 473 512 433 C678 487 781 606 783 752 C786 907 650 1024 512 1047 Z',
   'M512 1047 C658 1021 803 894 802 752 C805 606 703 473 512 433'],
];
const sheen = ctx.createLinearGradient(270, 505, 760, 992);
sheen.addColorStop(0, 'rgba(193,250,246,0.38)');
sheen.addColorStop(0.33, 'rgba(77,174,195,0.025)');
sheen.addColorStop(0.65, 'rgba(96,197,214,0.10)');
sheen.addColorStop(1, 'rgba(220,252,239,0.43)');
for (const [fill, edge] of ribbons) {
  ctx.fillStyle = sheen;
  ctx.fill(new Path2D(fill));
  litPath(edge, cyan, 0.34, 0.65);
}

// Curves and prominent nodes are placed from the reference illustration.
const connections = [
  ['M247 602 C369 625 591 664 779 601', 0, 0.94, 1],
  ['M308 555 C401 592 518 590 583 494', 1, 0.76, 1],
  ['M308 555 C324 659 406 730 456 691 C536 644 602 630 658 614', 1, 0.76, 0],
  ['M363 637 C406 686 543 743 617 792 C679 823 719 848 746 878', 1, 0.94, 1],
  ['M211 751 C236 727 308 690 363 637 C394 608 420 580 444 562', 0, 0.72, 0],
  ['M284 517 C334 500 391 529 444 562 C507 598 573 650 615 681 C672 735 704 815 746 878', 1, 0.88, 1],
  ['M363 637 C422 753 512 862 612 988', 1, 0.67, 1],
  ['M247 602 C209 728 221 819 242 839 C294 946 538 923 746 878', 1, 0.43, 1],
  ['M242 839 C290 754 411 705 456 691 C526 746 576 756 617 792 C679 738 734 674 779 601', 0, 0.84, 1],
  ['M308 751 C329 810 341 829 366 847 C450 856 548 827 617 792 C695 783 766 761 815 752', 0, 0.98, 1],
  ['M357 910 C427 886 516 817 615 681 C641 651 653 631 658 614', 1, 0.83, 1],
  ['M357 910 C393 945 460 974 512 963 C589 1000 704 987 746 878', 1, 0.86, 1],
  ['M363 637 C299 750 313 905 382 990', 1, 0.46, 1],
  ['M583 494 C651 504 734 541 779 601 C821 712 797 811 790 899', 1, 0.59, 1],
  ['M308 555 C365 477 641 427 741 520', 0, 0.47, 1],
  ['M382 990 C448 1015 555 1009 635 967', 1, 0.58, 0],
];
for (const [path, warm, alpha, dotted] of connections) {
  const rgb = warm ? gold : cyan;
  stroke(path, rgba(rgb, alpha * 0.065), 3.6);
  stroke(path, rgba(rgb, alpha), dotted ? 1.30 : 0.76, dotted ? [0.45, 3.5] : []);
}

const spine = ctx.createLinearGradient(512, 433, 512, 1047);
spine.addColorStop(0, 'rgba(244,255,233,0.85)');
spine.addColorStop(0.12, 'rgba(148,230,236,0.43)');
spine.addColorStop(0.50, 'rgba(126,219,234,0.39)');
spine.addColorStop(0.88, 'rgba(160,238,240,0.53)');
spine.addColorStop(1, 'rgba(250,255,228,0.95)');
stroke('M512 433 L512 1047', 'rgba(89,206,224,0.065)', 6);
stroke('M512 433 L512 1047', 'rgba(145,237,241,0.16)', 2.5);
stroke('M512 433 L512 1047', spine, 0.9);

// Fine fragments and luminous tangencies make the glass edge shimmer.
for (let i = 0; i < 240; i++) {
  const t = random() * TAU, r = radius + (random() - 0.5) * 25;
  const x = cx + Math.cos(t) * r, y = cy + Math.sin(t) * radius;
  const rgb = random() < 0.2 ? gold : cyan;
  star(x, y, 0.35 + random() * 0.8, rgb, 0.22 + random() * 0.48);
}
for (const [rx, ry, rotation, start, end] of [
  [307, 307, 0, 3.65, 4.59], [306, 307, 0, 0.29, 1.21], [318, 307, 0.02, 4.71, 5.23],
]) {
  const path = new Path2D();
  path.ellipse(cx, cy, rx, ry, rotation, start, end);
  litPath(path, cyan, 0.88, 1.35);
}
glow(291, 544, 33, 44, [210, 251, 239], 0.52);
glow(736, 930, 34, 39, [173, 241, 239], 0.30);

// Broad specular bands follow the diagonal lighting across the glass.
ctx.save();
ctx.globalCompositeOperation = 'screen';
for (let layer = 0; layer < 15; layer++) {
  const r = radius - layer * 1.20;
  const rimLight = ctx.createLinearGradient(282, 510, 742, 970);
  const strength = 0.61 * (1 - layer / 19);
  for (const [position, intensity] of [[0,1],[0.10,0.66],[0.24,0.08],[0.4,0],[0.6,0],[0.76,0.08],[0.90,0.55],[1,0.87]])
    rimLight.addColorStop(position, rgba([225, 255, 245], strength * intensity));
  stroke(ellipse(cx, cy, r, radius), rimLight, 1.75);
}
ctx.restore();
for (const [path, a, b] of [
  ['M512 433 C361 430 232 536 211 694', [226,618], [437,441]],
  ['M512 1047 C671 1041 797 937 811 786', [602,1035], [805,858]],
]) {
  const highlight = ctx.createLinearGradient(...a, ...b);
  highlight.addColorStop(0, 'rgba(182,247,247,0)');
  highlight.addColorStop(0.30, 'rgba(218,255,246,0.39)');
  highlight.addColorStop(0.58, 'rgba(250,255,238,0.72)');
  highlight.addColorStop(1, 'rgba(156,233,245,0.05)');
  stroke(path, highlight, 3.4);
}

const nodes = [
  [284,517,2.3,1], [308,555,3.5,1], [247,602,3.1,0], [324,599,2.8,0],
  [363,637,4.8,1], [444,562,3.7,1], [583,494,3.3,1], [658,614,4.4,1],
  [779,601,3.1,1], [741,520,2.2,0], [795,596,2.3,1], [615,681,3.7,0],
  [709,668,2.8,1], [456,691,4.0,1], [512,524,2.8,1], [512,486,1.7,0],
  [211,751,4.4,1], [242,839,3.0,1], [366,847,4.0,1], [355,769,2.1,1],
  [357,910,4.3,1], [382,990,4.1,1], [303,982,2.9,0], [238,923,2.2,0],
  [512,1013,2.1,1], [512,963,1.8,1], [512,924,2.3,1], [512,806,4.2,1],
  [617,792,5.0,1], [649,720,2.5,1], [706,734,2.7,0], [716,834,2.9,0],
  [746,878,4.0,1], [790,899,2.6,1], [815,752,3.0,1], [842,740,1.9,0],
  [832,783,2.1,0], [635,967,2.3,1], [702,993,1.8,0], [553,963,2.2,1],
  [479,785,1.8,0], [193,680,2.2,0], [309,744,2.0,0], [512,574,1.5,0],
];
for (const [x, y, size, warm] of nodes) star(x, y, size * 1.10, warm ? gold : cyan, 0.98, size >= 3.3);
star(512, 433, 3.3, gold, 1, true);
star(512, 1047, 3.9, white, 1, true);
glow(512, 433, 3, 36, cyan, 0.29);

// Mirror the globe into a shallow surface, with fading reflected light.
const reflection = createCanvas(width, height), rc = reflection.getContext('2d');
rc.scale(scale, scale);
rc.save();
rc.beginPath();
rc.rect(0, 1047, 1024, 55);
rc.clip();
rc.translate(512, 1047);
rc.scale(0.78, -0.078);
rc.drawImage(hero, -512, -1047, 1024, 1536);
rc.restore();
rc.globalCompositeOperation = 'destination-in';
const fade = rc.createLinearGradient(0, 1047, 0, 1102);
fade.addColorStop(0, 'rgba(255,255,255,0.26)');
fade.addColorStop(0.55, 'rgba(255,255,255,0.07)');
fade.addColorStop(1, 'rgba(255,255,255,0)');
rc.fillStyle = fade;
rc.fillRect(0, 0, 1024, 1536);
ctx = base;
glow(512, 1068, 340, 55, [27, 116, 130], 0.48);
glow(512, 1062, 237, 35, [80, 190, 199], 0.46);
glow(512, 1055, 102, 25, [130, 229, 228], 0.34);
ctx.save();
ctx.filter = `blur(${2.5 * scale}px)`;
ctx.drawImage(reflection, 0, 0, 1024, 1536);
ctx.restore();
ctx.drawImage(hero, 0, 0, 1024, 1536);
glow(512, 1066, 5, 40, [182, 242, 224], 0.82);
glow(512, 1060, 1.8, 32, [243, 255, 219], 0.48);

if (!globeOnly) {
text('OPEN SOURCE / RESEARCH PREVIEW', [300, 36, 716, 47], { color: '#d4eef3' });
text('ATLAS', [178, 79, 842, 200], { bold: true });
text('Agentic Tracking and Longitudinal Analysis for Surveillance', [180, 214, 845, 236]);
text('One Health', [383, 269, 639, 305]);
text('outbreak intelligence.', [267, 321, 761, 369]);
text('Across sources, places and time.', [295, 381, 728, 405], { color: '#d6eef3' });
text('AI assisted. Human reviewed.', [317, 1107, 707, 1126], { color: '#d6eef3' });
text('Source evidence', [96, 1187, 279, 1204], { color: '#d6eef3' });
text('Longitudinal analysis', [399, 1187, 628, 1209], { color: '#d6eef3' });
text('Research datasets', [744, 1187, 936, 1204], { color: '#d6eef3' });
stroke('M337 1175 L337 1217 M687 1175 L687 1217', 'rgba(217,244,246,0.85)', 0.8);
text('Build with us.', [270, 1268, 758, 1332], { bold: true });
text('Scientific review, contributions and research support welcome.', [149, 1353, 877, 1374]);
text('Explore', [80, 1427, 158, 1449], { color: '#d6eef3' });
text('qtj.me/atlas', [181, 1424, 338, 1451], { color: '#ffd175' });
stroke('M394 1416 L394 1458', 'rgba(217,244,246,0.85)', 0.8);
text('Contribute', [450, 1427, 567, 1444], { color: '#d6eef3' });
text('github.com/EvoLandEco/ATLAS', [587, 1427, 948, 1451], { color: '#ffd175' });
}

// Checks cover the copy, central spine, reflected light and encoded dimensions.
assert.equal(textBounds.length, globeOnly ? 0 : 16);
const sample = (x, y) => base.getImageData(Math.round(x * scale), Math.round(y * scale), 1, 1).data;
assert(sample(512, 433)[0] > 180, 'The upper pole must emit light.');
assert(sample(512, 740)[1] > sample(503, 740)[1], 'The central spine must remain visible.');
assert(sample(512, 1060)[1] > sample(150, 1060)[1] + 40, 'The surface must receive reflected light.');
if (globeOnly) {
  assert.equal(sample(0, 0)[3], 0, 'The globe canvas must have a transparent background.');
  const bounds = [64, 300, 896, 864].map(value => Math.round(value * scale));
  const [x, y, w, h] = bounds;
  const asset = createCanvas(w, h), ac = asset.getContext('2d');
  ac.drawImage(canvas, x, y, w, h, 0, 0, w, h);
  assert.equal(ac.getImageData(0, 0, 1, 1).data[3], 0, 'The cropped corner must remain transparent.');
  const png = asset.toBuffer('image/png');
  assert.equal(png.readUInt32BE(16), w);
  assert.equal(png.readUInt32BE(20), h);
  writeFileSync(output, png);
  console.log(`${output} (${w} × ${h}); transparent globe and reflection checks passed.`);
} else if (isPDF) {
  const pdf = new PDFDocument({ title: 'ATLAS — One Health outbreak intelligence',
    creator: 'ATLAS Node.js Canvas renderer', encodingQuality: 101, compressionLevel: 9 });
  pdf.beginPage(12 * 72, 18 * 72).drawImage(canvas, 0, 0, 12 * 72, 18 * 72);
  pdf.endPage();
  writeFileSync(output, pdf.close());
  console.log(`${output} (12 × 18 inches; ${width / 12} ppi; ${width} × ${height} pixels)`);
} else {
  const png = canvas.toBuffer('image/png');
  assert.equal(png.readUInt32BE(16), width);
  assert.equal(png.readUInt32BE(20), height);
  writeFileSync(output, png);
  console.log(`${output} (${width} × ${height}); text, light and PNG checks passed.`);
}
