"""
CHERENKOV stages/enrich.py — RESTGPT-inspired spec enhancement preprocessor.
Authority: v3.1 + delta.

Extracts constraint rules and example values from OpenAPI natural-language
descriptions, examples, defaults, enums, and patterns. Enriched context is
injected into the generator prompt to improve value generation accuracy.

Research basis: LlamaRestTest (FSE 2025, arXiv 2501.08598) proved that
richer spec context — extracted via RESTGPT-style preprocessing — produces
59-194% more branch coverage vs baseline tools. RESTGPT (arXiv 2312.00894)
achieved 97% rule extraction precision and 73% valid-value generation
accuracy (vs 17% for the ARTE baseline).
"""
from __future__ import annotations

import re
from typing import Any

from cherenkov.core.errors import get_logger


# Phrases that typically introduce a constraint in natural language
_CONSTRAINT_PHRASES = [
    r"must\s+be",
    r"should\s+be",
    r"cannot\s+be",
    r"must\s+not",
    r"is\s+required",
    r"can\s+only",
    r"only\s+(?:accepts?|allows?)",
    r"must\s+match",
    r"must\s+contain",
    r"must\s+have",
    r"is\s+(?:always|never)",
    r"between\s+\d+\s+and\s+\d+",
    r"at\s+(?:least|most)\s+\d+",
    r"minimum\s+(?:length|value|count)",
    r"maximum\s+(?:length|value|count)",
    r"valid\s+(?:values?|options?|choices?)",
    r"one\s+of\b",
    r"(?:upper|lower)case",
    r"alphanumeric",
    r"ISO\s*\d+",
    r"RFC\s*\d+",
    r"e\.g\.",
    r"for\s+example",
    r"such\s+as",
]
_CONSTRAINT_RE = re.compile("|".join(_CONSTRAINT_PHRASES), re.IGNORECASE)


def _extract_constraint_sentences(text: str) -> list[str]:
    """Pull sentences that contain a constraint-language phrase."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if _CONSTRAINT_RE.search(s)]


def _collect_examples(schema: dict[str, Any]) -> list[Any]:
    """Collect concrete example values from a schema node."""
    examples: list[Any] = []
    if "example" in schema:
        examples.append(schema["example"])
    if "examples" in schema and isinstance(schema["examples"], dict):
        for ex in schema["examples"].values():
            if isinstance(ex, dict) and "value" in ex:
                examples.append(ex["value"])
            else:
                examples.append(ex)
    if "default" in schema:
        examples.append(schema["default"])
    if "enum" in schema and isinstance(schema["enum"], list):
        examples.extend(schema["enum"][:3])  # cap enum list
    return examples


def _collect_schema_hints(schema: dict[str, Any]) -> list[str]:
    """Collect pattern/format/range constraints as short human-readable hints."""
    hints: list[str] = []
    if "pattern" in schema:
        hints.append(f"must match regex: {schema['pattern']}")
    if "format" in schema:
        hints.append(f"format: {schema['format']}")
    if "minimum" in schema:
        hints.append(f"minimum value: {schema['minimum']}")
    if "maximum" in schema:
        hints.append(f"maximum value: {schema['maximum']}")
    if "minLength" in schema:
        hints.append(f"minimum length: {schema['minLength']}")
    if "maxLength" in schema:
        hints.append(f"maximum length: {schema['maxLength']}")
    if "exclusiveMinimum" in schema:
        hints.append(f"exclusive minimum: {schema['exclusiveMinimum']}")
    if "exclusiveMaximum" in schema:
        hints.append(f"exclusive maximum: {schema['exclusiveMaximum']}")
    return hints


class SpecRules:
    """Enrichment payload for one operation: extracted rules + concrete examples."""

    def __init__(self) -> None:
        self.rules: list[str] = []                # constraint sentences from descriptions
        self.param_examples: dict[str, Any] = {}  # param name → example value
        self.body_examples: dict[str, Any] = {}   # field name → example value
        self.body_hints: dict[str, list[str]] = {} # field name → pattern/format hints

    def render_prompt_block(self) -> str:
        """Render as a compact block suitable for appending to the generator prompt."""
        lines: list[str] = []
        if self.rules:
            lines.append("SPEC RULES (extracted from descriptions):")
            for r in self.rules[:8]:  # cap to avoid context blowup
                lines.append(f"  - {r}")
        if self.param_examples:
            lines.append("EXAMPLE PARAMETER VALUES:")
            for k, v in list(self.param_examples.items())[:6]:
                lines.append(f"  {k}: {v!r}")
        if self.body_examples:
            lines.append("EXAMPLE REQUEST BODY FIELD VALUES:")
            for k, v in list(self.body_examples.items())[:10]:
                lines.append(f"  {k}: {v!r}")
        if self.body_hints:
            lines.append("FIELD CONSTRAINTS:")
            for k, hints in list(self.body_hints.items())[:6]:
                if hints:
                    lines.append(f"  {k}: {', '.join(hints)}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return not (
            self.rules or self.param_examples or self.body_examples or self.body_hints
        )


class SpecEnrichStage:
    """
    RESTGPT-inspired preprocessing stage: mines OpenAPI descriptions, examples,
    defaults, enums, and schema constraints to produce a SpecRules payload that
    the GenerateStage injects into the LLM prompt.

    Operates purely on the already-parsed operation dict + resolved schemas from
    IngestStage — no additional I/O, no LLM calls.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.log = get_logger("ENRICH", run_id)

    def enrich(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        schemas: dict[str, Any],
    ) -> SpecRules:
        """
        Mine all available natural-language and structural spec context for an
        operation and return a SpecRules payload.

        Args:
            path:      URL path, e.g. "/users/{id}"
            method:    HTTP method, e.g. "post"
            operation: The OpenAPI operation object from the spec.
            schemas:   Depth-limited resolved component schemas from IngestStage.

        Returns:
            SpecRules with rules, param_examples, body_examples, body_hints.
        """
        result = SpecRules()

        # 1. Extract constraint sentences from operation-level prose
        for field in ("summary", "description"):
            text = operation.get(field, "")
            if text:
                result.rules.extend(_extract_constraint_sentences(str(text)))

        # 2. Parameters: descriptions + examples + schema hints
        for param in operation.get("parameters", []):
            if not isinstance(param, dict):
                continue
            name = param.get("name", "")
            schema = param.get("schema") or {}

            if isinstance(schema, dict) and "$ref" in schema:
                ref_name = schema["$ref"].split("/")[-1]
                schema = schemas.get(ref_name, schema)

            # Constraint sentences from param description
            desc = param.get("description", "")
            if desc:
                result.rules.extend(_extract_constraint_sentences(str(desc)))

            # Concrete example from schema or param-level example
            examples = _collect_examples(schema)
            if not examples and "example" in param:
                examples = [param["example"]]
            if examples and name:
                result.param_examples[name] = examples[0]

            # Schema constraints as hints
            hints = _collect_schema_hints(schema)
            if hints and name:
                result.body_hints.setdefault(name, []).extend(hints)

        # 3. Request body: descriptions + field examples + schema hints
        req_body = operation.get("requestBody", {})
        if req_body:
            content = req_body.get("content", {})
            media = (
                content.get("application/json")
                or content.get("multipart/form-data")
                or {}
            )
            body_schema = media.get("schema", {}) if media else {}

            if isinstance(body_schema, dict) and "$ref" in body_schema:
                ref_name = body_schema["$ref"].split("/")[-1]
                body_schema = schemas.get(ref_name, body_schema)

            if isinstance(body_schema, dict):
                body_desc = body_schema.get("description", "")
                if body_desc:
                    result.rules.extend(_extract_constraint_sentences(str(body_desc)))

                for prop, prop_schema in body_schema.get("properties", {}).items():
                    if not isinstance(prop_schema, dict):
                        continue

                    if "$ref" in prop_schema:
                        ref_name = prop_schema["$ref"].split("/")[-1]
                        prop_schema = schemas.get(ref_name, prop_schema)

                    prop_desc = prop_schema.get("description", "")
                    if prop_desc:
                        result.rules.extend(_extract_constraint_sentences(str(prop_desc)))

                    examples = _collect_examples(prop_schema)
                    if examples:
                        result.body_examples[prop] = examples[0]

                    hints = _collect_schema_hints(prop_schema)
                    if hints:
                        result.body_hints.setdefault(prop, []).extend(hints)

        # Deduplicate rules while preserving encounter order
        seen: set[str] = set()
        unique_rules: list[str] = []
        for r in result.rules:
            key = r.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_rules.append(r)
        result.rules = unique_rules

        self.log.info(
            "enrichment complete",
            endpoint=f"{method.upper()} {path}",
            rules=len(result.rules),
            param_examples=len(result.param_examples),
            body_examples=len(result.body_examples),
            body_hints=len(result.body_hints),
        )
        return result
