# Fine-Tuning Strategy: cherenkov-coder-7b

**Status:** Proposed (Phase 15)  
**Target Architecture:** Horizon 3  

## 1. The Moat

While base models like `qwen2.5-coder:7b` are highly capable, they often lack the deep, domain-specific intuition required to generate flawless Playwright API tests from complex OpenAPI specifications without multiple healing iterations. 

To build an unassailable technical moat in the AI testing market, CHERENKOV will train its own specialized model: **`cherenkov-coder-7b`**. This model will achieve the highest zero-shot success rate for test generation, drastically reducing compute costs and execution latency.

## 2. The Data Pipeline (Corpus Collection)

The most valuable asset for fine-tuning is high-quality data. We will implement an **opt-in telemetry pipeline** to collect "Golden Triangles" of data:

1. **The Prompt**: The isolated slice of the OpenAPI specification.
2. **The Output**: The generated, typed Playwright test case.
3. **The Verdict**: The execution result (Pass/Fail) and any syntax/AST gate corrections.

Only tests that successfully pass the 6-gate review and execute flawlessly against a real server will be added to the high-quality fine-tuning corpus. 

*Note: All telemetry will be strictly opt-in, anonymized, and scrubbed of PII/secrets before transmission.*

## 3. Training Methodology

- **Base Model**: `Qwen/Qwen2.5-Coder-7B-Instruct` (Provides strong baseline coding capabilities).
- **Technique**: Parameter-Efficient Fine-Tuning (PEFT) using LoRA / QLoRA to keep training costs low while maximizing adaptation.
- **Objective**: Maximize the generation of spec-compliant, executable Playwright TypeScript code without hallucinating assertions or HTTP status codes.

## 4. Evaluation Benchmark

We will evaluate the fine-tuned model against a standardized set of complex open-source APIs (e.g., Stripe, GitHub, Petstore).

**Key Metrics**:
- **Compile Rate**: % of generated tests that pass the AST and TypeScript compiler gates on the first try.
- **Zero-Shot Conformance**: % of generated tests that execute successfully without requiring the suggest-only healing loop.
- **Assertion Quality**: Density and strictness of expected-value assertions compared to the source spec.

## 5. Delivery

The fine-tuned weights will be published to the Hugging Face Model Hub and registered as a custom Ollama Modelfile, allowing users to pull and run `cherenkov-coder-7b` locally with a single command.
