# AI Routing Consolidation Plan

## Current State

As of the latest refactoring, the `cherenkov.ai` module has been moved/merged into `cherenkov.substrate.providers`. However, we are left with two layers of abstraction co-existing in the same directory:

1. **Transport Layer (`*_client.py`)**: 
   Classes like `OpenAIInferenceClient` and `NemoClawInferenceClient` implement the `InferenceClient` interface. These handle raw HTTP transport, retries, LLM compatibility layers, and low-level completions.
   
2. **Orchestration Adapter Layer (`*.py`)**:
   Classes like `OpenAIProvider` and `NemoClawProvider` implement the `ProviderCapabilities` and wrap the `InferenceClient` objects. They adapt the raw text/json generation into domain-specific types like `ReasoningResult`.

## Analysis

The two layers **do serve genuinely different purposes**:
- The `*_client.py` files act as **API Drivers** (Network, rate limiting, raw payload serialization, LLM APIs).
- The wrapper `.py` files act as **Domain Adapters** (Bridging standard LLM output to CHERENKOV's internal types like `ReasoningRequest` and `ReasoningResult`).

Forcing a merge of these two layers would violate the single-responsibility principle by mixing HTTP transport logic with CHERENKOV domain object mapping.

## Proposed Consolidation & Cleanup

Since the layers serve different architectural purposes, they should not be squashed into single files. Instead, they should be structurally clarified to remove the confusion that they are redundant:

1. **Rename the Transport Layer Modules**:
   Move or keep the `*_client.py` files in a distinct `transport/` or `clients/` subpackage within `substrate/` (e.g., `cherenkov/substrate/clients/openai_client.py`), so it is visually obvious they are lower-level dependencies of the providers.
   
2. **Clarify Docstrings**:
   Update `cherenkov/substrate/providers/__init__.py` to reflect that the transport clients are no longer in `cherenkov.ai`, but rather exist as driver implementations, and the providers simply adapt them to the `ReasoningResult` schema.
   
3. **Remove Redundant `ai/` References**:
   Scrub any stale docstrings still referring to `cherenkov.ai` since the directory has already been collapsed into `substrate/`.

Executing this plan will clear the tech debt described in T7 without risking regressions in the network or retry logic.
