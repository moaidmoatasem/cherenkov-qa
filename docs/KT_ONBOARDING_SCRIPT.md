# CHERENKOV QA — Knowledge Transfer & Demo Script

> **Target Audience:** Engineering Leads, QA Managers, and Developers.
> **Estimated Time:** 10-15 Minutes
> **Format:** Suitable for live presentation, Loom recording, or an Asciinema terminal cast.

---

## 🎬 Part 1: The Pitch (2 Minutes)

**[Visual: Title Slide or the CHERENKOV GitHub README]**

**Presenter (Voiceover):**
"Hi everyone, today I'm going to walk you through CHERENKOV QA. 

In the world of AI coding, generation is free. We can generate hundreds of tests in seconds. But **trust isn't free**. If an AI writes a test and hallucinates the expected outcome, you end up with green builds that are actually broken.

CHERENKOV is built on a single, uncompromising principle: **The OpenAPI Specification is the Single Source of Truth (SSOT).** 

When CHERENKOV generates a test using an LLM, it doesn't just trust the output. It passes that generated code through a series of rigid, deterministic gates. It checks if the assertions match the spec. It dry-runs the requests. If the AI hallucinates, CHERENKOV catches it statically. 

Today, we're going to see how you can go from zero to a fully verified test suite in under 60 seconds against completely real APIs—no mock servers."

---

## 🚀 Part 2: Zero to Hero Quickstart (4 Minutes)

**[Visual: A clean terminal window]**

**Presenter:**
"Let's start with a classic example: The public Petstore API. We want to generate a full suite of Playwright tests for it without writing a single line of boilerplate."

**[Action: Type the following commands]**

```bash
# 1. Initialize the project (zero-config)
cherenkov init

# 2. Download the standard Petstore spec
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json

# 3. Generate the tests
cherenkov generate --spec petstore.json --output-dir tests/ --no-repair
```

**Presenter:**
"What's happening right now? CHERENKOV is ingesting the OpenAPI spec, planning out happy paths and edge cases (like 400s and 404s), and passing that context to our local LLM. 

But crucially, before it writes those tests to disk, it verifies them against the spec. If the LLM tried to assert a `200 OK` on a POST creation endpoint instead of a `201 Created` as defined by the spec, our Gate 4 assertion checker would block it."

**[Action: The terminal shows tests being generated]**

**Presenter:**
"Now we have our tests. Let's run them directly against the real, live public Petstore API to see if their implementation actually matches their spec."

**[Action: Type validation command]**

```bash
cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json --fail-on-drift
```

**Presenter:**
"Here’s where CHERENKOV shines. By running this against a live API, we frequently discover 'spec drift'. For example, the spec says an endpoint returns a `404` for a missing pet, but the actual live server returns a `400`. CHERENKOV highlights these exact discrepancies immediately."

---

## ⚡ Part 3: The Live Case - JSONPlaceholder API (5 Minutes)

**[Visual: Clear the terminal window]**

**Presenter:**
"Petstore is great for a hello-world, but let's test another fully real, production API. We'll use JSONPlaceholder, a popular public REST API that accepts real CRUD operations."

**[Action: Navigate to the live-case data]**

```bash
cd demos/live-case-data/
```

**Presenter:**
"We have a minimal OpenAPI spec defining JSONPlaceholder's `/posts` endpoint. We are going to generate tests and run them directly against the production server."

**[Action: Generate]**

```bash
cherenkov generate --spec jsonplaceholder_spec.json --output-dir tests-jsonplaceholder/ --repair
```

**Presenter:**
"Notice we used the `--repair` flag here. If the AI makes a mistake generating the JSON payloads, CHERENKOV will catch it and automatically send the error back to the LLM to fix it. A self-healing test generation loop."

**[Action: Validate against the real production server]**

```bash
cherenkov validate --target https://jsonplaceholder.typicode.com --spec jsonplaceholder_spec.json
```

**Presenter:**
"Our generated Playwright tests hit the real JSONPlaceholder API across the internet, validating that the payloads are perfectly constructed and the live server responds exactly according to its strict OpenAPI contract. Real requests, real test data, no mocks."

---

## 📊 Part 4: The Dashboard & CI/CD (3 Minutes)

**[Visual: Still in the terminal]**

**Presenter:**
"Command line tools are great for developers, but QA teams and managers need visuals. CHERENKOV includes a beautiful, built-in dashboard."

**[Action: Launch dashboard]**

```bash
cherenkov dashboard
```

**[Visual: Open web browser to the localhost dashboard URL]**

**Presenter:**
"This dashboard provides a real-time view of your spec coverage, pass/fail rates, and most importantly, spec drift. You can see exactly which endpoints are violating your OpenAPI contract.

Furthermore, you can easily integrate this into your CI/CD. By running `cherenkov certify`, you can fail your Jenkins or GitHub Actions build if the code diverges from the spec."

---

## 🎯 Part 5: Conclusion

**[Visual: Return to title slide or CHERENKOV logo]**

**Presenter:**
"To summarize:
1. Generation is fast, but CHERENKOV makes it **safe** by enforcing the spec as the ultimate authority.
2. It catches spec drift immediately against real APIs.
3. It integrates perfectly into local dev workflows, CI pipelines, and provides management visibility through the dashboard.

Thank you for watching. Check out the repository to get started with `cherenkov init` today."
