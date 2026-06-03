#!/usr/bin/env bash
# Publish docs/wiki/*.md to the GitHub wiki.
# Pre-req: enable the wiki once (repo Settings → Features → Wikis), then:
#   GH_TOKEN=<token> bash scripts/wiki_publish.sh
set -euo pipefail
REPO="moaidmoatasem/cherenkov-qa"
: "${GH_TOKEN:?set GH_TOKEN=<token> in the environment}"
SRC="$(git rev-parse --show-toplevel)/docs/wiki"
TMP="$(mktemp -d)"
git clone "https://x-access-token:${GH_TOKEN}@github.com/${REPO}.wiki.git" "$TMP" 2>/dev/null \
  || { git init -q "$TMP"; git -C "$TMP" remote add origin "https://x-access-token:${GH_TOKEN}@github.com/${REPO}.wiki.git"; }
cp "$SRC"/*.md "$TMP"/
cd "$TMP"
git add -A
git -c user.name="cherenkov-bot" -c user.email="bot@users.noreply.github.com" commit -q -m "docs(wiki): sync from docs/wiki" || { echo "nothing to publish"; exit 0; }
git push origin HEAD:master 2>/dev/null || git push origin HEAD:main
echo "Wiki published: https://github.com/${REPO}/wiki"
