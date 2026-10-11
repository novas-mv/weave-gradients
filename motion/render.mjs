// Render a weave as a still or a seamless drifting loop, using the studio's own shader.
//
//   node motion/render.mjs <scene> --still out.png [--t 0.25] [--w 1920 --h 1080]
//   node motion/render.mjs <scene> --video out.mov [--seconds 10 --fps 25] [--w 1920 --h 1080]
//   node motion/render.mjs <scene> --seq dir --start 0 --count 60 [--fps 25 --period 10]   PNG frames, drift continues across the range
//   add --overscan 0.3,0.06 to render past the frame edges (fraction of W,H per side) for panning in comp
//   add --raw to skip the grade in scenes.mjs
//
// Scenes live in motion/scenes.mjs. The drift is periodic in t ∈ [0,1), so frame N wraps to frame 0.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { SCENES, GRADE } from './scenes.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright');

const args = process.argv.slice(2);
const name = args[0];
const opt = k => { const i = args.indexOf('--' + k); return i < 0 ? null : args[i + 1]; };
const scene = SCENES[name];
if (!scene) { console.error(`Unknown scene "${name}". Known: ${Object.keys(SCENES).join(', ')}`); process.exit(1); }

const grade = args.includes('--raw') ? '' : ',' + (scene.grade || GRADE);   // --raw skips the grade
const W = +(opt('w') || 1920), H = +(opt('h') || 1080);
const here = path.dirname(fileURLToPath(import.meta.url));
const studio = pathToFileURL(path.join(here, '..', 'studio', 'index.html')).href;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage();
await page.goto(studio);

// Runs inside the studio page: its setParams/render/gl/U globals are in scope.
await page.evaluate(() => {
  window.__frame = (params, drift, t, W, H, ox = 0, oy = 0) => {
    const TAU = Math.PI * 2, p = JSON.parse(JSON.stringify(params));
    p.stops = p.stops.map(([c, pos]) => ({ c, pos }));
    const d = drift || {};
    (p.layers || []).forEach((l, i) => {
      const ph = TAU * (t + i * 0.37);                     // each layer on its own phase
      l.x += (d.move || 0) * Math.sin(ph);
      l.y += (d.move || 0) * Math.cos(ph) * 0.8;
      l.angle += (d.turn || 0) * Math.sin(ph + 1.3);
    });
    p.rotate += (d.rotate || 0) * Math.sin(TAU * t);
    p.angle += (d.angle || 0) * Math.sin(TAU * t + 0.9);
    setParams(p);
    const rnd = mulberry32(p.seed * 9973 + 1);
    for (let i = 0; i < 32; i++) rnd();
    const sx = rnd() * 100, sy = rnd() * 100, r = d.noise || 0;
    gl.uniform2f(U.uSeedOff, sx + r * Math.cos(TAU * t), sy + r * Math.sin(TAU * t));
    // overscan: render past the frame edges (ox/oy as a fraction of W/H per side) so the plate can pan in comp
    const pw = Math.round(W * (1 + 2 * ox)), ph = Math.round(H * (1 + 2 * oy));
    render(W, H, -ox * W, -oy * H, pw, ph, pw, ph, 1);
    const px = new Uint8Array(pw * ph * 4);
    gl.readPixels(0, 0, pw, ph, gl.RGBA, gl.UNSIGNED_BYTE, px);
    let s = ''; for (let i = 0; i < px.length; i += 0x8000) s += String.fromCharCode.apply(null, px.subarray(i, i + 0x8000));
    return btoa(s);
  };
});
const [OX, OY] = (opt('overscan') || '0,0').split(',').map(Number);   // e.g. --overscan 0.3,0.06
const PW = Math.round(W * (1 + 2 * OX)), PH = Math.round(H * (1 + 2 * OY));
const frame = async t => Buffer.from(await page.evaluate(([p, d, t, W, H, ox, oy]) => window.__frame(p, d, t, W, H, ox, oy), [scene.params, scene.drift, t, W, H, OX, OY]), 'base64');

const ff = (outArgs, extraIn = []) => spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${PW}x${PH}`, ...extraIn, '-i', '-', ...outArgs], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = p => new Promise((ok, no) => p.on('close', c => c ? no(new Error('ffmpeg ' + c)) : ok()));

if (opt('still')) {
  const p = ff(['-vf', 'vflip' + grade, '-frames:v', '1', opt('still')]);
  p.stdin.end(await frame(+(opt('t') || 0)));
  await done(p);
} else if (opt('seq')) {
  // Frames start..start+count-1 of a loop `period` seconds long, written as dir/NNNN.png.
  const fps = +(opt('fps') || 25), period = +(opt('period') || 10), start = +(opt('start') || 0), n = +(opt('count') || 1);
  const p = ff(['-vf', 'vflip' + grade, '-start_number', String(start), path.join(opt('seq'), '%04d.png')], ['-r', String(fps)]);
  for (let i = start; i < start + n; i++) {
    if (!p.stdin.write(await frame((i / (fps * period)) % 1))) await new Promise(r => p.stdin.once('drain', r));
  }
  p.stdin.end(); await done(p);
} else if (opt('video')) {
  const fps = +(opt('fps') || 25), n = Math.round(+(opt('seconds') || 10) * fps), out = opt('video');
  const enc = out.endsWith('.mov')
    ? ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-vendor', 'apl0']
    : ['-c:v', 'libx264', '-crf', '12', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-tune', 'grain'];
  const p = ff(['-vf', 'vflip' + grade + ',scale=out_color_matrix=bt709:out_range=tv', ...enc,
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', out], ['-r', String(fps)]);
  for (let i = 0; i < n; i++) {
    if (!p.stdin.write(await frame(i / n))) await new Promise(r => p.stdin.once('drain', r));
    if (i % 25 === 0) process.stderr.write(`\r${name}: ${i}/${n}`);
  }
  p.stdin.end(); await done(p); process.stderr.write(`\r${name}: ${n}/${n} → ${out}\n`);
}
await browser.close();
