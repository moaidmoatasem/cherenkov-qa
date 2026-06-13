// CHERENKOV Week 0 — Stub setup (Delta D1: openapi-fetch, NO hand-rolled client class)
//
// The "ammunition." This is the typed client the generator is FORCED to use.
// openapi-typescript emits types only; openapi-fetch turns them into a 2-line client.
//
// Then this file IS the client the tests import. That's the whole stub.

import createClient from "openapi-fetch";
import type { paths } from "./generated-types";
import { AsyncLocalStorage } from "node:async_hooks";

// 1. Storage for Playwright's test fixtures (specifically request context)
export const playwrightContextStorage = new AsyncLocalStorage<any>();

// 2. Monkey-patch @playwright/test to run test bodies inside AsyncLocalStorage
try {
  const pwTest = require("@playwright/test");
  const originalTest = pwTest.test;

  if (originalTest && typeof originalTest === "function") {
    const wrapTestFn = (original: any) => {
      if (!original || typeof original !== "function") return original;
      const wrapped = function (this: any, title: string, body: any) {
        if (typeof body === "function") {
          const originalBody = body;
          // Playwright parses the parameter destructuring to determine fixtures.
          // By destructuring all standard fixtures, we ensure Playwright loads them
          // and we can intercept the request context.
          body = async function (
            this: any,
            { request, page, context, browser, browserName, playwright }: any,
            testInfo: any
          ) {
            const fixtures = { request, page, context, browser, browserName, playwright };
            return playwrightContextStorage.run(fixtures, async () => {
              return originalBody.call(this, fixtures, testInfo);
            });
          };
        }
        return original.call(this, title, body);
      };
      Object.assign(wrapped, original);
      return wrapped;
    };

    const wrappedTest = wrapTestFn(originalTest);
    wrappedTest.only = wrapTestFn(originalTest.only);
    wrappedTest.skip = wrapTestFn(originalTest.skip);
    wrappedTest.fixme = wrapTestFn(originalTest.fixme);
    wrappedTest.fail = wrapTestFn(originalTest.fail);

    pwTest.test = wrappedTest;
  }
} catch (e) {
  // Safe fail if @playwright/test is not available or required
}

// 3. Custom fetch implementation routing openapi-fetch calls through Playwright's APIRequestContext
const customFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const store = playwrightContextStorage.getStore();
  
  if (store && store.request) {
    const requestContext = store.request;
    
    // Resolve URL, method, headers and body from the input Request object or init options
    let url = "";
    let method = "GET";
    const headersRecord: Record<string, string> = {};
    let bodyData: any = undefined;

    if (input instanceof Request) {
      url = input.url;
      method = input.method;
      input.headers.forEach((value, key) => {
        headersRecord[key] = value;
      });
      if (["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase())) {
        try {
          bodyData = await input.clone().text();
        } catch (e) {
          // ignore
        }
      }
    } else {
      url = String(input);
      method = init?.method || "GET";
      if (init?.body) {
        bodyData = init.body;
      }
      if (init?.headers) {
        if (init.headers instanceof Headers) {
          init.headers.forEach((value, key) => {
            headersRecord[key] = value;
          });
        } else if (Array.isArray(init.headers)) {
          for (const [key, value] of init.headers) {
            headersRecord[key] = value;
          }
        } else {
          for (const [key, value] of Object.entries(init.headers)) {
            if (value !== undefined && value !== null) {
              headersRecord[key] = String(value);
            }
          }
        }
      }
    }

    // Ensure method is uppercase
    method = method.toUpperCase();

    // Construct Playwright-compatible request options
    const pwOptions: any = {
      method: method,
      headers: headersRecord,
    };

    if (bodyData !== undefined && bodyData !== null) {
      pwOptions.data = bodyData;
    }

    // Call Playwright's native APIRequestContext.fetch which generates trace network events
    const pwResponse = await requestContext.fetch(url, pwOptions);

    // Reconstruct standard fetch Response from Playwright APIResponse
    const bodyText = await pwResponse.text();
    const headers = new Headers();
    for (const [k, v] of Object.entries(pwResponse.headers())) {
      headers.append(k, String(v));
    }

    // Null-body statuses (204, 304) must not have a body in the Response constructor
    const NULL_BODY_STATUSES = new Set([101, 204, 205, 304]);
    const body = NULL_BODY_STATUSES.has(pwResponse.status()) ? null : bodyText;

    return new Response(body, {
      status: pwResponse.status(),
      statusText: pwResponse.statusText(),
      headers: headers,
    });
  }

  // Fallback to standard Node fetch
  return fetch(input, init);
};

export const client = createClient<paths>({
  baseUrl: process.env.API_URL ?? "http://localhost:8000",
  fetch: customFetch,
});
