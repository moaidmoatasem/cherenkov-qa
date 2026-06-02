# CHERENKOV Configuration Cookbook

Covers all 4 profiles and common configuration scenarios. Every key in `cherenkov.toml` is optional — defaults apply when omitted.

---

## Profiles at a glance

| Profile | egress | deep tier | mode | Best for |
|---|---|---|---|---|
| `laptop` | internal | local (ollama) | one-shot | A developer on their machine |
| `ci` | internal | local (fast model) | one-shot + PR diff | CI/CD pipelines |
| `enterprise-vpc` | **none** | self-hosted | daemon + audit | Regulated environments |
| `frontier-cloud` | any | frontier API (GPT-4o) | one-shot/daemon | Maximum quality, cost OK |

---

## Profile 1: `laptop` (default)

Zero-config. Works offline, free, deterministic.

```bash
# After init, this is all you need:
./bin/cherenkov init
./bin/cherenkov doctor
./bin/cherenkov validate --target http://localhost:8000
```

Generated `cherenkov.toml`:
```toml
profile = "laptop"

[sources]
openapi = ["./stub/target_spec.json"]

[substrate]
egress = "internal"

[substrate.tiers.small]
provider = "ollama"
model = "qwen2.5-coder:7b"

[substrate.tiers.deep]
provider = "ollama"
model = "deepseek-r1:8b"

[substrate.budgets]
max_cost_usd_per_run = 0.0
max_latency_ms = 120000

[divergence]
space = ["D1", "D2", "D3", "D4", "D5"]
adversarial_self_play = true
min_severity = "low"

[artifacts]
emitters = ["playwright"]
eject = true

[oracle]
kind = "spec+prism"

[continuity]
mode = "one-shot"
behavioral_diff_on_pr = false
```

---

## Profile 2: `ci`

Same as laptop but with fast model for both tiers, reduced divergence space, and behavioral diff on PR enabled.

```toml
profile = "ci"

[sources]
openapi = ["./openapi.yaml"]

[substrate]
egress = "internal"

[substrate.tiers.small]
provider = "ollama"
model = "qwen2.5-coder:7b"

[substrate.tiers.deep]
# CI uses the same fast model for both tiers
provider = "ollama"
model = "qwen2.5-coder:7b"

[divergence]
# Narrower scope for CI speed
space = ["D1", "D2"]
adversarial_self_play = false
min_severity = "medium"

[artifacts]
emitters = ["playwright"]
eject = true

[continuity]
mode = "one-shot"
behavioral_diff_on_pr = true
```

---

## Profile 3: `enterprise-vpc`

Egress blocked, self-hosted models only. Daemon mode with audit log for regulated environments (banks, healthcare, government).

```toml
profile = "enterprise-vpc"

[sources]
openapi = ["./openapi.yaml"]

[substrate]
egress = "none"  # No outbound network calls

[substrate.tiers.small]
provider = "ollama"
model = "qwen2.5-coder:7b"

[substrate.tiers.deep]
provider = "ollama"
model = "deepseek-r1:8b"

[substrate.budgets]
max_cost_usd_per_run = 0.0
max_latency_ms = 120000

[divergence]
space = ["D1", "D2", "D3", "D4", "D5"]
adversarial_self_play = true
min_severity = "low"

[artifacts]
emitters = ["playwright", "k6"]
eject = true

[oracle]
kind = "spec+prism"

[continuity]
mode = "daemon"
behavioral_diff_on_pr = true
```

If you run with `egress = "none"` and a cloud provider is configured for the deep tier, `cherenkov doctor` will warn you.

---

## Profile 4: `frontier-cloud`

Maximum quality. Uses frontier API (GPT-4o) for deep reasoning. Budget-capped.

```toml
profile = "frontier-cloud"

[sources]
openapi = ["./openapi.yaml"]

[substrate]
egress = "any"  # Allows cloud API calls

[substrate.tiers.small]
provider = "ollama"
model = "qwen2.5-coder:7b"

[substrate.tiers.deep]
provider = "openai"
model = "gpt-4o"

[substrate.budgets]
max_cost_usd_per_run = 5.0
max_latency_ms = 30000

[divergence]
space = ["D1", "D2", "D3", "D4", "D5"]
adversarial_self_play = true
min_severity = "low"

[artifacts]
emitters = ["playwright", "spec-patch", "pr-comment"]
eject = true

[continuity]
mode = "one-shot"
behavioral_diff_on_pr = true
```

When using `frontier-cloud`, set `OPENAI_API_KEY` (or the equivalent for your provider):
```bash
export OPENAI_API_KEY="sk-..."
export CHERENKOV_PROFILE="frontier-cloud"
./bin/cherenkov doctor
```

---

## Environment variable overrides

Every config key can be set via `CHERENKOV_*` env vars. These take precedence over `cherenkov.toml` values:

| Environment variable | Config key | Example |
|---|---|---|
| `CHERENKOV_PROFILE` | `profile` | `export CHERENKOV_PROFILE=ci` |
| `CHERENKOV_EGRESS` | `substrate.egress` | `export CHERENKOV_EGRESS=any` |
| `CHERENKOV_TIER_SMALL_PROVIDER` | `substrate.tiers.small.provider` | `export CHERENKOV_TIER_SMALL_PROVIDER=ollama` |
| `CHERENKOV_TIER_SMALL_MODEL` | `substrate.tiers.small.model` | `export CHERENKOV_TIER_SMALL_MODEL=qwen2.5-coder:7b` |
| `CHERENKOV_TIER_DEEP_PROVIDER` | `substrate.tiers.deep.provider` | `export CHERENKOV_TIER_DEEP_PROVIDER=openai` |
| `CHERENKOV_TIER_DEEP_MODEL` | `substrate.tiers.deep.model` | `export CHERENKOV_TIER_DEEP_MODEL=gpt-4o` |
| `CHERENKOV_MODE` | `continuity.mode` | `export CHERENKOV_MODE=daemon` |

---

## Resolution order

Values are resolved from lowest to highest precedence:

```
built-in defaults  (hardcoded in the tool)
  -> profile defaults  (laptop | ci | enterprise-vpc | frontier-cloud)
    -> cherenkov.toml  (your project file)
      -> CHERENKOV_* env vars
        -> CLI flags
```

Highest wins. Every layer is optional. With none present, built-in defaults run (profile=laptop, egress=internal).

---

## Verifying your config

```bash
# See effective config, what layer each value came from, and system health:
./bin/cherenkov doctor
```

---

## Unknown keys

If `cherenkov.toml` contains a key that CHERENKOV doesn't recognise, you'll get an explicit error:

```
Unknown config key 'substrate.tiers.mega' in cherenkov.toml.
Known keys: artifacts.eject, artifacts.emitters, ...
```

All known keys are listed in the [config schema](/cherenkov/core/config_loader.py).
