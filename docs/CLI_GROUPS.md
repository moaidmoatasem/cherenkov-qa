# CHERENKOV CLI Command Groups

The CHERENKOV CLI organizes its **45 top-level commands** into **7 logical command
groups** for discoverability. Every command remains registered at the top level for
backwards compatibility, so `cherenkov validate` and `cherenkov pipeline`
both work identically.

This page is the canonical reference for the command groups. The group layout is
defined in `cherenkov/cli/groups.py` (`GROUP_LAYOUT`).

---

There are deliberately no `review`, `enterprise` or `routine` groups: a group named like a command would shadow that command's own options (#1039). Those commands live under `operate` / `admin` and at the top level.

## Group overview

| Group | Purpose | Member commands |
|-------|---------|-----------------|
| [`pipeline`](#pipeline) | Core API conformance pipeline | `validate`, `verify`, `audit`, `check-suite`, `check-stale`, `synthetic`, `generate`, `bench`, `eval`, `drift` |
| [`model`](#model) | Model / VLM substrate commands | `visual`, `perf`, `mobile`, `mcp`, `examples` |
| [`operate`](#operate) | Long-running operations and observability | `daemon`, `dashboard`, `explore`, `map`, `author`, `record`, `tokens`, `governance`, `profile`, `teleport`, `hitl`, `review`, `ocr`, `routine` |
| [`admin`](#admin) | Setup, maintenance, and self-service | `init`, `doctor`, `self-test`, `eject`, `completion`, `report`, `diff`, `demo`, `enterprise`, `certify`, `playbook`, `guardian` |

---

## `pipeline`

Core API conformance pipeline: `validate`, `verify`, `audit`, `check-suite`,
`check-stale`, `synthetic`, `generate`, `bench`, `eval`, `drift`.

```bash
# List the commands in the group
cherenkov pipeline --help

# Run a command through the group (equivalent to the top-level form)
cherenkov pipeline --target http://localhost:8000
```

## `model`

Model / VLM substrate commands: `visual`, `perf`, `mobile`, `mcp`, `examples`.

```bash
cherenkov model --help
cherenkov model mcp serve
```

## `operate`

Long-running operations and observability: `daemon`, `dashboard`, `explore`,
`map`, `author`, `record`, `tokens`, `governance`, `profile`, `teleport`.

```bash
cherenkov operate --help
cherenkov operate daemon --interval 30
```

## `admin`

Setup, maintenance, and self-service: `init`, `doctor`, `self-test`, `eject`,
`completion`, `report`, `diff`, `demo`.

```bash
cherenkov admin --help
cherenkov admin doctor
```

---

## Related

- [GETTING_STARTED.md](GETTING_STARTED.md) — install + first run guide.
- [cli-reference.md](cli-reference.md) — full per-command reference.
- [STATUS.md](STATUS.md) — project status.