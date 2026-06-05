# Spike #195 — Semantic Chunking / RAG for Large Specs

**Issue:** [#195](https://github.com/moaidmoatasem/cherenkov-qa/issues/195) · `[Horizon V][9c][spike]` · Source: Doc3 #3
**Status:** Spike (design + measurement plan). Implementation deferred to Phase 3+.

## Problem

Huge OpenAPI specs bloat the LLM context. The bundled `stripe_spec.json` is
**7.8 MB** (`stripe_spec.json`, 7,830,636 bytes). Today the only context
control is **depth-limited `$ref` resolution** in
[`cherenkov/stages/ingest.py`](../../cherenkov/stages/ingest.py):

```python
def resolve_refs_depth(node, schemas, resolved, depth, max_depth):  # ingest.py:16
    ...  # follows #/components/schemas/* refs up to Config.SCHEMA_DEPTH
```

`Config.SCHEMA_DEPTH` defaults to **1** (`cherenkov/core/config.py:19`). Depth-1
is a blunt instrument: it bounds *how deep* we follow refs from an operation,
but for a fat endpoint it still drags in every directly-referenced component
whether or not the generator needs it. On a Stripe-class spec that is still far
more schema than any single test needs, and it pushes unrelated bytes into the
prompt — which also **evicts the prefix cache** (the system-prompt / instruction
prefix that `cherenkov/ai/cache.py` relies on staying hot).

## Hypothesis

For a given endpoint + mutation, only a small, *semantically relevant* subset of
the resolved component schemas is strictly necessary to generate a correct test.
Retrieving that subset with embeddings — instead of "everything at depth N" —
should cut context size and generation latency materially, while keeping the
instruction prefix stable enough to stay cache-hot.

## Approach (spike)

Use **`nomic-embed-text`** (already an Ollama-family model, consistent with the
existing `cherenkov/ai/ollama_client.py` seam) as the retriever:

1. **Index** each component schema in `spec["components"]["schemas"]` as a
   chunk: `name + description + property names/types`, embedded once per spec
   and cached on disk keyed by spec hash.
2. **Query** per `(endpoint, mutation)`: embed the operation summary +
   parameter/body field names + the mutation `instruction`.
3. **Retrieve** top-k chunks by cosine similarity (k≈3–5), *unioned with* the
   directly-referenced schemas (never drop a `$ref` the operation explicitly
   names — retrieval augments, it doesn't replace correctness-critical refs).
4. Feed only that retrieved set to `generate` instead of the full depth-N
   `resolved_schemas`.

This slots in as an alternative populator of `EndpointSlice.schemas`
(`contracts.py:68`) — no change to the generate/review contract downstream.

## Measurement plan (the acceptance deliverable)

The issue's acceptance is: *measure context size and generation latency on a
large spec, with vs without chunking.* Proposed harness (`scripts/spike_195_rag.py`,
not yet written — this doc is the design):

| Metric | How measured | Baseline (depth-1) | RAG (top-k) |
|--------|--------------|--------------------|-------------|
| Prompt tokens / endpoint | tokenizer count of assembled prompt | — | — |
| Schema bytes injected | `len(json.dumps(slice.schemas))` | — | — |
| Generation latency (p50/p95) | wall-clock around `generate` call | — | — |
| Prefix-cache hit rate | `cherenkov/ai/cache.py` instrumentation | — | — |
| Test correctness (regression) | does generated test still go green→red on the bug-toggle target? | must not regress | must not regress |

Run on: (a) `stub/target_spec.json` (small control), (b) a mid spec, (c)
`stripe_spec.json` (7.8 MB stress case). Report the deltas; the spike succeeds
if RAG cuts injected bytes + latency on (c) **without** correctness regression
on (a).

## Risks / open questions

- **Retrieval miss = wrong test.** If top-k drops a schema the test actually
  needs, the generator hallucinates the shape. Mitigation: always union with
  explicitly-named `$ref`s; treat RAG as *additive recall*, and measure
  correctness as a hard gate (table row 5), not just latency.
- **Embedding cost / cold start.** Indexing a 7.8 MB spec is a one-time cost per
  spec hash — must be cached, or it dwarfs the savings on a single run.
- **Cache-warmth interaction.** Variable per-endpoint schema sets could
  *fragment* the prefix cache rather than preserve it. The measurement must
  confirm the cache-hit-rate row actually improves — this is the real point of
  the spike, not raw byte count.
- **Determinism.** CHERENKOV's mutation menu is deterministic by design;
  embedding-based retrieval introduces a non-deterministic selection step.
  Pin the model version and k, and snapshot retrieved-chunk IDs per run for
  reproducibility.
