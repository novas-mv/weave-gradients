# Motion loops

Renders weaves as seamless drifting video loops for compositing (AE, Premiere), using the studio's own shader through headless Chromium.

```sh
node motion/render.mjs career --still career.png             # check a look (1920×1080)
node motion/render.mjs career --video career.mov             # 10 s loop, 25 fps, ProRes 422 HQ, BT.709
node motion/render.mjs career --video career.mp4 --seconds 8  # H.264 preview
```

Options: `--w/--h` size, `--fps`, `--seconds`, `--t` loop phase for stills (0–1), `--raw` to skip the grade.

`scenes.mjs` holds the scenes (Vara Expo teaser: career, education, skills, market, finale) in the same shape as a studio preset, plus:

- `GRADE`: an ffmpeg curve applied after rendering. It currently pulls shadows and mids down about 30% so type and the path sit on a quiet ground.
- `drift`: how far things move per loop. `noise` is the radius the noise field travels, `move` is how far layers orbit (frame units), `turn` and `angle` are degree swings. Every motion is one sine period per loop, so the last frame wraps cleanly into the first.

Needs Node 22, ffmpeg and Playwright (`PLAYWRIGHT_PATH` if it is not at `/opt/node-tools/node_modules/playwright`).
