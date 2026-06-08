# CHERENKOV — Technical Design Policy Notes

**Authority:** [docs/STATUS.md](STATUS.md) · [docs/PHASE_PLAN.md](PHASE_PLAN.md) · [docs/HANDOVER.md](HANDOVER.md) · **For:** Core Architecture

> **Anti-drift note (HANDOVER §2):** there is **no spec called "v3.1 + delta."**
> The earlier "Authority: v3.1 + delta" line in this file was a fabrication
> by a prior agent. This file's authority is now anchored to the live docs
> (SSOT) listed above. If you find a reference to "v3.1 + delta" anywhere
> in the repo, treat it as stale and re-anchor.

---

## 🖥️ Device Portability & Execution Target Policy

This document registers the official architectural decisions regarding hardware execution profiles.

### 1. Hardware Specification
- **GPU Optimized Target Path**: The primary, supported, and optimized execution target is the local NVIDIA GPU (specifically tested on NVIDIA GeForce RTX 5060 Laptop GPU with 8GB VRAM). All prompt templates, prefix-caching structures, and inference constraints are built to maximize GPU performance.
- **Warm Generation Baseline**: GPU acceleration target is **3s - 5s** warm generation speed for standard test scenarios.

### 2. Portability Policy (CPU Profile)
- **CPU Portability as a Courtesy**: Running CHERENKOV on CPU is supported as a fallback for CI pipelines, local contributors without compatible GPUs, or lightweight testing environments.
- **Performance Characteristics**: Under CPU execution, generation times are expected to be ~10x slower (~40s per test scenario) because hardware-level RadixAttention prefix caching and high-speed tensor operations are absent.
- **Zero CPU Egress Optimization**: No CPU-specific optimizations are permitted (e.g., no dynamic model-size switching, no batching, no quantization tuning). CPU remains a baseline courtesy, not a first-tier product path.

---

## 🛠️ Pipeline Startup Health Check Policy
- Every execution of the orchestrator must perform a dynamic device-detection health check during pipeline initialization.
- The pipeline queries Ollama's active memory usage via `/api/ps`.
- The system must loudly emit a warning in the JSONL stream if it detects a CPU runtime, notifying users of the ~10x slower execution speeds.
