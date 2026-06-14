Hey Product Hunt! 👋

I'm the creator of CHERENKOV.

I built this because I was tired of finding spec violations in production. The workflow was always the same: update the spec, merge it, forget to update the tests, and three weeks later discover the API returns 400 when the spec says 422.

CHERENKOV reads your OpenAPI spec and generates conformance tests automatically using a local LLM (qwen2.5-coder via Ollama). No API costs, no data leaving your machine. Just point it at your spec and your live API, and it tells you exactly where the contract is broken.

The generated tests are fully ejectable — vanilla Playwright, zero CHERENKOV imports. You can take them and run them anywhere.

It also has native support for GraphQL and gRPC, exports OpenTelemetry spans, and integrates with Backstage.

Would love your feedback and questions!
