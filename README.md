# Weave Gradients

Aurora-style gradient weaves — soft colour blooms and fabric-like folds — at print resolution.

**→ [Read this instead](https://novas-mv.github.io/weave-gradients/)** — same instructions, easier to follow, and the studio is one click away.

| | |
|---|---|
| **Studio** | <https://novas-mv.github.io/weave-gradients/studio/> — a web page, nothing to install |
| **Figma plugin** | [Download the ZIP](https://github.com/novas-mv/weave-gradients/archive/refs/heads/main.zip), then see below |

---

## Install the Figma plugin

1. [Download the ZIP](https://github.com/novas-mv/weave-gradients/archive/refs/heads/main.zip) and unzip it.
2. **Move the folder somewhere permanent** — Documents, not Downloads. Figma reads these files every time you run the plugin.
3. Figma → **Plugins → Development → Import plugin from manifest…**
4. Choose **`plugin/manifest.json`** inside that folder.

## Use it

- **Presets** load a look; **Shuffle** gives a new weave in the same style.
- **Gradient**: click the bar to add a stop (max 6), drag to move, Backspace to remove. Glow A/B colour the light.
- **Generative weave** makes random folds. **Compose layers** places each ribbon and blast yourself — drag the dots on the preview.
- **Insert as Editable** keeps the settings on the layer: select it later (or click **Edit weave** in Figma's right panel) and press **Update layer**. **Flattened** inserts a plain image.
- Over 4096 px, Figma inserts seamless tiles (Figma's image limit).

## Print

Use **Download** at 300 dpi (A4–A1) or 150 dpi (A0 and bigger). The PNG carries DPI metadata. Max ~240 MP per file.

## Editing this repo

`plugin/ui.html` is the source of truth. The studio is the same file opened in a browser — after editing it, run `./sync.sh` to copy it to `studio/index.html`.
