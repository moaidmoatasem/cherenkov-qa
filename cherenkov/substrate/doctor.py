from __future__ import annotations

import json

import click

from cherenkov.core.settings import get_settings
from cherenkov.core.devices import DeviceInfo, VLMTier


def _detect_ollama_vlm() -> dict:
    result = {"available": False, "model": "", "error": ""}
    try:
        import requests

        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            vlm_models = [
                m["name"]
                for m in models
                if "vl" in m["name"].lower() or "vision" in m["name"].lower()
            ]
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

        url = get_settings().VLM_LOCALAI_URL.rstrip("/")
        resp = requests.get(f"{url}/readyz", timeout=5)
        if resp.status_code == 200:
            result["available"] = True
            result["model"] = get_settings().VLM_LOCALAI_MODEL
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
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
@click.option("--evals", is_flag=True, help="Show latest eval report")
@click.option("--adversarial", is_flag=True, help="Show latest adversarial report")
def doctor(
    vlm: bool,
    localai: bool,
    device: bool,
    json_out: bool,
    evals: bool,
    adversarial: bool,
) -> None:
    report = {"device": {}, "vlm": {}, "localai": {}, "recommendations": []}  # type: ignore
    show_all = not vlm and not localai and not device

    if show_all or device:
        d = _detect_device()
        report["device"] = d
        if not json_out:
            click.echo("\nDevice Info")
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
            click.echo("\nOllama VLM")
            click.echo(f"{'=' * 40}")
            click.echo(f"  Available:   {'Yes' if ollama['available'] else 'No'}")
            click.echo(f"  Model:       {ollama['model'] or 'N/A'}")
            if ollama["error"]:
                click.echo(f"  Error:       {ollama['error']}")

    if show_all or localai:
        lai = _detect_localai_vlm()
        report["localai"] = lai
        if not json_out:
            click.echo("\nLocalAI VLM")
            click.echo(f"{'=' * 40}")
            click.echo(f"  URL:         {get_settings().VLM_LOCALAI_URL}")
            click.echo(f"  Available:   {'Yes' if lai['available'] else 'No'}")
            click.echo(f"  Model:       {lai['model'] or 'N/A'}")
            if lai["error"]:
                click.echo(f"  Error:       {lai['error']}")

    if show_all or device:
        recommendations = []
        d = report["device"]  # type: ignore
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
                click.echo("\nRecommendations")
                click.echo(f"{'=' * 40}")
                for rec in report["recommendations"]:
                    click.echo(f"  - {rec}")

    if show_all or evals:
        try:
            from cherenkov.evals.store import EvalStore

            store = EvalStore()
            latest = store.latest()
            if latest:
                report["latest_evals"] = latest
                if not json_out:
                    click.echo("\nLatest Eval Report")
                    click.echo(f"{'=' * 40}")
                    click.echo(f"  Timestamp:   {latest['timestamp']}")
                    click.echo(f"  Model:       {latest['model']}")
                    click.echo(f"  Pass rate:   {latest['pass_rate']:.1%}")
                    click.echo(
                        f"  Scenarios:   {latest['passed']}/{latest['total']} passed"
                    )
                    for metric, avg in latest.get("metrics", {}).items():
                        click.echo(f"  {metric:20s} {avg:.2f}")
            else:
                report["latest_evals"] = None
                if not json_out:
                    click.echo(
                        "\nNo eval reports found. Run the generator pipeline first."
                    )
        except Exception as e:
            report["latest_evals"] = {"error": str(e)}

    if show_all or adversarial:
        try:
            from pathlib import Path
            import json as json_module

            adv_path = Path(".cherenkov/adversarial_report.json")
            if adv_path.exists():
                latest = json_module.loads(adv_path.read_text())
                report["latest_adversarial"] = latest
                if not json_out:
                    click.echo("\nLatest Adversarial Report")
                    click.echo(f"{'=' * 40}")
                    click.echo(f"  Timestamp:   {latest['timestamp']}")
                    click.echo(f"  Model:       {latest['model']}")
                    click.echo(f"  Pass rate:   {latest['pass_rate']:.1%}")
                    click.echo(f"  Total:       {latest['total_payloads']}")
                    click.echo(f"  Detected:    {latest['detected']}")
                    click.echo(f"  Critical:    {latest['critical']}")
                    click.echo(
                        f"  Garak:       {'available' if latest.get('garak_available') else 'not installed'}"
                    )
            else:
                report["latest_adversarial"] = None
                if not json_out:
                    click.echo(
                        "\nNo adversarial reports found. Run adversarial tests first."
                    )
        except Exception as e:
            report["latest_adversarial"] = {"error": str(e)}

    if json_out:
        click.echo(json.dumps(report, indent=2))
