"""
scripts/fetch_corpus_specs.py — Download and validate real-world OpenAPI 3.x specs into specs/corpus/
"""
import json
import os
import urllib.request
import yaml
from pathlib import Path

SPECS_CONFIG = {
    "stripe.json": [
        "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
        "https://api.apis.guru/v2/specs/stripe.com/2022-11-15/openapi.json",
        "stripe_spec.json",
        "demos/live-case-data/stripe_spec.json"
    ],
    "github.json": [
        "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
        "https://api.apis.guru/v2/specs/github.com/api.github.com/1.1.4/openapi.json"
    ],
    "twilio.json": [
        "https://raw.githubusercontent.com/twilio/twilio-oai/main/json/twilio_rest_v2010.json",
        "https://api.apis.guru/v2/specs/twilio.com/api/1.42.0/openapi.json"
    ],
    "kubernetes.json": [
        "https://raw.githubusercontent.com/kubernetes/kubernetes/master/api/openapi-spec/swagger.json",
        "https://api.apis.guru/v2/specs/kubernetes.io/unversioned/swagger.json"
    ],
    "openai.yaml": [
        "https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml",
        "https://api.apis.guru/v2/specs/openai.com/1.2.0/openapi.json"
    ],
    "petstore.json": [
        "https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.json",
        "https://raw.githubusercontent.com/swagger-api/swagger-petstore/master/src/main/resources/openapi.yaml",
        "docs/evidence/petstore_spec.json"
    ],
    "slack.yaml": [
        "https://raw.githubusercontent.com/APIs-guru/openapi-directory/main/APIs/slack.com/1.7.0/openapi.yaml",
        "https://api.apis.guru/v2/specs/slack.com/1.7.0/openapi.json"
    ],
    "box.json": [
        "https://raw.githubusercontent.com/box/box-openapi/main/openapi.json",
        "https://api.apis.guru/v2/specs/box.com/2.0.0/openapi.json"
    ],
    "sendgrid.json": [
        "https://raw.githubusercontent.com/sendgrid/sendgrid-oai/main/oai.json",
        "https://api.apis.guru/v2/specs/sendgrid.com/1.0.0/openapi.json"
    ],
    "digitalocean.yaml": [
        "https://raw.githubusercontent.com/digitalocean/openapi/main/specification/DigitalOcean-public.v2.yaml",
        "https://api.apis.guru/v2/specs/digitalocean.com/2.0/openapi.json"
    ],
}

def fetch_and_save():
    """Fetch OpenAPI specs from configured URL/local sources into specs/corpus/.

    Returns:
        None.

    Raises:
        RuntimeError: If any spec fails to download or save as valid spec file.
    """
    corpus_dir = Path("specs/corpus")
    corpus_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CherenkovCorpusAcquisition/1.0"}

    for filename, sources in SPECS_CONFIG.items():
        out_path = corpus_dir / filename
        name_stem = Path(filename).stem
        downloaded = False

        for source in sources:
            if source.startswith("http://") or source.startswith("https://"):
                print(f"Fetching {filename} from {source}...")
                try:
                    req = urllib.request.Request(source, headers=headers)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        content = resp.read()
                        # If it's yaml target and fetched json (or vice versa), parse and serialize properly
                        if filename.endswith(".yaml") or filename.endswith(".yml"):
                            try:
                                data = yaml.safe_load(content.decode("utf-8"))
                            except Exception:
                                data = json.loads(content.decode("utf-8"))
                            with open(out_path, "w", encoding="utf-8") as f:
                                yaml.dump(data, f, sort_keys=False)
                        else:
                            try:
                                data = json.loads(content.decode("utf-8"))
                            except Exception:
                                data = yaml.safe_load(content.decode("utf-8"))
                            with open(out_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2)
                        downloaded = True
                        print(f"  Successfully downloaded from {source}")
                        break
                except Exception as e:
                    print(f"  Failed fetching from {source}: {e}")
            else:
                local_p = Path(source)
                if local_p.exists():
                    print(f"Loading local file for {filename} from {source}...")
                    with open(local_p, "r", encoding="utf-8") as f:
                        if source.endswith(".yaml") or source.endswith(".yml"):
                            data = yaml.safe_load(f)
                        else:
                            data = json.load(f)
                    if filename.endswith(".yaml") or filename.endswith(".yml"):
                        with open(out_path, "w", encoding="utf-8") as f:
                            yaml.dump(data, f, sort_keys=False)
                    else:
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    downloaded = True
                    break

        if not downloaded:
            # Fallback to converting existing json in corpus if present
            existing_json = corpus_dir / f"{name_stem}.json"
            existing_yaml = corpus_dir / f"{name_stem}.yaml"
            if existing_json.exists() and filename.endswith(".yaml"):
                print(f"Converting existing {existing_json.name} to {filename}...")
                with open(existing_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(out_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, sort_keys=False)
                downloaded = True
            elif existing_yaml.exists() and filename.endswith(".json"):
                print(f"Converting existing {existing_yaml.name} to {filename}...")
                with open(existing_yaml, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                downloaded = True

        if not out_path.exists() or os.path.getsize(out_path) == 0:
            raise RuntimeError(f"Failed to acquire valid spec file: {out_path}")

        # Validate parsing
        with open(out_path, "r", encoding="utf-8") as f:
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        paths = data.get("paths", {})
        total_ops = 0
        for p, pitem in paths.items():
            if isinstance(pitem, dict):
                for m, op in pitem.items():
                    if m.lower() in {"get", "post", "put", "patch", "delete", "options", "head", "trace"} and isinstance(op, dict):
                        total_ops += 1

        version = data.get("openapi") or data.get("swagger") or "3.0.0"
        title = data.get("info", {}).get("title", name_stem)

        summary.append({
            "filename": filename,
            "title": title,
            "version": version,
            "paths_count": len(paths),
            "endpoints_count": total_ops,
            "file": str(out_path),
            "size_bytes": os.path.getsize(out_path)
        })
        print(f"  Verified {filename} ({os.path.getsize(out_path):,} bytes, {total_ops} endpoints, OpenAPI/Swagger {version})")

    print("\n--- Spec Corpus Acquisition Summary ---")
    for s in summary:
        print(f"[{s['filename']}] Title: {s['title']} | Version: {s['version']} | Endpoints: {s['endpoints_count']} | Size: {s['size_bytes']:,} B")

if __name__ == "__main__":
    fetch_and_save()
