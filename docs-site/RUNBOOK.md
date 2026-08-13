# CHERENKOV-QA Docs Site — Operations Runbook
# Covers: rollback, hotfix, staging, and emergency procedures.

## 1. Rollback a Bad Deploy

If a broken or unwanted version was shipped to `latest`:

```bash
# List all deployed versions
mike list

# Example output:
# 1.1 [latest] -> /
# 1.0

# Option A: Delete a version entirely (use with caution)
mike delete --push 1.1

# Option B: Revert 'latest' alias to a previous good version
mike set-default --push 1.0

# Option C: Redeploy a specific version from a known-good tag
git checkout v1.0.0
mike deploy --push --update-aliases 1.0 latest
mike set-default --push latest
```

**Verify recovery:**

```bash
# Check version list again
mike list

# Confirm the live site shows the right version
curl -s https://moaidmoatasem.github.io/cherenkov-qa/ | grep "version"
```

---

## 1b. `latest` Points at the Wrong Minor

The most common way this site goes wrong is not a bad build — it's an older
minor being **redeployed from a `main` checkout after a newer release shipped**.
`mike deploy --update-aliases 1.2 latest` run from tip-of-main does two damaging
things at once:

- the `/1.2/` URL now serves *newer* content than `/1.3/` (it was built from
  main, while `/1.3/` still holds what tag `v1.3.0` published), and
- the `latest` alias moves **backwards** to 1.2, so every `/latest/` link in the
  README lands readers on the older minor.

This happened on 2026-08-08 and again on 2026-08-10; the 08-10 deploy also undid
a manual `Copied 1.3 to latest` fix from the same day. Symptom: `/1.2/` looks
more current than `/1.3/`.

**Detect it:**

```bash
make docs-version-audit
# [FAIL] 'latest' points at 1.2 but 1.3 is deployed — readers landing on
#        /latest/ get the older minor.
```

**Fix it (preferred — rebuilds 1.3 from its tag, in CI):**

Actions → **Deploy Docs** → Run workflow, with `version=1.3`, `ref` blank
(resolves to the highest `v1.3.*` tag), `update_latest=true`.

**Fix it manually** if you must, from a clean checkout of the release tag:

```bash
git checkout v1.3.0
cd docs-site
mike deploy --push --update-aliases 1.3 latest
mike set-default --push latest
cd .. && make docs-version-audit   # expect [PASS]
```

Note that the older minor's directory keeps whatever content was last pushed
into it. If `/1.2/` was polluted with post-1.2 material, redeploy it from its
own tag without touching the alias:

```bash
git checkout v1.2.0
cd docs-site && mike deploy --push --update-aliases 1.2   # no 'latest'
```

**Prevention:** `make docs-deploy-release` now defaults `VERSION` to the
major.minor in `pyproject.toml` and refuses, via
`scripts/check_docs_site_versions.py`, to move `latest` backwards. Releases are
deployed by `docs-deploy.yml` from the release tag — deploying a version by hand
is the exception, not the routine.

---

## 2. Backport Docs to an Old Minor Version

Example: `v1.0.1` ships a security fix. The `1.0` docs need updating.

```bash
# 1. Check out the old release branch
git checkout v1.0.0 -b docs/hotfix-1.0

# 2. Apply the doc change
# (edit docs-site/docs/... as needed)
git add docs-site/
git commit -m "docs: backport security fix note to v1.0"

# 3. Deploy the patch to the existing 1.0 version (overwrites in place)
cd docs-site
mike deploy --push --update-aliases 1.0
# Do NOT add 'latest' — we don't want 1.0 to become latest

# 4. Verify
mike list
# Expected: 1.1 [latest], 1.0 (updated)

# 5. Clean up
git checkout main
git branch -d docs/hotfix-1.0
```

---

## 3. Bootstrap gh-pages for the First Time

Only needed once — on the very first `mike` deploy:

```bash
# Ensure the gh-pages branch exists and is initialized
cd docs-site
mike deploy --push dev      # creates gh-pages branch if absent

# Confirm in GitHub:
# Settings → Pages → Source = "Deploy from branch: gh-pages / root"
```

---

## 4. gh-pages Branch Protection

To prevent accidental pushes to `gh-pages` by any workflow other than `docs-deploy.yml`:

1. Go to GitHub → Settings → Branches → Add rule for `gh-pages`
2. Enable "Restrict who can push to matching branches"
3. Add only the `github-actions[bot]` actor

---

## 5. Check Current Deploy Status

```bash
# List all versions and aliases
cd docs-site && mike list

# Check what's on gh-pages
git ls-remote origin gh-pages

# Inspect gh-pages content
git fetch origin gh-pages
git show origin/gh-pages:versions.json
```

---

## 6. PR Preview Deploys (Future)

Currently not configured. To add Netlify-style PR previews:

```yaml
# In docs-deploy.yml, add a PR preview job:
docs-preview:
  if: github.event_name == 'pull_request'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r docs-site/docs-requirements.txt
    - run: mkdocs build --config-file docs-site/mkdocs.yml
    # Upload to Netlify or GitHub Pages PR environment
```

---

## 7. Emergency Contacts

| Issue | Action |
|-------|--------|
| gh-pages branch corrupt | Delete and re-run `mike deploy --push dev` from a known-good commit |
| Latest redirects to wrong version | `mike set-default --push <version>` |
| Internal docs accidentally published | Delete from gh-pages: `git push origin --delete gh-pages` then redeploy |
| Build stuck / CI frozen | Cancel the workflow run, push an empty commit to re-trigger |
