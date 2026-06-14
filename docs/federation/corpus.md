# Divergence Corpus: Privacy & Data Retention

Opt-in anonymized aggregation of divergence findings across CHERENKOV instances. Enables research and tooling without exposing service topology or request details.

## What We Keep

Structural shape and divergence kinds:

- divergence_class: D1_SPEC_CODE, D5_SPEC_PROD, etc. (enum)
- severity: HIGH, MEDIUM, LOW (enum)
- claim_a / claim_b key structure: method + endpoint path **structure only** (hashed)
- Divergence metadata: timestamps (UTC), protocol version

The anonymized payload preserves the ability to:
- Count divergence types by class/severity
- Trend divergence frequency over time
- Train a fine-tuned model on (pair of fragments) → divergence list

## What We Strip & Hash

All identifying information is replaced with stable SHA-256 hashes (12-char truncated):

- rom_service, 	o_service → hashes (service topology hidden)
- File paths in repro steps or evidence → hashes
- Numeric identifiers (IDs, ports) → hashes
- Any string that could leak internal structure

Hash is deterministic: same input always produces the same hash. This enables:
- Correlation: different users with the same service name produce identical hashes, enabling aggregate statistics
- Stability: repeated corpus queries on the same data are reproducible
- Privacy: original strings are cryptographically unrecoverable

## How to Opt In

Set the environment variable before running CHERENKOV tests or inference:

`ash
export CHERENKOV_CORPUS_OPT_IN=true
`

Optionally override the corpus path (defaults to ~/.cherenkov/corpus.jsonl):

`ash
export CHERENKOV_CORPUS_PATH=/custom/path/corpus.jsonl
`

Submit divergences to the corpus:

`python
from cherenkov.federation.corpus import Corpus
corpus = Corpus()
corpus.submit(my_divergence_envelope)
`

## How to Opt Out

Default: opt-out. Do nothing. The corpus is not written to unless CHERENKOV_CORPUS_OPT_IN=true.

If previously opted in and want to stop:

`ash
unset CHERENKOV_CORPUS_OPT_IN
# or
export CHERENKOV_CORPUS_OPT_IN=false
`

Delete the corpus file:

`ash
rm ~/.cherenkov/corpus.jsonl
`

## Data Retention

- Corpus entries are append-only (immutable after write)
- No server-side sync; entirely local unless you push the file
- Entries are never automatically deleted; cleanup is manual
- Privacy depends on keeping the corpus file access-controlled

## Compliance Notes

- Anonymization is deterministic but not cryptographically secure against a determined attacker with side channels
- For production deployments, audit the Corpus.submit() anonymization logic (see cherenkov/federation/corpus.py)
- Test coverage in 	est_federation_corpus.py validates that service names and file paths do not appear in output
