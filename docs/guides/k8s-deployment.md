# Deploying CHERENKOV to Kubernetes

For enterprise teams, CHERENKOV is best run as a native Kubernetes Operator. By deploying the CHERENKOV `ConformanceCheck` Custom Resource Definition (CRD), you can automate API testing for every service running in your cluster.

## 1. Install the Operator

First, deploy the CHERENKOV K8s Operator and CRDs to your cluster. 

```bash
kubectl apply -f https://raw.githubusercontent.com/moaidmoatasem/cherenkov-qa/main/k8s/crd.yaml
kubectl apply -f https://raw.githubusercontent.com/moaidmoatasem/cherenkov-qa/main/k8s/operator.yaml
```

The Operator runs in the `cherenkov-system` namespace by default and watches for `ConformanceCheck` resources.

## 2. Create a ConformanceCheck

To test a service, create a `ConformanceCheck` manifest. This tells the operator which OpenAPI spec to read, and which internal cluster service to test against.

```yaml
apiVersion: cherenkov.dev/v1alpha1
kind: ConformanceCheck
metadata:
  name: payment-api-check
  namespace: default
spec:
  # The target API service inside the cluster
  targetUrl: http://payment-service.default.svc.cluster.local:8080
  
  # Where to fetch the OpenAPI spec
  specSource:
    url: http://payment-service.default.svc.cluster.local:8080/openapi.json
  
  # How often to run the check
  schedule: "0 * * * *" # Every hour
  
  # What to do on failure
  alerting:
    slackWebhook: "https://hooks.slack.com/services/..."
```

Apply the manifest:

```bash
kubectl apply -f payment-api-check.yaml
```

## 3. ArgoCD Integration (GitOps)

If you use ArgoCD, you can use an `ApplicationSet` to automatically generate a `ConformanceCheck` for every microservice in your organization!

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-wide-conformance
spec:
  generators:
  - list:
      elements:
      - service: payment-api
      - service: user-api
      - service: inventory-api
  template:
    spec:
      source:
        repoURL: https://github.com/my-org/manifests.git
        path: cherenkov-chart
        helm:
          values: |
            conformanceCheck:
              target: http://{{ service }}.prod.svc.cluster.local
```

Now, every service deployed via ArgoCD gets automatic, continuous API conformance monitoring!
