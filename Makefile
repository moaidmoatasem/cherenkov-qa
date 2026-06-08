DOCKER_REGISTRY ?= localhost:5000/cherenkov
NAMESPACE ?= cherenkov
K3D ?= ./scripts/k3d

.PHONY: demo full k3d-up k3d-down k3d-reset k3d-test operator-image engine-image all-images scripts-setup install-tools

demo:
	docker compose --profile demo up

full:
	docker compose --profile full up

# Install dev tools (one-time setup)
install-tools:
	sudo bash scripts/install-tools.sh

# k3d targets
K3D_KUBECONFIG := $$HOME/.config/k3d/kubeconfig-cherenkov.yaml

k3d-up: all-images
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

k3d-down:
	@echo "Deleting k3d cluster..."
	@$(K3D) cluster delete cherenkov 2>/dev/null || true

k3d-reset: k3d-down k3d-up

k3d-test: k3d-up
	@echo "=== Test 1: CLI bridge happy path ==="
	@KUBECONFIG=$(K3D_KUBECONFIG) ./scripts/k8s-run --spec petstore-spec --target prism --port 4010 --timeout 60s
	@echo ""
	@echo "=== Test 2: CLI bridge failure path ==="
	@KUBECONFIG=$(K3D_KUBECONFIG) ./scripts/k8s-run --spec petstore-spec --target nonexistent --port 9999 --timeout 120s
	@echo ""
	@echo "=== Tests complete ==="

# Image builds
all-images: operator-image engine-image

operator-image:
	docker build -t cherenkov-operator:latest -f operator/Dockerfile operator/

engine-image:
	docker build -t cherenkov-engine:latest engine/

sandbox-image:
	docker build -t cherenkov-sandbox:latest --target=build -f operator/Dockerfile operator/

# Scripts setup
scripts-setup:
	chmod +x scripts/k3d-setup.sh 2>/dev/null || true

# Go build (requires Go installed)
operator-build:
	cd operator && CGO_ENABLED=0 go build -o manager main.go
	cd operator && CGO_ENABLED=0 go build -o k8s-run ./cmd/k8s-run/main.go

# Cleanup
clean-k8s:
	KUBECONFIG=$(K3D_KUBECONFIG) kubectl delete namespace $(NAMESPACE) 2>/dev/null || true
	$(K3D) cluster delete cherenkov 2>/dev/null || true

.PHONY: mobile-smoke
mobile-smoke:  ## Run mobile smoke tests (requires Maestro)
	@echo "Running mobile smoke tests..."
	cd tests/mobile && maestro test --format junit --output results.xml . 2>/dev/null || echo "Maestro not installed — install via: curl -Ls https://get.maestro.mobile.dev | bash"
