"""Synthetic data and test suite generation from OpenAPI schemas."""

from cherenkov.synthetic.generator import (
    GenerationStrategy,
    SyntheticDataGenerator,
    generate_from_schema,
    generate_from_spec,
)
from cherenkov.synthetic.runner import SyntheticDataReport, generate_for_endpoints
from cherenkov.synthetic.personas import (
    TesterPersona,
    DEFAULT_PERSONAS,
    PERSONA_BY_NAME,
    OperationContext,
    build_spec_contexts,
    HAPPY_PATH,
    ERROR_PATH,
    SECURITY_PROBER,
    SCHEMA_PEDANT,
    BOUNDARY_SEEKER,
)
from cherenkov.synthetic.merge import merge_suites
from cherenkov.synthetic.enricher import enrich_suite
from cherenkov.synthetic.suite_engine import SuiteEngine, SuiteEngineResult, PersonaRunResult

__all__ = [
    # data generator
    "GenerationStrategy",
    "SyntheticDataGenerator",
    "generate_from_schema",
    "generate_from_spec",
    "SyntheticDataReport",
    "generate_for_endpoints",
    # personas
    "TesterPersona",
    "DEFAULT_PERSONAS",
    "PERSONA_BY_NAME",
    "OperationContext",
    "build_spec_contexts",
    "HAPPY_PATH",
    "ERROR_PATH",
    "SECURITY_PROBER",
    "SCHEMA_PEDANT",
    "BOUNDARY_SEEKER",
    # pipeline
    "merge_suites",
    "enrich_suite",
    "SuiteEngine",
    "SuiteEngineResult",
    "PersonaRunResult",
]
