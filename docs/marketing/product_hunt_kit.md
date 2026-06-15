# Product Hunt Launch Kit

**Product Name**: CHERENKOV-QA
**Tagline**: AI-native API testing. Spec in, Playwright tests out.
**Website**: https://github.com/cherenkov-qa/cherenkov
**Pricing**: Free Options

## Description (260 chars max)
Turn your OpenAPI spec into an automated, self-healing Playwright test suite in seconds. CHERENKOV-QA uses local LLMs to generate assertions, test endpoints, and detect API drift—with zero vendor lock-in. Eject to vanilla Playwright anytime.

## Maker Comment
Hey Product Hunt! 👋 I'm Moaid, creator of CHERENKOV-QA.

API testing is traditionally a massive chore. You write a spec, and then you have to manually write thousands of lines of Postman/Playwright assertions to keep the API honest. When the API drifts, the tests break, and you rewrite them.

**We built CHERENKOV to automate this entire loop:**
1. **Ingest**: Reads OpenAPI, GraphQL, or gRPC specs.
2. **Generate**: A local LLM (Ollama) generates strongly-typed Playwright tests.
3. **Validate**: Runs tests against your live API to detect drift.
4. **Heal**: Auto-suggests spec or code fixes when things break.

**Key features:**
- 🚫 **Zero lock-in**: Run `cherenkov eject` and walk away with a clean, standard Playwright suite.
- 🔒 **Privacy-first**: Uses local models by default (Qwen/Llama) so your API data never leaves your machine.
- 🐙 **CI/CD native**: Drop it into GitHub Actions to break the build on conformance drift.

We'd love for you to try it on your API today (`npx cherenkov init`) and let us know what you think! We are open-source and MIT licensed.

## Images & Assets
- **Logo (240x240)**: `logo/dark.png`
- **Thumbnail (600x600)**: GIF of CLI `cherenkov validate` running in terminal.
- **Gallery Image 1 (1270x760)**: Visual diagram of Spec -> LLM -> Playwright loop.
- **Gallery Image 2 (1270x760)**: Screenshot of the React Dashboard showing drift.
- **Gallery Image 3 (1270x760)**: Code diff showing `cherenkov heal` suggesting a fix.
- **Video**: 2-minute Loom walkthrough embedded via YouTube.

## Launch Day Checklist
- [ ] Post at 12:01 AM PST
- [ ] Send announcement to Discord community
- [ ] Post on Twitter/X, tagging @ProductHunt
- [ ] Reply to comments within 15 minutes
- [ ] Share on HackerNews and relevant subreddits (r/programming, r/webdev, r/softwaretesting)
