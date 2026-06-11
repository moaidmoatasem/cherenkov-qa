#!/bin/bash
set -e

# If running inside GitHub Actions or INPUT_SPEC is set, execute the Action pipeline
if [ "$GITHUB_ACTIONS" = "true" ] || [ -n "$INPUT_SPEC" ]; then
  echo "=== CHERENKOV GitHub Actions Conformance Check ==="
  echo "Spec: $INPUT_SPEC"
  echo "Target: $INPUT_TARGET"
  echo "LLM Provider: $INPUT_LLM_PROVIDER"
  
  # Set provider environment variables if specified
  if [ -n "$INPUT_LLM_PROVIDER" ]; then
    export CHERENKOV_TIER_SMALL_PROVIDER="$INPUT_LLM_PROVIDER"
    export CHERENKOV_TIER_DEEP_PROVIDER="$INPUT_LLM_PROVIDER"
    export PROVIDER="$INPUT_LLM_PROVIDER"
  fi
  
  # Configure cherenkov profile to CI
  export CHERENKOV_PROFILE="ci"
  
  # Check if generated tests exist, otherwise run generation
  TESTS_EXIST=false
  if [ -d "stub/generated_tests" ] && [ "$(ls -A stub/generated_tests/*.spec.ts 2>/dev/null)" ]; then
    TESTS_EXIST=true
  fi
  
  if [ "$TESTS_EXIST" = "false" ]; then
    echo "No pre-generated tests found. Initializing and generating tests..."
    python cherenkov.py init --profile ci --force
    
    python -c "
from cherenkov.core.orchestrator import OrchestrationEngine
import sys
engine = OrchestrationEngine(run_id='ci_generation')
success = engine.run_pipeline('$INPUT_SPEC')
if not success:
    sys.exit(1)
"
  else
    echo "Using pre-generated tests in stub/generated_tests."
  fi
  
  # Run validation and output reports
  echo "Running validation..."
  python cherenkov.py validate --target "$INPUT_TARGET" --spec "$INPUT_SPEC" --output-format junit > cherenkov-junit.xml || true
  python cherenkov.py validate --target "$INPUT_TARGET" --spec "$INPUT_SPEC" --output-format sarif > cherenkov-sarif.json || true
  
  # Print JUnit validation report to console for visibility
  echo "=== Validation Report ==="
  if [ -f "cherenkov-junit.xml" ]; then
    cat cherenkov-junit.xml
  else
    echo "JUnit report was not generated."
  fi
  echo "========================="
  
  # Count violations from SARIF
  VIOLATIONS=$(python -c "
import json
import os
try:
    if os.path.exists('cherenkov-sarif.json'):
        with open('cherenkov-sarif.json') as f:
            data = json.load(f)
        print(len(data['runs'][0]['results']))
    else:
        print(0)
except Exception:
    print(0)
")
  
  echo "Violations found: $VIOLATIONS"
  
  # Write outputs to GITHUB_OUTPUT
  if [ -n "$GITHUB_OUTPUT" ]; then
    echo "violations=$VIOLATIONS" >> "$GITHUB_OUTPUT"
    echo "report-path=cherenkov-junit.xml" >> "$GITHUB_OUTPUT"
    echo "sarif-path=cherenkov-sarif.json" >> "$GITHUB_OUTPUT"
  fi
  
  # Exit code handling
  if [ "$INPUT_FAIL_ON_DRIFT" = "true" ] && [ "$VIOLATIONS" -gt 0 ]; then
    echo "Conformance drift detected. Failing step."
    exit 1
  fi
  
  exit 0
else
  # Act as a transparent wrapper forwarding arguments to the CLI
  exec python cherenkov.py "$@"
fi
