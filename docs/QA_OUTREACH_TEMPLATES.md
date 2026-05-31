# QA Demo Outreach Templates

## Slack/Teams Message (copy-paste ready)

```
Hey [NAME] — I've been building a tool that generates Playwright API tests 
from an OpenAPI spec using a local LLM. No cloud, no vendor lock-in.

I want to show you one specific thing: it caught a real conformance bug 
(spec says 422, server returns 400) without anyone writing the test by hand.

Takes 7 minutes. I'll show you the generated test, the bug it catches, 
and the eject command that strips everything to vanilla Playwright.

One question at the end: "Would you keep these tests in your suite?"

When works for you this week?
```

## Calendar Invite Description

```
CHERENKOV QA Demo — 15 min

Moaid will demo a CLI tool that:
1. Reads your OpenAPI spec
2. Generates Playwright API tests via local LLM
3. Catches conformance drift (spec vs server)
4. Ejects to vanilla Playwright (zero vendor dependency)

Live demo of a real bug caught by a generated test. 
One question at the end — 2 minutes of your honest opinion.
```

## Post-Demo Follow-Up Message

```
Thanks for looking at this [NAME]. Your answer and feedback are recorded.

If you want to try it yourself:
- Repo: https://github.com/moaidmoatasem/cherenkov-qa (I'll add you)
- Getting started: docs/GETTING_STARTED.md — install to first test in 5 min
- The key command: ./bin/cherenkov validate --target <your-server-url>

No pressure — if you said "no" that's equally valuable data. 
The feedback shapes what gets built next.
```
