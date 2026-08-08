# Migrating from Postman to CHERENKOV-QA

Postman is a fantastic tool for manual API exploration, but scaling Postman collections for automated CI/CD testing often leads to fragile scripts, heavy maintenance burdens, and vendor lock-in.

CHERENKOV allows you to migrate your existing Postman collections into intelligent, auto-generated, zero-lock-in Playwright tests.

## Why Migrate?

- **Zero Scripting:** No more writing `pm.test()` assertions by hand.
- **Spec-Driven Truth:** The OpenAPI spec is the single source of truth, not a disconnected collection file.
- **Zero Lock-in:** `cherenkov eject` gives you standard Playwright Typescript files.
- **Local First:** Run tests locally without cloud syncing issues.

## Step 1: Export your Postman Collection

1. In Postman, click on your Collection.
2. Click the `...` menu and select **Export**.
3. Choose **Collection v2.1 (recommended)** and save the `.json` file to your project.

## Step 2: Ingest the Collection

CHERENKOV natively understands Postman v2.1 format. You can use it as a source adapter alongside your OpenAPI spec to train the LLM on your specific testing scenarios and edge cases.

```bash
cherenkov generate \
  --spec api.yaml \
  --postman-collection my-collection.json
```

CHERENKOV will parse the Postman collection, extract the saved request parameters and headers, and use them as high-quality data seeds when generating the new typed Playwright tests!

## Step 3: Run and Eject

Once the tests are generated, verify them against your live server:

```bash
cherenkov verify --url http://localhost:8080
```

If you ever decide to stop using CHERENKOV, you can eject the tests completely:

```bash
cherenkov eject --output ./my-playwright-tests
```

You now have a fully automated, standalone Playwright test suite, completely free from Postman!
