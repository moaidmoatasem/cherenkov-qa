# Case Study: Testing Our Own Petstore API

At CHERENKOV-QA, we eat our own dog food. Before launching `v1.0.0`, we needed a reliable baseline to prove that the AI-native generation was both deterministic and powerful. We chose the classic Swagger Petstore API. 

We deployed a standard implementation of the Petstore API, handed its OpenAPI `v3` spec to CHERENKOV, and ran the validation suite.

Here is what we found.

## The Setup

- **Target:** Standard Node.js implementation of Swagger Petstore.
- **Spec:** `petstore.json` (OpenAPI 3.0.0)
- **Model:** `qwen2.5-coder:7b` (running locally via Ollama)

Command executed:
```bash
cherenkov verify --spec petstore.json --target http://localhost:3000
```

## Bug 1: The "Required Field" Lie

**Spec Definition:**
The `Pet` schema marks `name` and `photoUrls` as `required` fields. 

**CHERENKOV Generated Test:**
CHERENKOV generated a mutation test that explicitly omitted the `name` field in a `POST /pet` request, expecting the server to return an HTTP `400 Bad Request` or `422 Unprocessable Entity` due to schema validation failure.

**The Reality:**
The server returned `200 OK` and created a Pet with a null name.

**Impact:** Any downstream client expecting `name` to be a guaranteed string would crash with a `NullPointerException`. The server implementation was missing basic request validation.

## Bug 2: Silent Truncation of Enums

**Spec Definition:**
The `/pet/findByStatus` endpoint accepts a query parameter `status`, which is an `enum` of `["available", "pending", "sold"]`.

**CHERENKOV Generated Test:**
CHERENKOV generated an edge-case test passing `status=INVALID_STATUS_CODE`. It expected a `400` error since the value is outside the allowed enum.

**The Reality:**
The server returned `200 OK` with an empty array `[]`.

**Impact:** While not a fatal crash, returning an empty array for an invalid enum value masks client-side bugs. A typo in the client application would fail silently rather than receiving a helpful error message indicating an invalid parameter.

## Bug 3: The Unimplemented 404

**Spec Definition:**
The `GET /pet/{petId}` endpoint explicitly documents a `404 Not Found` response if the Pet ID does not exist.

**CHERENKOV Generated Test:**
CHERENKOV generated a test requesting a highly improbable Pet ID (`999999999999`), expecting the documented `404` response.

**The Reality:**
The server returned a `500 Internal Server Error`.

**Impact:** The database query failed to find the record, and the server threw an unhandled exception instead of gracefully translating it into a `404`. This inflates the 5xx error rate in monitoring systems and triggers unnecessary pager alerts for what is actually a client error (4xx).

## Bug 4: Content-Type Mismatch

**Spec Definition:**
The `POST /pet/{petId}/uploadImage` endpoint documents that it consumes `multipart/form-data`.

**CHERENKOV Generated Test:**
CHERENKOV correctly formatted a multipart payload with a binary boundary and sent it.

**The Reality:**
The server returned `415 Unsupported Media Type`. 

**Impact:** The implementation was actually expecting `application/x-www-form-urlencoded`. The spec and the server were completely out of sync, meaning anyone using an auto-generated client SDK based on the OpenAPI spec would be completely unable to use this endpoint.

## Conclusion

By running CHERENKOV against a standard reference API, we identified four distinct classes of spec drift:
1. Missing request validation (Bug 1 & 2)
2. Unhandled edge cases (Bug 3)
3. Hard contract mismatches (Bug 4)

These are bugs that traditional unit tests miss because they often mock the very boundaries where these issues occur. CHERENKOV caught them all with zero manual scripting.
