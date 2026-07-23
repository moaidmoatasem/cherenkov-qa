# Session 8: Zero Lock-in — Eject

> **Duration:** 3-5 minutes
> **Audience:** Skeptics / Anyone concerned about vendor lock-in
> **API:** Petstore (live or local)
> **Key Message:** Your tests are yours. Always. Zero lock-in guaranteed.
> **Difficulty:** Beginner

---

## Hook (5 seconds)

**Voiceover:**
> "What if you stop using CHERENKOV tomorrow? Your tests still run. Let me prove it."

*Visual: Terminal with generated tests.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Ensure tests are generated (from Session 1 or 3)
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: The Fear (30 seconds)

**Voiceover:**
> "I hear this question all the time: 'What if we adopt CHERENKOV and then want to switch tools? Are we stuck?' It's a fair question. Any vendor who doesn't address it upfront is hiding something."

*Visual: Overlay text:*

```
The Lock-in Fear:
  "If we adopt this tool, can we ever leave?"
```

**Voiceover:**
> "Let me address it right now."

---

## Part 2: The Eject Command (2 minutes)

### Step 2.1: Eject the Suite

**Voiceover:**
> "One command. `cherenkov eject`. It strips everything — every CHERENKOV import, every dependency, every reference — and leaves you with vanilla Playwright tests."

**Command:**
```bash
cherenkov eject --output /tmp/ejected_suite
```

*Expected:*
```
Ejected 6 test files + client.ts + generated-types.ts
Output: /tmp/ejected_suite/
Stripped: cherenkov imports, config references, tool metadata
Remaining: Standard Playwright + openapi-fetch
```

### Step 2.2: Inspect the Output

**Command:**
```bash
ls /tmp/ejected_suite/
```

*Expected:*
```
client.ts
generated-types.ts
happy_path.spec.ts
password_too_short.spec.ts
...
```

**Voiceover:**
> "Standard files. Let's look at one."

### Step 2.3: Show the Ejected Test

**Command:**
```bash
cat /tmp/ejected_suite/happy_path.spec.ts
```

*Expected:*
```typescript
import { test, expect } from '@playwright/test';
import createClient from 'openapi-fetch';
import type { paths } from './generated-types';

const client = createClient<paths>({ baseUrl: 'http://localhost:8000' });

test('POST /auth/register — happy path', async () => {
  const body = { email: 'test@example.com', password: 'password123' };
  const { data, error } = await client.POST('/auth/register', { body });
  expect(error).toBeFalsy();
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('email');
  expect(data.email).toBe('test@example.com');
});
```

**Voiceover:**
> "Standard Playwright. Standard openapi-fetch. No CHERENKOV anywhere. You could give this to any developer who's never heard of CHERENKOV, and they'd know exactly what it does."

### Step 2.4: Verify Zero References

**Command:**
```bash
grep -ri "cherenkov" /tmp/ejected_suite/ || echo "No CHERENKOV references found"
```

*Expected:*
```
No CHERENKOV references found
```

**Voiceover:**
> "Zero references. Clean. You own this code."

*[PAUSE — 2 seconds]*

---

## Part 3: Run It Standalone (60 seconds)

### Step 3.1: Install Dependencies

**Command:**
```bash
cd /tmp/ejected_suite
npm init -y
npm install @playwright/test openapi-fetch
```

*Expected: Standard npm install output.*

### Step 3.2: Run the Tests

**Voiceover:**
> "Run the tests. No CHERENKOV. No special tools. Just Playwright."

**Command:**
```bash
npx playwright test
```

*Expected:*
```
Running 6 tests using 1 worker

  ✓ happy_path.spec.ts (2.1s)
  ✓ password_too_short.spec.ts (1.8s)
  ✓ missing_email.spec.ts (1.5s)
  ...

  6 passed (5.4s)
```

**Voiceover:**
> "6 passed. No CHERENKOV in the loop. Vanilla Playwright. You're free."

*[PAUSE — 2 seconds]*

---

## Part 4: The Guarantee (30 seconds)

**Voiceover:**
> "Let me make this explicit:
> 1. Generated tests are standard Playwright TypeScript
> 2. `cherenkov eject` strips all dependencies
> 3. The ejected suite runs with `npx playwright test`
> 4. No CHERENKOV binary, no CHERENKOV imports, no CHERENKOV config
>
> You are never locked in. Your tests are yours. Period."

*Visual: Overlay:*

```
Zero Lock-in Guarantee:
  ✓ Standard Playwright output
  ✓ One-command eject
  ✓ Runs without CHERENKOV
  ✓ You own the code
```

---

## Closing CTA (5 seconds)

**Voiceover:**
> "Zero lock-in. Try it yourself — `cherenkov eject`."

*Visual: Project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 5 minutes
- [ ] The eject output is clean (zero CHERENKOV references)
- [ ] The standalone test run succeeds
- [ ] The grep for "cherenkov" returns nothing
- [ ] Voiceover is confident and direct
- [ ] The guarantee slide is on screen for 3+ seconds

---

## Editing Notes

- **Overlay** the "Lock-in Fear" text during Step 1
- **Red highlight** on "No CHERENKOV references found" for 2 seconds
- **Speed up** `npm install` to 4x
- **Add** text overlay: "Your tests. Your code. Always." at the end
- **Keep this session tight** — it's the shortest and most punchy
