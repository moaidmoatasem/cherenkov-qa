from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


BUILT_IN_RULES: list[dict] = [
    {"path": "**/*.spec.ts", "rule": "Check Playwright assertions reference valid HTTP status codes and response body properties"},
    {"path": "**/*.spec.ts", "rule": "Verify generated test uses openapi-fetch client, not raw fetch or axios"},
    {"path": "**/*.spec.ts", "rule": "Check for null-safety on response body access (optional chaining or type guard)"},
    {"path": "**/*.spec.ts", "rule": "Ensure test descriptions are unique and descriptive"},
    {"path": "**/*.spec.ts", "rule": "Verify mock server URL is configurable, not hardcoded"},
]

DEFAULT_EXCLUDE = [
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
]

SUPPORTED_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".py", ".yaml", ".yml", ".json", ".md"}


def _brace_expand(pattern: str) -> list[str]:
    if "{" not in pattern or "}" not in pattern:
        return [pattern]
    start = pattern.index("{")
    end = pattern.index("}")
    prefix = pattern[:start]
    suffix = pattern[end + 1:]
    alternatives = pattern[start + 1:end].split(",")
    return [f"{prefix}{alt}{suffix}" for alt in alternatives]


def _glob_match(pattern: str, filepath: str) -> bool:
    import fnmatch
    patterns = _brace_expand(pattern)
    for pat in patterns:
        if "**" not in pat:
            if fnmatch.fnmatch(filepath, pat):
                return True
            continue
        parts = pat.split("**")
        if pat == "**":
            return True
        if len(parts) == 3 and not parts[0] and not parts[2]:
            middle = parts[1].strip("/")
            if middle in filepath.replace("\\", "/").split("/"):
                return True
            continue
        if len(parts) == 2:
            prefix = parts[0].rstrip("/")
            suffix = parts[1].lstrip("/")
            if not prefix:
                if fnmatch.fnmatch(filepath, suffix) or _glob_match(suffix, filepath):
                    return True
                continue
            if not suffix:
                if filepath.startswith(prefix):
                    return True
                continue
            if filepath.startswith(prefix) and filepath.endswith(suffix):
                inner = filepath[len(prefix):]
                inner = inner[:-len(suffix)] if suffix else inner
                inner = inner.lstrip("/")
                if "/" in inner or not inner:
                    return True
    return False


class OCRRuleEngine:
    def __init__(self, cli_rule_path: Optional[str] = None, repo_root: Optional[str] = None):
        self.repo_root = repo_root or os.getcwd()
        self._layers: list[dict] = []
        self._load_layers(cli_rule_path)

    def _load_layers(self, cli_rule_path: Optional[str] = None):
        layers = []

        cli_rules = self._load_rule_file(cli_rule_path)
        if cli_rules:
            layers.append(cli_rules)

        project_path = os.path.join(self.repo_root, ".opencodereview", "rule.json")
        project_rules = self._load_rule_file(project_path)
        if project_rules:
            layers.append(project_rules)

        global_path = os.path.join(Path.home(), ".opencodereview", "rule.json")
        global_rules = self._load_rule_file(str(global_path))
        if global_rules:
            layers.append(global_rules)

        layers.append({"rules": BUILT_IN_RULES})

        self._layers = layers

    def _load_rule_file(self, path: Optional[str]) -> Optional[dict]:
        if not path:
            return None
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def resolve_rule(self, filepath: str) -> Optional[str]:
        candidates = []
        try:
            candidates.append(os.path.relpath(filepath, self.repo_root))
        except (ValueError, OSError):
            pass
        candidates.append(os.path.basename(filepath))
        for layer in self._layers:
            for entry in layer.get("rules", []):
                pattern = entry.get("path", "")
                for candidate in candidates:
                    if _glob_match(pattern, candidate):
                        return entry.get("rule")
        return None

    def is_excluded(self, filepath: str, custom_exclude: Optional[list[str]] = None) -> bool:
        try:
            relative = os.path.relpath(filepath, self.repo_root)
        except ValueError:
            relative = os.path.basename(filepath)
        patterns = list(DEFAULT_EXCLUDE)
        if custom_exclude:
            patterns.extend(custom_exclude)
        for pattern in patterns:
            if _glob_match(pattern, relative):
                return True
        ext = os.path.splitext(filepath)[1]
        if ext and ext not in SUPPORTED_EXTENSIONS:
            return True
        return False
