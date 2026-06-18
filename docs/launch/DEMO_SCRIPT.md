# CHERENKOV: 90-Second Demo Video Script

**Target Length:** 1:30  
**Format:** Screen recording + Voiceover (or high-energy text callouts)  
**Goal:** Prove the "Magic" (LLM generation) and the "Moat" (Zero Lock-In).

---

### Scene 1: The Problem (0:00 - 0:15)
**Visual:** 
- Split screen. Left: An OpenAPI spec showing `age: integer (max 150)`. Right: A live server codebase showing someone accidentally typing `age: 200`.
**Voiceover/Text:** 
"APIs drift. Specs say one thing, the server does another, and production breaks. Writing tests to catch this takes hours."

### Scene 2: The Magic (0:15 - 0:40)
**Visual:**
- Terminal window.
- User types: `cherenkov validate --source openapi --spec ./api.yaml`
- Terminal shows progress bars: `[LocalAI] Generating Test Scenario...`, `[AST] Validating TypeScript...`, `[Playwright] Executing...`
- Terminal outputs a massive red failure: `❌ DRIFT DETECTED. Expected max 150, Received 200.`
**Voiceover/Text:** 
"CHERENKOV reads your spec and uses a local LLM to autonomously generate and run Playwright tests to find the drift. Completely offline. No API keys required."

### Scene 3: The Integration (0:40 - 0:55)
**Visual:**
- Terminal window. User runs the same command with `--export-jira`.
- Switch to Jira board in browser: a new bug ticket magically appears with the exact drift details and LLM root-cause hypothesis.
**Voiceover/Text:** 
"When it finds drift in CI, it automatically exports beautifully formatted Jira tickets so your team can fix it fast."

### Scene 4: The Moat / Eject (0:55 - 1:15)
**Visual:**
- Terminal window.
- User types: `cherenkov eject ./tests/`
- IDE opens showing a pristine, human-readable Playwright TypeScript file.
- User types `npm run playwright test` and it runs perfectly without CHERENKOV.
**Voiceover/Text:** 
"Don't want to be locked into an AI testing tool? Just type `cherenkov eject`. We strip our framework and give you standard Playwright tests you own forever."

### Scene 5: Call to Action (1:15 - 1:30)
**Visual:**
- CHERENKOV Logo / Reality Engine text.
- GitHub URL and `npx cherenkov-cli init` command on screen.
**Voiceover/Text:** 
"Stop writing API tests by hand. Maintain continuous truth with the Reality Engine. Open source and available now on GitHub."
