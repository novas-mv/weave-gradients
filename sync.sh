#!/usr/bin/env bash
# The studio is the plugin's own panel opened in a browser. plugin/ui.html is the
# source of truth — run this after editing it so the hosted studio matches.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/plugin/ui.html" "$HERE/studio/index.html"
echo "studio/index.html ← plugin/ui.html"
