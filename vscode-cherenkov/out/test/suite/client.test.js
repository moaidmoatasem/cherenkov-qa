"use strict";
/**
 * Unit tests for CherenkovClient.parseSarif() — runs in plain Node.js (no VS Code API).
 *
 * Tests verify:
 * - parseSarif returns an empty array for non-SARIF input
 * - parseSarif correctly extracts violations from valid SARIF 2.1.0 JSON
 * - parseSarif handles SARIF with no violations (all passed)
 * - parseSarif extracts line number from region info
 */
Object.defineProperty(exports, "__esModule", { value: true });
const assert = require("assert");
const sarif_1 = require("../../backend/sarif");
const VALID_SARIF_VIOLATIONS = JSON.stringify({
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {
                "driver": {
                    "name": "CHERENKOV-QA",
                    "version": "1.0.0",
                    "rules": [
                        { "id": "POST /payments", "shortDescription": { "text": "Conformance for POST /payments" } }
                    ]
                }
            },
            "results": [
                {
                    "ruleId": "POST /payments",
                    "message": { "text": "Expected 201, got 400" },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": { "uri": "openapi.yaml" },
                                "region": { "startLine": 42 }
                            }
                        }
                    ]
                },
                {
                    "ruleId": "GET /items",
                    "message": { "text": "Expected 200, got 500" },
                    "locations": []
                }
            ]
        }
    ]
});
const VALID_SARIF_NO_RESULTS = JSON.stringify({
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [{ "tool": { "driver": { "name": "CHERENKOV-QA", "version": "1.0.0", "rules": [] } }, "results": [] }]
});
suite('parseSarif', () => {
    test('returns empty array for empty input', () => {
        assert.deepStrictEqual((0, sarif_1.parseSarif)(''), []);
    });
    test('returns empty array for non-SARIF text', () => {
        assert.deepStrictEqual((0, sarif_1.parseSarif)('hello world\nsome output\n'), []);
    });
    test('returns empty array for SARIF with no results', () => {
        const result = (0, sarif_1.parseSarif)(VALID_SARIF_NO_RESULTS);
        assert.strictEqual(result.length, 0);
    });
    test('parses violations from valid SARIF JSON', () => {
        const violations = (0, sarif_1.parseSarif)(VALID_SARIF_VIOLATIONS);
        assert.strictEqual(violations.length, 2);
    });
    test('correctly extracts method and endpoint from ruleId', () => {
        const violations = (0, sarif_1.parseSarif)(VALID_SARIF_VIOLATIONS);
        const payment = violations.find(v => v.endpoint === '/payments');
        assert.ok(payment, 'Expected /payments violation');
        assert.strictEqual(payment.method, 'POST');
        assert.strictEqual(payment.error, 'Expected 201, got 400');
    });
    test('extracts line number from region', () => {
        const violations = (0, sarif_1.parseSarif)(VALID_SARIF_VIOLATIONS);
        const payment = violations.find(v => v.endpoint === '/payments');
        assert.strictEqual(payment.line, 42);
    });
    test('handles missing region gracefully', () => {
        const violations = (0, sarif_1.parseSarif)(VALID_SARIF_VIOLATIONS);
        const items = violations.find(v => v.endpoint === '/items');
        assert.ok(items, 'Expected /items violation');
        assert.strictEqual(items.line, undefined);
    });
    test('parses SARIF embedded in surrounding CLI output text', () => {
        const surrounding = `Running validation...\n${VALID_SARIF_VIOLATIONS}\nDone.`;
        const violations = (0, sarif_1.parseSarif)(surrounding);
        assert.strictEqual(violations.length, 2);
    });
});
//# sourceMappingURL=client.test.js.map