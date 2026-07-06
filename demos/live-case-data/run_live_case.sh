#!/bin/bash
set -e
cd /home/moaid/cherenkov-qa/demos/live-case-data

echo "Generating tests against JSONPlaceholder OpenAPI Spec..."
# We use the parent project's venv and cherenkov.py
../../.venv/bin/python ../../cherenkov.py generate --spec jsonplaceholder_spec.json --output-dir tests-jsonplaceholder/ --no-repair

echo "Validating generated tests against the REAL JSONPlaceholder API..."
../../.venv/bin/python ../../cherenkov.py validate --target https://jsonplaceholder.typicode.com --spec jsonplaceholder_spec.json

echo "Fully real Live case completed successfully!"
