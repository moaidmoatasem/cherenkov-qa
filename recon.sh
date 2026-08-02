#!/usr/bin/env bash
cd "$HOME/cherenkov-qa" || exit 1
python3 -c "import click; print('click', click.__version__)" 2>&1 | tail -2
echo "===docs-parity check==="
python3 scripts/check_cli_docs.py 2>&1 | tail -50
