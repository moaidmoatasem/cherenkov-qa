#!/usr/bin/env python3
import argparse
import json
import sys

from validator import run_validation


def main():
    parser = argparse.ArgumentParser(description="CHERENKOV Engine — API Conformance Validator")
    parser.add_argument("--spec", required=True, help="Path to OpenAPI spec (JSON/YAML)")
    parser.add_argument("--target", required=True, help="Base URL of target API")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--strict", action="store_true", default=True, help="Require exact status match")

    args = parser.parse_args()

    try:
        result = run_validation(args.spec, args.target, strict=args.strict)
    except Exception as exc:
        result = {
            "passed": False,
            "divergences": [str(exc)],
            "summary": f"Fatal error: {exc}",
            "checks": [],
        }

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Summary: {result['summary']}")
        if result["divergences"]:
            print("Divergences:")
            for d in result["divergences"]:
                print(f"  - {d}")
        if result.get("checks"):
            print("Details:")
            for c in result["checks"]:
                status = "PASS" if c["passed"] else "FAIL"
                print(f"  [{status}] {c['method']} {c['path']} -> {c.get('actual', '?')}")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
