#!/usr/bin/env bash
# Integrity-check mode of action.yml: run `cherenkov check`, write the markdown
# verdict to the step summary, and (on a pull request) upsert ONE sticky comment.
# Inputs arrive as INPUT_* env vars. Exit: 0 clean, 1 violations (when
# INPUT_FAIL_ON_DRIFT=true), 2 usage error / could not run.
set -u
OUT="${INPUT_OUTPUT_PATH:-cherenkov-check.md}"
BASE="${INPUT_BASELINE:-}"
if [ -z "$BASE" ]; then
  echo "cherenkov check needs a baseline: pass the 'baseline' input or run on a pull_request event." >&2
  exit 2
fi
# Shallow checkouts do not have the base commit; try to fetch it.
git cat-file -e "${BASE}^{commit}" 2>/dev/null || git fetch --no-tags --depth=1 origin "$BASE" 2>/dev/null || true

args=()
[ -n "${INPUT_TESTS_PATH:-}" ] && args+=("$INPUT_TESTS_PATH")
args+=(--baseline "$BASE" --format md)
[ -n "${INPUT_SPEC:-}" ] && args+=(--spec "$INPUT_SPEC")

cherenkov check "${args[@]}" > "$OUT"
code=$?
cat "$OUT"
[ -n "${GITHUB_STEP_SUMMARY:-}" ] && cat "$OUT" >> "$GITHUB_STEP_SUMMARY"

# Count finding bullets only: the "Not checked" list below them reuses the same class names.
violations=$(awk '/^\*\*Not checked:\*\*/{exit} /^- `(WEAKENED|DELETED|HALLUCINATED)`/{n++} END{print n+0}' "$OUT")
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "violations=${violations}"
    echo "drift-detected=$([ "$violations" -gt 0 ] && echo true || echo false)"
    echo "report-path=${OUT}"
  } >> "$GITHUB_OUTPUT"
fi

if [ "${INPUT_COMMENT:-true}" = "true" ] && [ -n "${INPUT_PR_NUMBER:-}" ] && [ -n "${GITHUB_TOKEN:-}" ] \
   && command -v gh >/dev/null 2>&1 && [ "$code" -le 1 ]; then
  export GH_TOKEN="$GITHUB_TOKEN"
  existing=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${INPUT_PR_NUMBER}/comments" --paginate \
    --jq '.[] | select(.body | contains("<!-- cherenkov-check -->")) | .id' 2>/dev/null | head -1)
  if [ -n "$existing" ]; then
    gh api -X PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${existing}" -F "body=@${OUT}" >/dev/null \
      || echo "warning: could not update the PR comment" >&2
  else
    gh api -X POST "repos/${GITHUB_REPOSITORY}/issues/${INPUT_PR_NUMBER}/comments" -F "body=@${OUT}" >/dev/null \
      || echo "warning: could not post the PR comment" >&2
  fi
fi

if [ "$code" -eq 1 ] && [ "${INPUT_FAIL_ON_DRIFT:-true}" != "true" ]; then
  exit 0
fi
exit "$code"
