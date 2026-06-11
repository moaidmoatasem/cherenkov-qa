from __future__ import annotations

import json
import sys

import click

from cherenkov.core.config import Config
from cherenkov.core.devices import DeviceInfo, VLMTier


def _detect_ollama_vlm() -> dict:
    result = {"available": False, "model": "", "error": ""}
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            vlm_models = [m["name"] for m in models if "vl" in m["name"].lower() or "vision" in m["name"].lower()]
            if vlm_models:
                result["available"] = True
                result["model"] = vlm_models[0]
            else:
                result["model"] = "no VLM models found"
        else:
            result["error"] = f"Ollama returned status {resp.status_code}"
    except Exception as e:
        result["error"] = str(e)
    return result


def _detect_localai_vlm() -> dict:
    result = {"available": False, "model": "", "error": ""}
    try:
        import requests
        url = Config.VLM_LOCALAI_URL.rstrip("/")
        resp = requests.get(f"{url}/readyz", timeout=5)
        if resp.status_code == 200:
            result["available"] = True
            result["model"] = Config.VLM_LOCALAI_MODEL
        else:
            result["error"] = f"LocalAI returned status {resp.status_code}"
    except Exception as e:
        result["error"] = str(e)
    return result


def _detect_device() -> dict:
    info = DeviceInfo()
    return {
        "device_class": info.device_class.value,
        "vlm_tier": info.vlm_tier.value,
        "has_gpu": info.has_gpu,
        "has_docker": info.has_docker,
        "os_name": info.os_name,
        "cpu_count": info.cpu_count,
        "memory_gb": info.memory_gb,
    }


@click.command(name="doctor")
@click.option("--vlm", is_flag=True, help="Check VLM capabilities")
@click.option("--localai", is_flag=True, help="Check LocalAI availability")
@click.option("--device", is_flag=True, help="Show device info")
@click.option("--desktop", is_flag=True, help="Check Rust and Tauri CLI dependencies")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
def doctor(vlm: bool, localai: bool, device: bool, desktop: bool, json_out: bool) -> None:
    report = {"device": {}, "vlm": {}, "localai": {}, "desktop": {}, "recommendations": []}
    show_all = not vlm and not localai and not device and not desktop

    if show_all or device:
        d = _detect_device()
        report["device"] = d
        if not json_out:
            click.echo(f"\nDevice Info")
            click.echo(f"{'=' * 40}")
            click.echo(f"  Class:       {d['device_class']}")
            click.echo(f"  VLM Tier:    {d['vlm_tier']}")
            click.echo(f"  GPU:         {'Yes' if d['has_gpu'] else 'No'}")
            click.echo(f"  Docker:      {'Yes' if d['has_docker'] else 'No'}")
            click.echo(f"  OS:          {d['os_name']}")
            click.echo(f"  CPUs:        {d['cpu_count']}")
            click.echo(f"  Memory:      {d['memory_gb']} GB")

    if show_all or vlm:
        ollama = _detect_ollama_vlm()
        report["vlm"] = ollama
        if not json_out:
            click.echo(f"\nOllama VLM")
            click.echo(f"{'=' * 40}")
            click.echo(f"  Available:   {'Yes' if ollama['available'] else 'No'}")
            click.echo(f"  Model:       {ollama['model'] or 'N/A'}")
            if ollama["error"]:
                click.echo(f"  Error:       {ollama['error']}")

    if show_all or localai:
        lai = _detect_localai_vlm()
        report["localai"] = lai
        if not json_out:
            click.echo(f"\nLocalAI VLM")
            click.echo(f"{'=' * 40}")
            click.echo(f"  URL:         {Config.VLM_LOCALAI_URL}")
            click.echo(f"  Available:   {'Yes' if lai['available'] else 'No'}")
            click.echo(f"  Model:       {lai['model'] or 'N/A'}")
            if lai["error"]:
                click.echo(f"  Error:       {lai['error']}")

    if show_all or device:
        recommendations = []
        d = report["device"]
        if d["vlm_tier"] == VLMTier.LOCAL.value:
            recommendations.append("localai" if d["has_docker"] else "ollama")
        elif d["vlm_tier"] == VLMTier.CLOUD.value:
            recommendations.append("openai")
        if recommendations:
            report["recommendations"] = [
                f"Use '{r}' as your VLM provider (CHERENKOV_TIER_VISION_PROVIDER={r})"
                for r in recommendations
            ]
            if not json_out:
                click.echo(f"\nRecommendations")
                click.echo(f"{'=' * 40}")
                for rec in report["recommendations"]:
                    click.echo(f"  - {rec}")

    if show_all or desktop:
        import shutil
        import subprocess
        cargo_path = shutil.which("cargo")
        has_cargo = cargo_path is not None
        cargo_ver = "not found"
        if has_cargo:
            try:
                res = subprocess.run(["cargo", "--version"], capture_output=True, text=True, timeout=5)
                cargo_ver = res.stdout.strip()
            except Exception:
                cargo_ver = "error running cargo"

        tauri_path = shutil.which("cargo-tauri") or shutil.which("tauri")
        has_tauri = tauri_path is not None
        tauri_ver = "not found"
        if has_tauri:
            try:
                cmd = ["cargo", "tauri", "--version"] if tauri_path.endswith("cargo-tauri") else ["tauri", "--version"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                tauri_ver = res.stdout.strip()
            except Exception:
                tauri_ver = "error running tauri-cli"

        report["desktop"] = {
            "cargo_available": has_cargo,
            "cargo_version": cargo_ver,
            "tauri_cli_available": has_tauri,
            "tauri_cli_version": tauri_ver,
        }

        if not json_out:
            click.echo(f"\nDesktop Host Environment")
            click.echo(f"{'=' * 40}")
            click.echo(f"  Cargo:       {'Yes' if has_cargo else 'No'} ({cargo_ver})")
            click.echo(f"  Tauri CLI:   {'Yes' if has_tauri else 'No'} ({tauri_ver})")

    if json_out:
        click.echo(json.dumps(report, indent=2))
