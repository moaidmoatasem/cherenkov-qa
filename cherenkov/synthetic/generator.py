"""SynthGen — generates synthetic test data from OpenAPI schemas.

Two strategies:
- RANDOM: values randomly generated per type (UUID strings, random ints, etc.)
- LLM: uses local Ollama to generate semantically realistic values for each field.
"""

from __future__ import annotations

import enum
import json
import random
import string
import uuid
from pathlib import Path
from typing import Any


class GenerationStrategy(enum.Enum):
    RANDOM = "random"
    LLM = "llm"


class SyntheticDataGenerator:
    """Generates synthetic values from OpenAPI schema definitions.

    Two strategies:
    - RANDOM: values randomly generated per type with semantic heuristics (UUID, email, etc.)
    - LLM: uses local Ollama to generate semantically realistic values for each field.
    """

    def __init__(self, strategy: GenerationStrategy = GenerationStrategy.RANDOM):
        self.strategy = strategy
        self._seed: dict[str, Any] = {}

    def seed(self, overrides: dict[str, Any]) -> None:
        """Seed specific field values (use in tests to pin determinism)."""
        self._seed.update(overrides)

    def generate(self, schema: dict[str, Any], field_path: str = "") -> Any:
        """Generate a synthetic value matching the given JSON Schema."""
        if field_path in self._seed:
            return self._seed[field_path]

        # Dispatch to LLM or random strategy
        if self.strategy == GenerationStrategy.LLM:
            return self._generate_with_llm(schema, field_path)

        schema_type = schema.get("type", "string")

        if schema_type == "object":
            return self._generate_object(schema, field_path)
        elif schema_type == "array":
            return self._generate_array(schema, field_path)
        elif schema_type in ("integer", "number"):
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return self._generate_boolean()
        elif schema_type == "string":
            return self._generate_string(schema, field_path)
        else:
            return "synthetic_value"

    def _generate_with_llm(self, schema: dict[str, Any], field_path: str) -> Any:
        """Generate a value using Ollama for semantically realistic output."""
        try:
            from cherenkov.ai import get_client
            from cherenkov.ai.ollama_client import strip_think

            client = get_client()
            schema_type = schema.get("type", "string")
            enum_vals = schema.get("enum")
            field_hint = field_path.split(".")[-1] if field_path else "value"

            prompt_parts = [
                f"Generate a single realistic {schema_type} value for field '{field_hint}'.",
            ]
            if enum_vals:
                prompt_parts.append(f"Choose from: {enum_vals}")
            if schema_type in ("integer", "number"):
                min_v = schema.get("minimum", 0)
                max_v = schema.get("maximum", 100000)
                prompt_parts.append(f"Range: [{min_v}, {max_v}]")
            if schema_type == "string":
                min_l = schema.get("minLength", 1)
                max_l = schema.get("maxLength", 255)
                pattern = schema.get("pattern")
                prompt_parts.append(f"Length: {min_l}-{max_l} chars")
                if pattern:
                    prompt_parts.append(f"Pattern: {pattern}")
            prompt_parts.append("Respond with ONLY the value, no explanation.")

            raw = client.complete_code(
                system_prompt="You generate realistic test data values. Return ONLY the value.",
                user_prompt="\n".join(prompt_parts),
                model="qwen2.5-coder:7b",
                temperature=0.7,
                run_id="synthetic-llm",
            )
            cleaned = strip_think(raw).strip()

            if schema_type == "integer":
                return int(cleaned)
            elif schema_type == "number":
                return float(cleaned)
            elif schema_type == "boolean":
                return cleaned.lower() in ("true", "yes", "1")
            else:
                return cleaned
        except Exception:
            return self._generate_random(schema, field_path)

    def _generate_random(self, schema: dict[str, Any], field_path: str) -> Any:
        """Fallback random generation (same as RANDOM strategy)."""
        schema_type = schema.get("type", "string")
        if schema_type == "object":
            return self._generate_object(schema, field_path)
        elif schema_type == "array":
            return self._generate_array(schema, field_path)
        elif schema_type in ("integer", "number"):
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return self._generate_boolean()
        elif schema_type == "string":
            return self._generate_string(schema, field_path)
        return "synthetic_value"

    def _generate_object(
        self, schema: dict[str, Any], field_path: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        properties = schema.get("properties", {})
        set(schema.get("required", []))

        for prop_name, prop_schema in properties.items():
            child_path = f"{field_path}.{prop_name}" if field_path else prop_name
            result[prop_name] = self.generate(prop_schema, child_path)

        return result

    def _generate_array(self, schema: dict[str, Any], field_path: str) -> list[Any]:
        min_items = schema.get("minItems", 1)
        max_items = schema.get("maxItems", min(min_items + 2, 5))
        count = random.randint(min_items, max_items)
        items_schema = schema.get("items", {})

        return [self.generate(items_schema, f"{field_path}[{i}]") for i in range(count)]

    def _generate_number(self, schema: dict[str, Any]) -> int | float:
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", minimum + 10000)
        if schema.get("type") == "integer":
            return random.randint(int(minimum), int(maximum))
        return round(random.uniform(float(minimum), float(maximum)), 2)

    def _generate_boolean(self) -> bool:
        return random.choice([True, False])

    def _generate_string(self, schema: dict[str, Any], field_path: str) -> str:
        field_lower = field_path.lower()

        # Check enum constraints
        enum_vals = schema.get("enum")
        if enum_vals:
            return str(random.choice(enum_vals))

        # Semantic generation based on field name heuristics
        if any(kw in field_lower for kw in ("uuid", "guid", "id")):
            return str(uuid.uuid4())
        if any(kw in field_lower for kw in ("email", "e-mail")):
            return f"user{random.randint(1, 9999)}@example.com"
        if any(kw in field_lower for kw in ("url", "uri", "link")):
            return f"https://example.com/resource/{random.randint(1, 999)}"
        if any(kw in field_lower for kw in ("date", "time")):
            return f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        if any(kw in field_lower for kw in ("phone", "tel")):
            return (
                f"+1-555-{random.randint(100,999):03d}-{random.randint(1000,9999):04d}"
            )
        if any(kw in field_lower for kw in ("name", "title", "label")):
            return random.choice(["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"])
        if any(kw in field_lower for kw in ("address", "city", "street")):
            return random.choice(["123 Main St", "456 Oak Ave", "789 Pine Rd"])
        if any(kw in field_lower for kw in ("password", "secret", "token")):
            return "s3cur3-P@ss!"

        # Default: random alphanumeric string
        pattern = schema.get("pattern")
        if pattern and pattern == r"^\d{10}$":
            return "".join(random.choices(string.digits, k=10))

        min_length = schema.get("minLength", 1)
        max_length = schema.get("maxLength", min_length + 20)
        length = random.randint(min_length, min(min_length + 15, max_length))
        return "".join(random.choices(string.ascii_lowercase, k=length))


def generate_from_schema(
    schema: dict[str, Any],
    strategy: GenerationStrategy = GenerationStrategy.RANDOM,
    overrides: dict[str, Any] | None = None,
) -> Any:
    """One-shot synthetic data generation from a JSON Schema."""
    gen = SyntheticDataGenerator(strategy)
    if overrides:
        gen.seed(overrides)
    return gen.generate(schema)


def generate_from_spec(
    spec_path: str,
    strategy: GenerationStrategy = GenerationStrategy.RANDOM,
    max_endpoints: int = 5,
) -> dict[str, Any]:
    """Generate synthetic request/response data for endpoints in an OpenAPI spec."""
    gen = SyntheticDataGenerator(strategy)
    spec = _load_spec(spec_path)
    paths = spec.get("paths", {})
    result: dict[str, Any] = {}

    endpoints_processed = 0
    for path, path_item in paths.items():
        if endpoints_processed >= max_endpoints:
            break
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in path_item:
                continue
            operation = path_item[method]
            key = f"{method.upper()} {path}"
            result[key] = {}

            # Generate request body
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if schema:
                    result[key]["request_body"] = gen.generate(schema)

            # Generate response examples
            responses = operation.get("responses", {})
            for status_code, response_def in responses.items():
                resp_content = response_def.get("content", {})
                if "application/json" in resp_content:
                    schema = resp_content["application/json"].get("schema", {})
                    if schema:
                        result[key][f"response_{status_code}"] = gen.generate(schema)

            endpoints_processed += 1

    return result


def _load_spec(spec_path: str) -> dict[str, Any]:
    """Load OpenAPI spec from file."""
    path = Path(spec_path)
    content = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml

        return yaml.safe_load(content)
    return json.loads(content)
