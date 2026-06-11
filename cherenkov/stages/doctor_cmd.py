"""
cherenkov/stages/doctor_cmd.py — E5-3: cherenkov doctor.
Authority: v3.1 + delta.

Report effective config, device/model/egress health, and where each value came from.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from cherenkov.core.config import Config
from cherenkov.core.compat import npx as _npx
from cherenkov.core.config_loader import (
    LayeredConfig,
    KNOWN_KEYS,
    load_effective_config,
)


def check_ollama_binary() -> tuple[bool, str]:
    path = shutil.which("ollama")
    if path:
        return True, path
    return False, "not found on PATH"


def check_ollama_daemon() -> tuple[bool, str]:
    path = shutil.which("ollama")
    if not path:
        return False, "binary not available"
    try:
        result = subprocess.run(
            [path, "list"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, "reachable"
        return False, f"daemon error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "timeout — daemon unresponsive"
    except FileNotFoundError:
        return False, "binary not found"


def check_ollama_model(model: str) -> tuple[bool, str]:
    path = shutil.which("ollama")
    if not path:
        return False, "ollama binary not available"
    try:
        result = subprocess.run(
            [path, "list"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            if model in result.stdout:
                return True, f"'{model}' is available"
            return False, f"'{model}' not pulled (run: ollama pull {model})"
        return False, f"cannot list models: {result.stderr.strip()}"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "cannot check"


def check_node() -> tuple[bool, str]:
    path = shutil.which("node")
    if path:
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=10,
            )
            return True, result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "cannot get version"
    return False, "not found on PATH"


def check_npx_playwright() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [_npx(), "playwright", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"not available ({result.stderr.strip()})"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "npx not found"


def check_prism_docker() -> tuple[bool, str]:
    """Check if Docker is available for Prism."""
    path = shutil.which("docker")
    if path:
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True, f"Docker {result.stdout.strip()} (Prism ready)"
            return False, "Docker daemon not running"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "cannot reach Docker"
    return False, "Docker not installed (Prism unavailable)"


def check_cargo() -> tuple[bool, str]:
    path = shutil.which("cargo")
    if path:
        try:
            result = subprocess.run(
                ["cargo", "--version"], capture_output=True, text=True, timeout=10,
            )
            return True, result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "cannot get version"
    return False, "not found on PATH"


def check_tauri_cli() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["cargo", "tauri", "info"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, "available"
        return False, "not installed (run: cargo install tauri-cli)"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "cargo not found"


def check_egress_blocked(cfg: LayeredConfig) -> tuple[bool, str]:
    """Check if the current egress policy would block cloud providers."""
    egress = cfg.get("substrate.egress", "internal")
    deep_provider = cfg.get("substrate.tiers.deep.provider", "ollama")
    warnings = []

    if egress == "none" and deep_provider != "ollama":
        warnings.append(
            f"egress=none but deep tier provider is '{deep_provider}'. "
            "Cloud providers require egress=any."
        )
    if egress == "internal" and deep_provider not in ("ollama",):
        warnings.append(
            f"egress=internal but deep tier provider is '{deep_provider}'. "
            "If this provider is external, set egress=any."
        )

    healthy = len(warnings) == 0
    return healthy, "; ".join(warnings) if warnings else "egress policy consistent"


def run_doctor(desktop: bool = False) -> int:
    """Execute `cherenkov doctor`.

    Returns exit code (0 = healthy, 1 = warnings/issues found).
    """
    print("=" * 64)
    print("  CHERENKOV doctor -- system health check")
    print("=" * 64)

    # ── Load effective config ────────────────────────────────────────────
    cfg = load_effective_config()
    effective = cfg.to_dict()

    print("\n  -- Effective Configuration --")
    print(f"  {'Key':<40} {'Value':<20} {'Source'}")
    print(f"  {'-'*40} {'-'*20} {'-'*20}")
    for key in sorted(effective):
        value = effective[key]
        provenance = cfg.get_with_provenance(key)
        source = provenance[-1][0] if provenance else "default"
        val_str = str(value)
        if len(val_str) > 36:
            val_str = val_str[:33] + "..."
        print(f"  {key:<40} {val_str:<20} {source}")

    # ── Environment checks ───────────────────────────────────────────────
    print("\n  -- Environment Health --")

    ollama_bin, ollama_bin_detail = check_ollama_binary()
    print(f"  {'ollama binary':<30} {'[OK]' if ollama_bin else '[NO]'}  {ollama_bin_detail}")

    if ollama_bin:
        ollama_daemon, ollama_daemon_detail = check_ollama_daemon()
        print(f"  {'ollama daemon':<30} {'[OK]' if ollama_daemon else '[NO]'}  {ollama_daemon_detail}")

    device = Config.detect_ollama_device()
    is_gpu = device == "GPU"
    print(f"  {'device':<30} {'[OK]' if is_gpu else '[WARN]'}  {device}")
    if not is_gpu:
        print(f"  {'':<30}  Warning: CPU mode - generation ~10x slower. GPU recommended.")

    small_model = cfg.get("substrate.tiers.small.model", "qwen2.5-coder:7b")
    deep_model = cfg.get("substrate.tiers.deep.model", "deepseek-r1:8b")
    if ollama_bin:
        for model in [small_model, deep_model]:
            ok, detail = check_ollama_model(model)
            print(f"  {'model ' + model:<30} {'[OK]' if ok else '[NO]'}  {detail}")

    node_ok, node_detail = check_node()
    print(f"  {'node':<30} {'[OK]' if node_ok else '[NO]'}  {node_detail}")

    pw_ok, pw_detail = check_npx_playwright()
    print(f"  {'playwright':<30} {'[OK]' if pw_ok else '[NO]'}  {pw_detail}")

    prism_ok, prism_detail = check_prism_docker()
    print(f"  {'prism (docker)':<30} {'[OK]' if prism_ok else '[NO]'}  {prism_detail}")

    if desktop:
        print("\n  -- Desktop Track (Track C) --")
        cargo_ok, cargo_detail = check_cargo()
        print(f"  {'cargo (rust)':<30} {'[OK]' if cargo_ok else '[NO]'}  {cargo_detail}")
        tauri_ok, tauri_detail = check_tauri_cli()
        print(f"  {'tauri-cli':<30} {'[OK]' if tauri_ok else '[NO]'}  {tauri_detail}")

    # ── Egress policy check ──────────────────────────────────────────────
    egress_ok, egress_detail = check_egress_blocked(cfg)
    print(f"\n  {'egress policy':<30} {'[OK]' if egress_ok else '[NO]'}  {egress_detail}")

    # ── Config errors ────────────────────────────────────────────────────
    config_errors = cfg.errors()
    if config_errors:
        print(f"\n  {'config validation':<30} [NO]  {len(config_errors)} issue(s)")
        for err in config_errors:
            print(f"  {'':<30}  - {err}")

    # ── Spec files ───────────────────────────────────────────────────────
    found_specs = cfg.autodetect_spec()
    if found_specs:
        print(f"\n  {'spec files':<30} [OK]  {len(found_specs)} found")
    else:
        print(f"\n  {'spec files':<30} [WARN]  none found (run `cherenkov init` or edit cherenkov.toml)")

    # ── Summary ──────────────────────────────────────────────────────────
    issues = 0
    if not ollama_bin:
        issues += 1
    if is_gpu:
        pass  # best case
    else:
        issues += 1  # CPU is a warning
    if not node_ok:
        issues += 1
    if not pw_ok:
        issues += 1
    if not prism_ok:
        issues += 1  # Docker not available
    if desktop:
        if not cargo_ok:
            issues += 1
        if not tauri_ok:
            issues += 1
    if config_errors:
        issues += len(config_errors)

    print(f"\n  {'-' * 60}")
    if issues == 0:
        print(f"  [OK] All systems healthy. Ready to run.")
    else:
        print(f"  [WARN] {issues} issue(s) detected - review the warnings above.")

    print()
    return 0 if issues == 0 else 1
