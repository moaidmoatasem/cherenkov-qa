#!/bin/bash
set -e

echo "=== Test 1: CLI bridge happy path ==="
K8S_SERVER="https://172.19.0.2:6443"
TOKEN=$(docker exec k3d-cherenkov-server-0 cat /var/lib/rancher/k3s/server/node-token 2>/dev/null || echo "")
CA_DATA=$(docker exec k3d-cherenkov-server-0 cat /var/lib/rancher/k3s/server/tls/server-ca.crt 2>/dev/null | base64 -w0 || echo "")

docker exec k3d-cherenkov-server-0 /tmp/k8s-run \
  --server "$K8S_SERVER" \
  --token "$TOKEN" \
  --ca "$CA_DATA" \
  --spec petstore-spec \
  --target prism \
  --port 4010 \
  --timeout 60s 2>&1 || echo "WARN: test 1 exited $?"

echo ""
echo "=== Test 2: CLI bridge failure path ==="
docker exec k3d-cherenkov-server-0 /tmp/k8s-run \
  --server "$K8S_SERVER" \
  --token "$TOKEN" \
  --ca "$CA_DATA" \
  --spec petstore-spec \
  --target nonexistent \
  --port 9999 \
  --timeout 120s 2>&1 || echo "WARN: test 2 exited $?"

echo ""
echo "=== Tests complete ==="
