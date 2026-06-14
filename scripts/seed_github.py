#!/usr/bin/env python3
"""Idempotent GitHub seeder for the CHERENKOV Reality Engine plan.

Creates labels, milestones (epochs), epic issues, and task issues via the REST
API. Auth token is read from `git credential fill` (no token printed). Safe to
re-run: existing labels/milestones/issues (matched by name/title) are reused.
"""

import json
import subprocess
import sys
import urllib.request
import urllib.error

OWNER, REPO = "moaidmoatasem", "cherenkov-qa"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def get_token():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
    )
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    sys.exit("No GitHub token found via git credential.")


TOKEN = get_token()
H = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "cherenkov-seeder",
}


def call(method, path, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "null")


def get_all(path):
    out, page = [], 1
    while True:
        st, data = call("GET", f"{path}?per_page=100&page={page}&state=all")
        if st != 200 or not data:
            break
        out += data
        if len(data) < 100:
            break
        page += 1
    return out


# ---------- labels ----------
LABELS = [
    ("reality-engine", "5319e7", "Part of the Reality Engine plan"),
    ("epic", "b60205", "Parent tracking issue for an Epoch"),
    ("agent-ready", "0e8a16", "Self-contained; an agent can start now"),
    ("type:contract", "1d76db", "Defines an SPI / boundary; do first"),
    ("type:feature", "0052cc", "Build it"),
    ("type:research", "5319e7", "Investigate / spike"),
    ("type:proof", "d93f0b", "Demonstrate the bet"),
    ("area:substrate", "fbca04", "L0 router / providers"),
    ("area:truth-model", "fbca04", "L1 ingest / semantic graph"),
    ("area:divergence", "fbca04", "L2 Skeptic / Witness — the bet"),
    ("area:artifacts", "fbca04", "L3 emitters / oracles / eject"),
    ("area:continuity", "fbca04", "L4 daemon / PR diff"),
    ("area:experience", "fbca04", "L5 CLI / config / dashboard / docs"),
    ("area:federation", "fbca04", "L6 protocol / corpus"),
    ("epoch:0", "c5def5", ""),
    ("epoch:1", "c5def5", ""),
    ("epoch:2", "c5def5", ""),
    ("epoch:3", "c5def5", ""),
    ("epoch:4", "c5def5", ""),
    ("epoch:5", "c5def5", ""),
    ("epoch:6", "c5def5", ""),
]


def ensure_labels():
    existing = {l["name"] for l in get_all("/labels")}
    for name, color, desc in LABELS:
        if name in existing:
            continue
        st, _ = call(
            "POST", "/labels", {"name": name, "color": color, "description": desc}
        )
        print(f"label {name}: {st}")


# ---------- milestones ----------
EPOCHS = [
    ("Epoch 0 - Reconcile foundation", "Generator green; carve the substrate seam."),
    ("Epoch 1 - Substrate Router (L0)", "Model-agnostic inference router + providers."),
    (
        "Epoch 2 - Truth Model (L1)",
        "Multi-source ingest into a unified semantic graph.",
    ),
    (
        "Epoch 3 - Divergence Engine (L2)",
        "THE BET: find 5 real reproduced divergences.",
    ),
    (
        "Epoch 4 - Artifacts + Continuity (L3/L4)",
        "Emitters, oracles, daemon, PR behavioral diff.",
    ),
    (
        "Epoch 5 - Experience + Config (L5)",
        "Zero-config default + full config surface.",
    ),
    ("Epoch 6 - Federation (L6)", "Truth protocol, cross-service contracts, corpus."),
]


def ensure_milestones():
    existing = {m["title"]: m["number"] for m in get_all("/milestones")}
    nums = {}
    for i, (title, desc) in enumerate(EPOCHS):
        if title in existing:
            nums[i] = existing[title]
            continue
        st, m = call("POST", "/milestones", {"title": title, "description": desc})
        print(f"milestone {title}: {st}")
        nums[i] = m["number"]
    return nums


# ---------- issues ----------
def task(code, title, body, area, typ, accept):
    ac = "\n".join(f"- [ ] {a}" for a in accept)
    full = f"{body}\n\n**Acceptance criteria**\n{ac}\n"
    return {
        "code": code,
        "title": f"[{code}] {title}",
        "body": full,
        "labels": ["reality-engine", "agent-ready", typ] + ([area] if area else []),
    }


PLAN = [
    # (epoch_index, epic_title, epic_summary, default_area, [tasks])
    (
        0,
        "Reconcile the foundation",
        "Make the existing Track A generator green and carve the substrate seam without breaking it. See docs/vision/02_ROADMAP.md.",
        None,
        [
            task(
                "E0-1",
                "Audit current pipeline vs the original plan",
                "Compare the actual code under `cherenkov/` against `docs/TECHNICAL_DEVELOPMENT_PLAN.md`; record what truly works vs what is claimed.",
                None,
                "type:research",
                [
                    "A written gap report committed under docs/",
                    "Each phase marked works/partial/missing with evidence",
                ],
            ),
            task(
                "E0-2",
                "Stabilise CI green on main",
                "Get smoke tests + docs check passing reliably on `main`.",
                None,
                "type:feature",
                ["CI green on main", "Flaky steps identified or fixed"],
            ),
            task(
                "E0-3",
                "Extract a thin InferenceClient interface",
                "Introduce an interface in front of `cherenkov/ai/ollama_client.py` with NO behaviour change. This is the seam Epoch 1 grows into.",
                "area:substrate",
                "type:contract",
                [
                    "InferenceClient interface added",
                    "Ollama client implements it",
                    "All existing tests still pass",
                ],
            ),
            task(
                "E0-4",
                "Tag foundation-v0 release",
                "Tag the current working generator so we can always return to a known-good baseline.",
                None,
                "type:feature",
                [
                    "Annotated git tag foundation-v0 pushed",
                    "Release notes summarise capabilities",
                ],
            ),
        ],
    ),
    (
        1,
        "Substrate Router (L0)",
        "Intelligence becomes swappable per call, bounded by org policy. The keystone of the whole vision.",
        "area:substrate",
        [
            task(
                "E1-1",
                "Define ReasoningRequest / ReasoningResult contracts",
                "Typed boundary for all agent->model calls: `{task, output_schema, capability_tier, max_cost, max_latency, sensitivity}` and a validated result.",
                "area:substrate",
                "type:contract",
                [
                    "Pydantic models in core/contracts.py",
                    "Round-trip .model_validate_json() test",
                    "schema_version present",
                ],
            ),
            task(
                "E1-2",
                "Model Provider SPI + Ollama provider",
                "Plugin interface for model providers; first impl wraps the existing Ollama client behind E0-3's interface.",
                "area:substrate",
                "type:contract",
                [
                    "Provider SPI defined",
                    "Ollama provider passes a conformance test",
                    "No agent code names a model",
                ],
            ),
            task(
                "E1-3",
                "Add a second provider (OpenAI or Anthropic)",
                "Prove agnosticism: a cloud provider implementing the same SPI.",
                "area:substrate",
                "type:feature",
                [
                    "Second provider passes the same conformance test",
                    "Selected purely via config",
                ],
            ),
            task(
                "E1-4",
                "Router: route by capability tier + egress policy",
                "Pick a provider per request from tier + policy; fallback/spillover on failure.",
                "area:substrate",
                "type:feature",
                [
                    "Same generation runs on local AND cloud by config alone",
                    "Fallback path has a test",
                ],
            ),
            task(
                "E1-5",
                "Response/prefix cache + cost & latency accounting",
                "Cache responses and account spend per request.",
                "area:substrate",
                "type:feature",
                ["Cache hit measured", "Per-run cost + latency reported"],
            ),
            task(
                "E1-6",
                "Sovereignty dial: egress none|internal|any",
                "Enforce egress policy at the router; forbidden network calls fail loud.",
                "area:substrate",
                "type:feature",
                [
                    "egress=none blocks all external providers with a clear error",
                    "Default is internal",
                ],
            ),
        ],
    ),
    (
        2,
        "Truth Model (L1)",
        "A unified, queryable semantic model of what the system claims to be, from multiple sources.",
        "area:truth-model",
        [
            task(
                "E2-1",
                "Source Adapter SPI + OpenAPI adapter",
                "Plugin interface for sources; first impl reuses existing INGEST slicing to emit claims.",
                "area:truth-model",
                "type:contract",
                ["Source SPI defined", "OpenAPI adapter emits claims with provenance"],
            ),
            task(
                "E2-2",
                "Truth Model graph schema",
                "Endpoints, shapes, constraints, each claim tagged with its source (provenance).",
                "area:truth-model",
                "type:contract",
                [
                    "Graph schema in contracts",
                    "Claims carry source provenance",
                    "Serialisable + tested",
                ],
            ),
            task(
                "E2-3",
                "Embedding index over claims",
                "Index claims (reuse nomic-embed-text) for retrieval by the Skeptic.",
                "area:truth-model",
                "type:feature",
                ["Claims embeddable + queryable", "Top-k retrieval test"],
            ),
            task(
                "E2-4",
                "Traffic adapter (HAR / proxy replay)",
                "Turn a captured traffic sample into observed-behaviour claims (enables D2/D5).",
                "area:truth-model",
                "type:feature",
                ["HAR import yields prod-behaviour claims", "Provenance = traffic"],
            ),
            task(
                "E2-5",
                "DB-schema adapter",
                "Turn DB constraints into claims (enables D4).",
                "area:truth-model",
                "type:feature",
                ["Schema constraints become claims", "Provenance = db"],
            ),
            task(
                "E2-6",
                "cherenkov map command",
                "Build + inspect the Truth Model for a target.",
                "area:truth-model",
                "type:feature",
                [
                    "`cherenkov map` builds from spec + traffic",
                    "Renders the claim graph with provenance",
                ],
            ),
        ],
    ),
    (
        3,
        "Divergence Engine (L2) - THE BET",
        "Find 5 real, reproduced 'the system is lying to itself' divergences on a real OSS target. This proves the company.",
        "area:divergence",
        [
            task(
                "E3-1",
                "Skeptic agent: hypothesise divergences",
                "Generate divergence hypotheses across the 5-way space (D1-D5) from the Truth Model, via the Substrate Router.",
                "area:divergence",
                "type:feature",
                [
                    "Emits structured hypotheses for each D-class",
                    "Uses ReasoningRequest, never a hardcoded model",
                ],
            ),
            task(
                "E3-2",
                "Witness agent: deterministic reproduction harness",
                "For each hypothesis, fire a real (or mocked) request and diff the real response vs the claim.",
                "area:divergence",
                "type:contract",
                [
                    "Reproduces or rejects each hypothesis",
                    "Divergence report contract emitted",
                    "Re-execution is independent of the Skeptic",
                ],
            ),
            task(
                "E3-3",
                "Adversarial self-play (anti reward-hacking)",
                "A candidate test must pass a correct mock AND fail a deliberately-broken impl; tests that pass both are tautological and killed.",
                "area:divergence",
                "type:feature",
                [
                    "Tautological tests detected + dropped",
                    "Documented kill rate on a sample",
                ],
            ),
            task(
                "E3-4",
                "Divergence report contract",
                "{claim A, claim B, evidence, repro steps, severity} as a typed, serialisable artifact.",
                "area:divergence",
                "type:contract",
                [
                    "Contract in core/contracts.py",
                    "Round-trip test",
                    "Human-readable render",
                ],
            ),
            task(
                "E3-5",
                "PROOF RUN on a real OSS service",
                "Point CHERENKOV at a mid-size open-source service (its spec + replayable traffic). Document >=5 real, reproduced divergences humans missed.",
                "area:divergence",
                "type:proof",
                [
                    ">=5 reproduced divergences documented with evidence",
                    "Write-up published in docs/",
                    "Each is independently reproducible",
                ],
            ),
        ],
    ),
    (
        4,
        "Artifact Layer + Continuity (L3/L4)",
        "Close every divergence with the right artifact; run continuously.",
        "area:artifacts",
        [
            task(
                "E4-1",
                "Artifact Emitter SPI + Playwright emitter",
                "Plugin interface for outputs; first impl reuses Track A GENERATE/REVIEW/EJECT.",
                "area:artifacts",
                "type:contract",
                [
                    "Emitter SPI defined",
                    "Playwright emitter produces an ejectable suite",
                ],
            ),
            task(
                "E4-2",
                "Spec-patch + PR-comment emitters",
                "Emit a spec patch or a PR comment when that better closes a divergence than a test.",
                "area:artifacts",
                "type:feature",
                [
                    "Spec-patch emitter produces a valid diff",
                    "PR-comment emitter posts evidence",
                ],
            ),
            task(
                "E4-3",
                "Oracle SPI: spec / prod-snapshot / human / sibling-service",
                "Pluggable definition of 'correct'.",
                "area:artifacts",
                "type:contract",
                [
                    "Oracle SPI defined",
                    "spec+prism and prod-snapshot oracles implemented",
                ],
            ),
            task(
                "E4-4",
                "Daemon mode",
                "Watch sources, keep the Truth Model fresh, queue divergences.",
                "area:continuity",
                "type:feature",
                [
                    "`cherenkov daemon` runs continuously",
                    "Re-maps on source change",
                    "Divergence queue persisted",
                ],
            ),
            task(
                "E4-5",
                "Behavioral diff on PR (GitHub Action)",
                "On a PR, comment which endpoints changed actual behaviour vs base.",
                "area:continuity",
                "type:feature",
                [
                    "Action posts a behavioral diff",
                    "Distinguishes intended vs unintended drift",
                    "Opt-in via config",
                ],
            ),
        ],
    ),
    (
        5,
        "Experience + Configuration (L5)",
        "Trivially easy by default, fully configurable on top. See docs/vision/03_CONFIGURATION.md.",
        "area:experience",
        [
            task(
                "E5-1",
                "cherenkov init zero-config happy path",
                "Autodetect spec, pick sane defaults, produce value with no file editing.",
                "area:experience",
                "type:feature",
                [
                    "`init` then `run` works with no config",
                    "Defaults: offline, free, deterministic",
                ],
            ),
            task(
                "E5-2",
                "Layered cherenkov.toml + profiles",
                "Layered config with laptop/ci/enterprise-vpc/frontier-cloud profiles.",
                "area:experience",
                "type:contract",
                [
                    "Layered resolution implemented + tested",
                    "All 4 profiles work",
                    "Unknown keys error clearly",
                ],
            ),
            task(
                "E5-3",
                "cherenkov doctor",
                "Report effective config, device/model/egress health, and where each value came from.",
                "area:experience",
                "type:feature",
                [
                    "`doctor` prints effective config + provenance",
                    "Warns on CPU runtime / blocked egress",
                ],
            ),
            task(
                "E5-4",
                "Dashboard: Truth Model + live divergences",
                "Defer-first; mock data acceptable. Visualise the claim graph and open divergences.",
                "area:experience",
                "type:feature",
                [
                    "Renders Truth Model + divergence list",
                    "CLI remains source of truth",
                ],
            ),
            task(
                "E5-5",
                "Docs: getting-started + config cookbook",
                "5-minute getting-started for the new flow + a config cookbook.",
                "area:experience",
                "type:feature",
                [
                    "New user reaches first reproduced divergence in <10 min following docs",
                    "Cookbook covers all 4 profiles",
                ],
            ),
        ],
    ),
    (
        6,
        "Federation (L6) - frontier",
        "Cross-system truth without coordination.",
        "area:federation",
        [
            task(
                "E6-1",
                "Truth Protocol",
                "A shared schema for publishing/consuming a system's claims.",
                "area:federation",
                "type:contract",
                ["Versioned protocol spec", "Reference publish + consume impls"],
            ),
            task(
                "E6-2",
                "Cross-service contract check",
                "Producer claims vs consumer expectations, caught before deploy.",
                "area:federation",
                "type:feature",
                ["Two daemons detect an inter-service break pre-deploy"],
            ),
            task(
                "E6-3",
                "Opt-in anonymized divergence corpus",
                "Aggregate divergence patterns across systems, privacy-preserving.",
                "area:federation",
                "type:research",
                ["Opt-in + anonymization design", "Aggregate insight report"],
            ),
            task(
                "E6-4",
                "Divergence-specialist model (research)",
                "Fine-tune a model on the corpus to beat generalist LLMs at divergence detection.",
                "area:federation",
                "type:research",
                ["Eval vs a generalist baseline", "Findings written up"],
            ),
        ],
    ),
]


def main():
    ensure_labels()
    ms = ensure_milestones()
    existing_titles = {i["title"]: i["number"] for i in get_all("/issues")}

    def make_issue(title, body, labels, milestone):
        if title in existing_titles:
            print(f"skip (exists): {title}")
            return existing_titles[title]
        st, data = call(
            "POST",
            "/issues",
            {"title": title, "body": body, "labels": labels, "milestone": milestone},
        )
        if st not in (200, 201):
            print(f"FAIL {title}: {st} {data}")
            return None
        print(f"created #{data['number']}: {title}")
        existing_titles[title] = data["number"]
        return data["number"]

    for epoch_i, epic_title, summary, area, tasks in PLAN:
        milestone = ms[epoch_i]
        elabels = ["reality-engine", "epic", f"epoch:{epoch_i}"] + (
            [area] if area else []
        )
        etitle = f"[EPIC] Epoch {epoch_i} - {epic_title}"
        # create children first to list them in the epic body
        child_nums = []
        for t in tasks:
            labels = t["labels"] + [f"epoch:{epoch_i}"]
            n = make_issue(
                t["title"],
                t["body"] + f"\n\n_Epoch {epoch_i}. See docs/vision/02_ROADMAP.md._",
                labels,
                milestone,
            )
            if n:
                child_nums.append(n)
        checklist = "\n".join(f"- [ ] #{n}" for n in child_nums)
        ebody = (
            f"{summary}\n\n**Tasks**\n{checklist}\n\n"
            f"Filter all children: label `epoch:{epoch_i}` + `reality-engine`.\n\n"
            f"See docs/vision/02_ROADMAP.md and 01_ARCHITECTURE.md."
        )
        make_issue(etitle, ebody, elabels, milestone)

    print("\nDONE.")


if __name__ == "__main__":
    main()
