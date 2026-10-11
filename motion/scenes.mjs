// Vara Expo teaser backgrounds, 16:9. Same shape as a studio preset (compose mode), plus `drift`:
//   noise  – radius of the circle the noise offset travels per loop (folds breathe)
//   move   – how far each layer orbits its position, in frame units
//   turn   – how far each layer swings, degrees
//   angle  – gradient-angle swing, degrees
// Grade applied after render: pulls shadows/mids down ~30%, leaves the corner light (zone identity) mostly intact.
export const GRADE = "curves=all='0/0 0.15/0.09 0.3/0.2 0.5/0.4 0.75/0.7 1/0.95'";
const DRIFT = { noise: 0.18, move: 0.012, turn: 2.5, angle: 3 };

export const SCENES = {
  career: {
    drift: DRIFT,
    params: { mode: 'compose', seed: 7, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#14c8c8', glowB: '#f2553a',
      stops: [['#5a0c66', 0], ['#5e1878', .3], ['#2d2d7e', .55], ['#0b4c88', .8], ['#06386f', 1]],
      layers: [
        { type: 'blast',  c: '#f2553a', x: .02, y: .02, angle: -20, width: .3,  stretch: 2,   amt: .9 },
        { type: 'blast',  c: '#b81f6c', x: .16, y: .3,  angle: 30,  width: .26, stretch: 1.4, amt: .75 },
        { type: 'ribbon', c: '#f05a40', x: .14, y: .16, angle: 32,  bend: -.5, width: 0.091, edge: .35, amt: .75, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#0a86b8', x: .84, y: .5,  angle: 120, width: .32, stretch: .8, amt: .85 },
        { type: 'ribbon', c: '#14c8c8', x: .8,  y: .3,  angle: -108, bend: .45, width: 0.065, edge: .35, amt: .85, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#170c5c', x: .12, y: 1.0, angle: 10,  width: .45, stretch: 2.2, amt: 1.1 },
      ] },
  },

  // Career, less navy: plum/magenta body instead of indigo, lighter grade. For comparison with `career`.
  career_warm: {
    grade: "curves=all='0/0 0.15/0.11 0.3/0.25 0.5/0.45 0.75/0.73 1/0.96'",
    drift: DRIFT,
    params: { mode: 'compose', seed: 7, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#14c8c8', glowB: '#f2553a',
      stops: [['#64105e', 0], ['#6a1a72', .3], ['#4a1c78', .55], ['#1e3a86', .8], ['#0a4878', 1]],
      layers: [
        { type: 'blast',  c: '#f2553a', x: .02, y: .02, angle: -20, width: .3,  stretch: 2,   amt: .9 },
        { type: 'blast',  c: '#c42a70', x: .16, y: .3,  angle: 30,  width: .3,  stretch: 1.4, amt: .85 },
        { type: 'ribbon', c: '#f05a40', x: .14, y: .16, angle: 32,  bend: -.5, width: 0.091, edge: .35, amt: .75, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#e0607a', x: .55, y: .1,  angle: 0,   width: .3,  stretch: 1.6, amt: .35 },
        { type: 'blast',  c: '#0a8ab8', x: .84, y: .5,  angle: 120, width: .32, stretch: .8, amt: .9 },
        { type: 'ribbon', c: '#22d0a6', x: .8,  y: .3,  angle: -108, bend: .45, width: 0.065, edge: .35, amt: .9, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#2a0e62', x: .12, y: 1.0, angle: 10,  width: .45, stretch: 2.2, amt: .9 },
      ] },
  },

  // Education, new composition: light rises from the bottom-right, deep teal-plum body (not navy),
  // cyan hint top-left for Skills. Paired with career_warm for the road-led transition.
  education_warm: {
    grade: "curves=all='0/0 0.15/0.11 0.3/0.25 0.5/0.45 0.75/0.73 1/0.96'",
    drift: DRIFT,
    params: { mode: 'compose', seed: 27, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 200, aura: .55, grain: 0,
      glowA: '#2ad48a', glowB: '#1aa6e0',
      stops: [['#0c4a4a', 0], ['#0e4e50', .3], ['#174060', .55], ['#2a2a6c', .8], ['#3a1e66', 1]],
      layers: [
        { type: 'blast',  c: '#36d05a', x: 1.0, y: 1.0, angle: 30,  width: .34, stretch: 2,   amt: 1.0 },
        { type: 'blast',  c: '#c8d040', x: 1.0, y: .92, angle: 20,  width: .12, stretch: 1.6, amt: .45 },
        { type: 'ribbon', c: '#46d86a', x: .78, y: .82, angle: 150, bend: .45, width: 0.09, edge: .35, amt: .8, halo: 3.2, len: .9, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#14a08a', x: .45, y: .55, angle: 0,   width: .3,  stretch: 2,   amt: .45 },
        { type: 'ribbon', c: '#2ab8e8', x: .2,  y: .12, angle: -20, bend: -.4, width: 0.06, edge: .35, amt: .6, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#1a1e5c', x: .1,  y: .45, angle: 0,   width: .35, stretch: 1.6, amt: .7 },
      ] },
  },

  // Green leads; cyan/blue on the right hints at Skills, a little amber warmth top-left breaks the green.
  education: {
    drift: DRIFT,
    params: { mode: 'compose', seed: 27, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#1fd08a', glowB: '#1aa6e0',
      stops: [['#0a3a52', 0], ['#0e4a5a', .3], ['#123e74', .6], ['#13286e', .85], ['#121c5e', 1]],
      layers: [
        { type: 'blast',  c: '#3fcf5a', x: .02, y: .04, angle: -20, width: .32, stretch: 2,   amt: 1.0 },
        { type: 'blast',  c: '#d9b23a', x: .0,  y: .02, angle: -10, width: .14, stretch: 1.6, amt: .55 },
        { type: 'ribbon', c: '#46d86a', x: .14, y: .16, angle: 32,  bend: -.5, width: 0.091, edge: .35, amt: .7, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#0f8fc8', x: .84, y: .5,  angle: 120, width: .32, stretch: .8, amt: .85 },
        { type: 'ribbon', c: '#2ad4e8', x: .8,  y: .3,  angle: -108, bend: .45, width: 0.065, edge: .35, amt: .8, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#0c1650', x: .12, y: 1.0, angle: 10,  width: .45, stretch: 2.2, amt: 1.1 },
      ] },
  },

  // Blue leads; violet/magenta on the right hints at Market, a soft coral bloom left (as in the brief's Sky board).
  skills: {
    drift: DRIFT,
    params: { mode: 'compose', seed: 11, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#3ad0ff', glowB: '#9a3ee0',
      stops: [['#0b2f86', 0], ['#0d3f9c', .3], ['#122f8a', .6], ['#1a207a', .85], ['#1c1666', 1]],
      layers: [
        { type: 'blast',  c: '#1aa4ec', x: .02, y: .04, angle: -20, width: .32, stretch: 2,   amt: 1.0 },
        { type: 'blast',  c: '#c86a7c', x: .0,  y: .5,  angle: 30,  width: .2,  stretch: 1.4, amt: .45 },
        { type: 'ribbon', c: '#3ac8f5', x: .14, y: .16, angle: 32,  bend: -.5, width: 0.091, edge: .35, amt: .7, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#7a2fd0', x: .84, y: .5,  angle: 120, width: .32, stretch: .8, amt: .8 },
        { type: 'ribbon', c: '#b04ae8', x: .8,  y: .3,  angle: -108, bend: .45, width: 0.065, edge: .35, amt: .75, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#0b1250', x: .12, y: 1.0, angle: 10,  width: .45, stretch: 2.2, amt: 1.1 },
      ] },
  },

  // Violet leads; amber/coral on the right hints back to Career and the warm finale, teal sliver for contrast.
  market: {
    drift: DRIFT,
    params: { mode: 'compose', seed: 19, count: 4, flow: .35, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#b04ae8', glowB: '#ff9a4a',
      stops: [['#3a0f86', 0], ['#4a1898', .3], ['#33188a', .6], ['#22157a', .85], ['#1a1266', 1]],
      layers: [
        { type: 'blast',  c: '#a33fe8', x: .02, y: .04, angle: -20, width: .32, stretch: 2,   amt: 1.0 },
        { type: 'blast',  c: '#2bb8c8', x: .0,  y: .55, angle: 30,  width: .16, stretch: 1.4, amt: .4 },
        { type: 'ribbon', c: '#b856f0', x: .14, y: .16, angle: 32,  bend: -.5, width: 0.091, edge: .35, amt: .7, halo: 3.2, len: .8, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#d0507a', x: .84, y: .5,  angle: 120, width: .32, stretch: .8, amt: .7 },
        { type: 'ribbon', c: '#ff9a4a', x: .8,  y: .3,  angle: -108, bend: .45, width: 0.065, edge: .35, amt: .6, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#120c50', x: .12, y: 1.0, angle: 10,  width: .45, stretch: 2.2, amt: 1.1 },
      ] },
  },

  // Summary + logo: the brief's navy board. Left half stays flat navy; light lives right — teal, violet, amber.
  finale: {
    drift: DRIFT,
    params: { mode: 'compose', seed: 63, count: 4, flow: .3, depth: .4, sharp: .3, glow: .9, shadow: .3, scale: 1, rotate: 0, angle: 352, aura: .55, grain: 0,
      glowA: '#0a8fb0', glowB: '#e0b040',
      stops: [['#021d62', 0], ['#021d62', .45], ['#0a2378', .7], ['#1f1a86', .85], ['#2a1690', 1]],
      layers: [
        { type: 'blast',  c: '#0a6fa0', x: .52, y: .45, angle: -75, width: .2,  stretch: 3,   amt: .8 },
        { type: 'ribbon', c: '#0e8fb8', x: .54, y: .7,  angle: -112, bend: -.35, width: 0.065, edge: .35, amt: .7, halo: 3.2, len: 1, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#4a3cc8', x: .68, y: .05, angle: 10,  width: .22, stretch: 1.5, amt: .9 },
        { type: 'blast',  c: '#7a2a9c', x: .82, y: .62, angle: 45,  width: .28, stretch: 1.2, amt: .85 },
        { type: 'ribbon', c: '#e8b040', x: .86, y: .45, angle: -135, bend: .15, width: 0.039, edge: .35, amt: .85, halo: 3.2, len: .7, flip: false, fold: .45, sheen: .08, roll: .75 },
        { type: 'blast',  c: '#3a1890', x: 1.0, y: .1,  angle: 0,   width: .25, stretch: 1, amt: .8 },
      ] },
  },
};
