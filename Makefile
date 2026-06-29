# CHERENKOV-QA — Makefile
# Local developer commands for docs, testing, and common workflows.
#
# Usage:
#   make docs-serve        Start local docs preview server
#   make docs-build        Build docs site (strict mode)
#   make docs-lint         Lint all public docs markdown
#   make docs-check-clean  Check docs for leaked internal tokens
#   make docs-gen-cli      Auto-generate CLI reference from cherenkov --help
#   make test              Run the full test suite
#   make doctor            Run environment health check
#
# Prerequisites: Python 3.10+, virtualenv at .venv/
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   pip install -r docs-site/docs-requirements.txt

.PHONY: help docs-serve docs-build docs-lint docs-check-clean docs-gen-cli \
        test doctor docs-version-list docs-deploy-dev

VENV := .venv
PYTHON := $(VENV)/bin/python3
MKDOCS := $(VENV)/bin/mkdocs
MIKE := $(VENV)/bin/mike
DOCS_CFG := docs-site/mkdocs.yml

##@ Help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Documentation — Local Dev
docs-serve: ## Start live-reload local docs preview (http://localhost:8000)
	@echo "→ Starting docs preview server at http://localhost:8000"
	@cd docs-site && $(MKDOCS) serve --dev-addr 0.0.0.0:8000 --config-file mkdocs.yml

docs-build: ## Build docs site in strict mode (fails on broken links)
	@echo "→ Building docs (strict mode)..."
	@cd docs-site && $(MKDOCS) build --strict --config-file mkdocs.yml
	@echo "✅ Build succeeded → docs-site/site/"

docs-lint: ## Lint all public docs markdown with pymarkdownlnt
	@echo "→ Linting markdown in docs-site/docs/..."
	@$(VENV)/bin/pymarkdown --config docs-site/.pymarkdown.json scan docs-site/docs/ || true
	@echo "Lint complete."

docs-check-clean: ## Check public docs for leaked internal SSOT tokens
	@echo "→ Checking public docs for internal tokens..."
	@$(PYTHON) scripts/check_public_docs_clean.py
	@echo "Sanitizer check complete."

docs-gen-cli: ## Auto-generate CLI reference from cherenkov --help
	@echo "→ Generating CLI reference..."
	@$(PYTHON) scripts/gen_cli_reference.py

##@ Documentation — Versioning (mike)
docs-version-list: ## List all deployed mike versions on gh-pages
	@cd docs-site && $(MIKE) list

docs-deploy-dev: ## Deploy docs as 'dev' alias (for testing mike locally)
	@echo "→ Deploying docs as 'dev' alias..."
	@cd docs-site && $(MIKE) deploy dev
	@echo "✅ Deployed. Run 'make docs-version-list' to confirm."

##@ Development
test: ## Run the full Python + Playwright test suite
	@$(PYTHON) -m pytest cherenkov/ -v

doctor: ## Run environment health check
	@$(PYTHON) -m cherenkov.cli doctor

##@ First-Time Setup
install: ## Install all Python + docs dependencies
	@pip install -r requirements.txt
	@pip install -r docs-site/docs-requirements.txt
	@echo "✅ Dependencies installed. Activate venv: source .venv/bin/activate"
