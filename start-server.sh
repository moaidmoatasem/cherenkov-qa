#!/bin/bash
export PATH=/home/moaid/.local/bin:/home/moaid/.nvm/versions/node/v22.23.0/bin:$PATH
export CHERENKOV_RATE_LIMIT_RPS=500
export CHERENKOV_RATE_LIMIT_BURST=1000
cd ~/cherenkov-qa
exec .venv/bin/python -m cherenkov review --demo --port 8000
