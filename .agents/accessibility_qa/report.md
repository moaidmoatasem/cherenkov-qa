# Accessibility QA Report: Cherenkov Dashboard

**Date**: 2026-06-11
**Target URL**: `http://localhost:8000`

## Observations

The dashboard's HTML source was fetched using standard HTTP request (`curl.exe -s http://localhost:8000`). The returned document is a Single Page Application (SPA) entry point, typical of React, Vue, or similar frameworks.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cherenkov QA Protocol</title>
    ...
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
```

## Accessibility Findings (Static HTML)

1. **Language Declaration**: The `<html>` tag correctly includes `lang="en"`. This is crucial for screen readers to properly pronounce the text. (Pass)
2. **Viewport Meta Tag**: `<meta name="viewport" content="width=device-width, initial-scale=1.0" />` is correctly implemented. This ensures proper text scaling and responsive layout on mobile devices. (Pass)
3. **Semantic Structure**: There are **no** semantic HTML5 elements (e.g., `<main>`, `<header>`, `<nav>`) present in the static payload. The body only contains an empty `<div id="root"></div>`.
4. **ARIA Attributes**: There are **no** ARIA tags (`aria-*`, `role`) present in the initial HTML document.

## Caveats and Limitations

Because the application is an SPA, `curl` only evaluates the initial payload shell, not the fully rendered DOM. To fully evaluate the accessibility, ARIA tags, and semantic structure of the dashboard components, we must run an accessibility audit against the dynamically rendered DOM (e.g., using a headless browser, Lighthouse, or Playwright).

## Conclusion

The static shell passes basic document-level checks (`lang` and `viewport`). However, no semantic HTML or ARIA markup is present in the initial request. To evaluate the actual Cherenkov UI, an active browser session with JS execution capabilities is required.
