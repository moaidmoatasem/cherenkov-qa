# ADR-016: Brain Map (extract → reconcile → publish, one map per project)

**Date:** 2026-08-12
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related:** ADR-004 (Clean Architecture), ADR-006 (Knowledge Mesh)

---

## Context

CHERENKOV knows a great deal about a repository that nobody can see at once: which
modules import which, which HTTP routes exist, which CLI commands are reachable,
which documents describe which code, and which tests touch any of it. That knowledge
was spread across the codebase itself, the docs tree, `agent_memory/`, and several
audit reports — each of which drifts independently. The repository's own history
contains the evidence: `docs/_archive/ROADMAP_RECONCILIATION.md` recorded gate results
that were never true, and `HANDOVER.md` exists precisely because no other artefact could
be trusted as the status anchor.

The ask was a *brain map*: an Obsidian-style graph of the project that is scalable,
automatically updated, reconciled, reusable across projects, and visible in the
dashboard.

Three approaches were considered:

1. **Generate documentation** (Sphinx/TypeDoc style) — produces per-symbol reference
   pages, not a navigable concept graph, and says nothing about docs, routes or tests
   as first-class things.
2. **Store the map in the existing knowledge mesh** (ADR-006) — the mesh answers
   semantic queries over heterogeneous stores; a code map needs exact structural
   queries (neighbourhood, degree, kind facets) and per-file invalidation, which is a
   different access pattern with a different write path.
3. **A dedicated cartography subsystem** with its own extract → reconcile → publish
   pipeline.

## Decision

Build `cherenkov/brainmap/` as a standalone subsystem following ADR-004's ports and
adapters shape, with three separated phases:

**Extract** — per file, pure, pluggable. Each extractor parses one file into nodes and
edges stamped with their `origin`. Python parsing is AST-only, so mapping a repository
never executes it. A profile's `extractors` list decides which run; entries are resolved
lazily through `importlib`, so an entry may be a bundled name *or* a dotted
`package.module:Class` spec belonging to another project entirely. Lazy resolution is
also what keeps the dependency one-directional — a registry that statically imports the
modules which import the registry is a real import cycle, and CodeQL was right to say so
on the first draft of this subsystem.

**Reconcile** — global. Extractors emit *hints* (an import string, a wikilink, a URL
literal); reconciliation joins them to real nodes and — the load-bearing part — records
every hint that does not join as a `Finding`. A map that silently drops a broken link
is the same failure mode as a test that silently asserts nothing.

**Publish** — the resolved graph is written to a separate table (`bm_links`) from the
raw per-file evidence (`bm_edges`). Readers query the published graph and never redo
resolution; a half-finished sync cannot publish a partial graph.

Persistence is SQLite keyed by `(project, id, origin)`, which makes "replace everything
derived from one file" the primitive operation and therefore makes sync incremental:
unchanged files cost one digest comparison and no I/O.

Three publication surfaces share that one map: an Obsidian vault (markdown, JSON Canvas
and `[[wikilinks]]` between notes), the `/api/v1/brainmap/*` HTTP API the dashboard
renders, and `cherenkov brain` on the CLI.

## Consequences

**Good**

- Full build of this repository: ~1,800 files, ~3,500 nodes, ~10,800 edges, ~6 s.
  Incremental sync with nothing changed: ~1 s, zero files parsed.
- Findings are actionable rather than decorative. The first run surfaced four Python
  files in this repository that do not parse, a set of TypeScript fixtures importing a
  `./client` module that does not exist, and documentation wikilinks pointing at notes
  that were never written.
- Reusable by construction: `--root` maps any repository, and a `[brainmap]` table in
  `cherenkov.toml` (or a standalone `brainmap.toml`) configures it per project. No
  extractor knows the name CHERENKOV.
- The vault is safe to regenerate on a schedule: generated notes carry a frontmatter
  marker and a manifest, so stale notes are pruned and hand-written notes are never
  touched.

**Costs**

- The frontend extractor is regex-based, not TypeScript-parser-based, so the engine can
  run from a plain Python install with no Node toolchain. It recognises declarations,
  not semantics.
- Reconciliation is whole-map on every sync. This is deliberate — resolution is global
  by nature, since a new module can satisfy a link that was dangling in a file nobody
  touched — but it means sync cost has a floor proportional to graph size, not to the
  diff.
- Node and edge kinds are open strings rather than closed enums. Extensibility was
  chosen over exhaustive type checking.

## Alternatives rejected

- **Reuse the knowledge mesh store** — different access pattern (exact structural
  traversal vs. semantic query) and different invalidation model (per source file vs.
  per item).
- **In-memory only, rebuilt per request** — a 6-second rebuild per dashboard load is
  not a dashboard.
- **A graph database** — the queries the UI needs are one- and two-hop neighbourhoods
  and facet counts, which SQLite indexes serve in milliseconds. A new service
  dependency would buy nothing.
