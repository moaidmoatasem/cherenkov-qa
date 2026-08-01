#!/bin/bash
set -e
cd /home/moaid/cherenkov-qa/demos/live-case-data

echo "Generating tests against JSONPlaceholder OpenAPI Spec..."
# We use the parent project's venv and the canonical `python -m cherenkov` entry point
PYTHONPATH=../.. ../../.venv/bin/python -m cherenkov generate --spec jsonplaceholder_spec.json --output-dir tests-jsonplaceholder/ --no-repair

echo "Validating generated tests against the REAL JSONPlaceholder API..."
PYTHONPATH=../.. ../../.venv/bin/python -m cherenkov validate --target https://jsonplaceholder.typicode.com --spec jsonplaceholder_spec.json

echo "Fully real Live case completed successfully!"
