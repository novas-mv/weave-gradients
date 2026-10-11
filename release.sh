#!/usr/bin/env bash
# Cut a release: ./release.sh 1.3.0 "What changed, in one line"
# Stamps the version into the plugin, studio, guide page, README and version.json,
# adds a changelog entry, commits, tags, pushes and creates the GitHub release.
set -euo pipefail
cd "$(dirname "$0")"
V="${1:?usage: ./release.sh <x.y.z> \"what changed\"}"; NOTE="${2:?add a one-line note}"
[[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must look like 1.3.0" >&2; exit 1; }
git rev-parse -q --verify "refs/tags/v$V" >/dev/null && { echo "v$V already exists" >&2; exit 1; }
D="$(date +%Y-%m-%d)"

sed -i '' -E "s/^const VERSION = '[^']*'/const VERSION = '$V'/" plugin/ui.html
sed -i '' -E "s#<!--v-->[^<]*<!--/v-->#<!--v-->$V<!--/v-->#g; s#<!--d-->[^<]*<!--/d-->#<!--d-->$D<!--/d-->#g; s#refs/tags/v[0-9.]+\.zip#refs/tags/v$V.zip#g" index.html
sed -i '' -E "s#Current version: \*\*v[0-9.]+\*\*#Current version: **v$V**#; s#refs/tags/v[0-9.]+\.zip#refs/tags/v$V.zip#g" README.md
printf '{ "version": "%s", "date": "%s" }\n' "$V" "$D" > version.json
python3 - "$V" "$D" "$NOTE" <<'PY'
import sys; v,d,n=sys.argv[1:]
s=open('CHANGELOG.md').read(); i=s.index('\n## ')
open('CHANGELOG.md','w').write(s[:i]+f'\n## v{v} — {d}\n- {n}\n'+s[i:])
PY
./sync.sh

git add -A
git commit -q -m "Release v$V: $NOTE"
git tag -a "v$V" -m "v$V — $NOTE"
git push -q --follow-tags
gh release create "v$V" --title "v$V" --notes "$NOTE" >/dev/null
echo "Released v$V — live in about a minute at https://novas-mv.github.io/weave-gradients/"
