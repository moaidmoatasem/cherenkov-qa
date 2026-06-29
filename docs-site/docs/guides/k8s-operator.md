---
title: K8s Operator
---

# Kubernetes Operator

The CHERENKOV K8s operator provides a `ConformanceCheck` CRD for scheduled, in-cluster API conformance runs.

## Install

```bash
kubectl apply -f https://github.com/moaidmoatasem/cherenkov-qa/releases/latest/download/operator.yaml
```

## Create a ConformanceCheck

```yaml
apiVersion: cherenkov.io/v1alpha1
kind: ConformanceCheck
metadata:
  name: my-api-check
spec:
  spec: https://my-api.example.com/openapi.json
  target: http://my-api-service:8080
  schedule: "0 */6 * * *"   # every 6 hours
  failOnDrift: true
```

```bash
kubectl apply -f conformance-check.yaml
kubectl get conformancechecks
```

This guide is under active development. See the [Phase 8 release notes](../releases/v1.1.0.md) for full K8s details.
