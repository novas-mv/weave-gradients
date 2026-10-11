// Weave Gradients — main thread. Receives rendered tiles from the UI and places them.
figma.showUI(__html__, { width: 340, height: 700, themeColors: true });

let job = null;

function selInfo() {
  const s = figma.currentPage.selection;
  if (s.length !== 1) return null;
  const n = s[0];
  if (!('width' in n) || !('fills' in n)) return null;
  return {
    id: n.id, name: n.name,
    w: Math.round(n.width * 100) / 100, h: Math.round(n.height * 100) / 100,
    weave: n.getPluginData('weave') || null,   // settings of an editable weave layer
  };
}

figma.on('selectionchange', () => figma.ui.postMessage({ type: 'selection', sel: selInfo() }));

(async () => {
  const saved = await figma.clientStorage.getAsync('weave-settings');
  figma.ui.postMessage({ type: 'init', saved: saved || null, sel: selInfo() });
})();

function absolute(f, parent) {
  if (parent && 'layoutMode' in parent && parent.layoutMode !== 'NONE') f.layoutPositioning = 'ABSOLUTE';
}

async function beginUpdate(msg) {
  const node = await figma.getNodeByIdAsync(msg.updateId);
  if (!node || node.removed) throw new Error('That weave layer no longer exists');
  if (node.getPluginData('weaveKind') === 'frame') {
    node.children.slice().forEach(c => c.remove());
    node.resize(msg.W, msg.H);
    return { mode: 'frame', node, created: false };
  }
  if (msg.count > 1) throw new Error('This layer holds a single image — lower the resolution (max 4096px) or insert a new weave');
  return { mode: 'fill', node, created: false };
}

async function beginInsert(msg) {
  const node = msg.selId ? await figma.getNodeByIdAsync(msg.selId) : null;
  if (node && msg.count === 1 && 'fills' in node) return { mode: 'fill', node, created: false };
  const f = figma.createFrame();
  f.name = msg.name;
  f.resize(msg.W, msg.H);
  f.fills = [];
  f.clipsContent = true;
  if (node && (node.type === 'FRAME' || node.type === 'COMPONENT')) {
    node.insertChild(0, f);
    absolute(f, node);
    f.x = 0; f.y = 0;
    f.constraints = { horizontal: 'SCALE', vertical: 'SCALE' };
  } else if (node && node.parent) {
    const p = node.parent;
    p.insertChild(p.children.indexOf(node) + 1, f);
    absolute(f, p);
    f.x = node.x; f.y = node.y;
  } else {
    const c = figma.viewport.center;
    f.x = Math.round(c.x - msg.W / 2);
    f.y = Math.round(c.y - msg.H / 2);
  }
  return { mode: 'frame', node: f, created: !node };
}

figma.ui.onmessage = async (msg) => {
  try {
    if (msg.type === 'save') {
      await figma.clientStorage.setAsync('weave-settings', msg.data);
    } else if (msg.type === 'begin') {
      job = msg.updateId ? await beginUpdate(msg) : await beginInsert(msg);
      job.label = msg.label;
      job.store = msg.store;     // JSON settings → editable; null → flattened
      job.update = !!msg.updateId;
      figma.ui.postMessage({ type: 'ack' });
    } else if (msg.type === 'tile') {
      const img = figma.createImage(msg.bytes);
      const paint = { type: 'IMAGE', imageHash: img.hash, scaleMode: 'FILL' };
      if (job.mode === 'fill') {
        job.node.fills = [paint];
      } else {
        const r = figma.createRectangle();
        r.name = msg.count > 1 ? 'Tile ' + (msg.i + 1) : 'Weave';
        r.resize(msg.w, msg.h);
        r.x = msg.x; r.y = msg.y;
        r.fills = [paint];
        r.constraints = { horizontal: 'SCALE', vertical: 'SCALE' };
        job.node.appendChild(r);
      }
      figma.ui.postMessage({ type: 'ack' });
    } else if (msg.type === 'end') {
      if (job) {
        const n = job.node;
        if (job.store) {
          n.setPluginData('weave', job.store);
          n.setPluginData('weaveKind', job.mode);
          n.setRelaunchData({ edit: 'Edit this weave' });
        } else {
          n.setPluginData('weave', '');
          n.setPluginData('weaveKind', '');
          n.setRelaunchData({});
        }
        figma.currentPage.selection = [n];
        if (job.created) figma.viewport.scrollAndZoomIntoView([n]);
        figma.notify((job.update ? 'Weave updated · ' : 'Weave inserted · ') + job.label);
        figma.ui.postMessage({ type: 'selection', sel: selInfo() });
      }
      job = null;
    } else if (msg.type === 'notify') {
      figma.notify(msg.text, { error: !!msg.error });
    }
  } catch (e) {
    job = null;
    figma.ui.postMessage({ type: 'error', message: String((e && e.message) || e) });
  }
};
