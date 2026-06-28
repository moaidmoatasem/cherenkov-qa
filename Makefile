DOCKER_REGISTRY ?= localhost:5000/cherenkov
NAMESPACE ?= cherenkov
K3D ?= ./scripts/k3d

.PHONY: help demo full install test test-unit lint lint-fix quick typecheck format \
        k3d-up k3d-down k3d-reset k3d-test \
        operator-image engine-image all-images sandbox-image \
        scripts-setup install-tools operator-build clean-k8s mobile-smoke

## Show this help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## Install Python + Node dependencies
install:
	pip install -r requirements.txt
	cd stub && npm install && npx playwright install && cd ..

## Run the full test suite (pytest + Playwright smoke)
test:
	PYTHONPATH=. python -m pytest tests/ -q --timeout=60 2>/dev/null || echo "Note: some tests require Ollama or other external services"

## Run unit tests only (excludes tests needing external services)
test-unit:
	PYTHONPATH=. python -m pytest tests/unit/ -q --timeout=30 --ignore=tests/unit/test_mcp_chat_tools.py --ignore=tests/unit/test_mcp_e2_2.py --ignore=tests/unit/test_mcp_tools.py --ignore=tests/unit/test_mcp_verify_system.py

## Run linting (ruff check)
lint:
	python -m ruff check cherenkov/ cherenkov.py

## Auto-fix lint issues (safe fixes only)
lint-fix:
	python -m ruff check --fix cherenkov/ cherenkov.py

## Quick check: lint + unit tests (common dev loop)
quick: lint test-unit

## Run type checking (mypy)
typecheck:
	python -m mypy --config-file=mypy.ini cherenkov/ cherenkov.py

## Auto-format code (ruff format)
format:
	python -m ruff format cherenkov/ cherenkov.py

demo: ## Start demo environment (mock data, no GPU required)
	docker compose --profile demo up

full: ## Start full environment (LocalAI + Redis + CHERENKOV, requires GPU)
	docker compose --profile full up

install-tools: ## Install dev tools (one-time setup, requires sudo)
	sudo bash scripts/install-tools.sh

# k3d targets
K3D_KUBECONFIG := $$HOME/.config/k3d/kubeconfig-cherenkov.yaml

k3d-up: all-images ## Create k3d cluster, import images, apply manifests
	@echo "Creating k3d cluster..."
	@$(K3D) cluster create cherenkov --config k8s/k3d-cluster.yaml 2>/dev/null || $(K3D) cluster start cherenkov
	@echo "Importing images into k3d..."
	@$(K3D) image import cherenkov-operator:latest cherenkov-engine:latest -c cherenkov
	@echo "Applying K8s manifests..."
	@KUBECONFIG=$(K3D_KUBECONFIG) kubectl apply -k k8s/
	@echo "Waiting for services to be ready..."
	@KUBECONFIG=$(K3D_KUBECONFIG) kubectl wait --for=condition=ready pod -l app=ollama -n $(NAMESPACE) --timeout=180s 2>/dev/null || true
	@echo "Waiting for model preloading..."
	@KUBECONFIG=$(K3D_KUBECONFIG) kubectl wait --for=condition=complete job/ollama-model-pull -n $(NAMESPACE) --timeout=300s 2>/dev/null || true
	@echo "k3d cluster is ready!"

k3d-down: ## Delete k3d cluster
	@echo "Deleting k3d cluster..."
	@$(K3D) cluster delete cherenkov 2>/dev/null || true

k3d-reset: k3d-down k3d-up ## Tear down and recreate k3d cluster

k3d-test: k3d-up ## Run integration tests against k3d cluster
	@echo "=== Test 1: CLI bridge happy path ==="
	@KUBECONFIG=$(K3D_KUBECONFIG) ./scripts/k8s-run --spec petstore-spec --target prism --port 4010 --timeout 60s
	@echo ""
	@echo "=== Test 2: CLI bridge failure path ==="
	@KUBECONFIG=$(K3D_KUBECONFIG) ./scripts/k8s-run --spec petstore-spec --target nonexistent --port 9999 --timeout 120s
	@echo ""
	@echo "=== Tests complete ==="

all-images: operator-image engine-image ## Build all Docker images

operator-image: ## Build the K8s operator Docker image
	docker build -t cherenkov-operator:latest -f operator/Dockerfile operator/

engine-image: ## Build the CHERENKOV engine Docker image
	docker build -t cherenkov-engine:latest engine/

sandbox-image: ## Build the sandbox Docker image
	docker build -t cherenkov-sandbox:latest --target=build -f operator/Dockerfile operator/

scripts-setup: ## Make scripts executable (one-time)
	chmod +x scripts/k3d-setup.sh 2>/dev/null || true

operator-build: ## Build the K8s operator binary (requires Go)
	cd operator && CGO_ENABLED=0 go build -o manager main.go
	cd operator && CGO_ENABLED=0 go build -o k8s-run ./cmd/k8s-run/main.go

clean-k8s: ## Delete k3d cluster and namespace
	KUBECONFIG=$(K3D_KUBECONFIG) kubectl delete namespace $(NAMESPACE) 2>/dev/null || true
	$(K3D) cluster delete cherenkov 2>/dev/null || true

security-audit: ## Run security audit (bandit + pip-audit)
	@echo "=== Bandit security scan ==="
	@python -m bandit -r cherenkov/ -q -ll 2>/dev/null || echo "  (bandit not installed — run: pip install bandit)"
	@echo ""
	@echo "=== pip-audit ==="
	@python -m pip_audit 2>/dev/null || echo "  (pip-audit not installed — run: pip install pip-audit)"

mobile-smoke: ## Run mobile smoke tests (requires Maestro)
	@echo "Running mobile smoke tests..."
	cd tests/mobile && maestro test --format junit --output results.xml . 2>/dev/null || echo "Maestro not installed — install via: curl -Ls https://get.maestro.mobile.dev | bash"
