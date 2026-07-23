# Robust Demo Harness

This folder contains a production-grade Docker Compose testing harness demonstrating how CHERENKOV integrates cleanly with CI/CD platforms like Jenkins and GitHub Actions.

## The Problem
Running integration tests against a Dockerized microservice often fails because the service is still booting up (e.g., waiting for database connections) when the tests launch.

## The Solution
This harness configures strict `healthcheck` protocols.

The `api` service (a real implementation of Petstore) is configured with an internal `wget` health check. The `cherenkov-validator` service (which in a real CI environment would be your runner or GitHub action) is configured with a `depends_on: condition: service_healthy` block.

**Result:** Tests are never run until the API guarantees it is ready to receive traffic, eliminating flaky pipeline runs.

### How to Run

```bash
docker compose up
```

You will see the `api` container start, and the validator will wait until the health check passes before executing the test command.
