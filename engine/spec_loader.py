import json
import sys

try:
    import yaml
except ImportError:
    yaml = None


def load_spec(path: str) -> dict:
    with open(path, "r") as f:
        raw = f.read()

    if path.endswith((".yaml", ".yml")):
        if yaml is None:
            print("ERROR: pyyaml required for YAML specs", file=sys.stderr)
            sys.exit(2)
        return yaml.safe_load(raw)
    return json.loads(raw)


def extract_routes(spec: dict) -> dict:
    routes = {}
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                operation = methods[method]
                expected_statuses = set()
                for status_code in operation.get("responses", {}):
                    try:
                        expected_statuses.add(int(status_code))
                    except ValueError:
                        pass
                routes[(method.upper(), path)] = expected_statuses
    return routes
