"use strict";
/**
 * sarif.ts — Pure SARIF 2.1.0 parser with no VS Code API dependency.
 * Can be unit-tested in plain Node.js.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseSarif = parseSarif;
/**
 * Parse SARIF 2.1.0 JSON output into structured Violation objects.
 * Tolerates surrounding CLI text — extracts the first JSON block containing
 * `"version": "2.1.0"`.
 */
function parseSarif(sarifJson) {
    const violations = [];
    try {
        const match = sarifJson.match(/(\{[\s\S]*"version"\s*:\s*"2\.1\.0"[\s\S]*\})/);
        if (!match) {
            return [];
        }
        const sarif = JSON.parse(match[1]);
        const runs = sarif.runs || [];
        for (const run of runs) {
            const results = run.results || [];
            for (const r of results) {
                const ruleId = r.ruleId || 'unknown';
                const [method, ...endpointParts] = ruleId.split(' ');
                const endpoint = endpointParts.join(' ') || ruleId;
                const message = r.message?.text || 'Conformance violation';
                const loc = r.locations?.[0]?.physicalLocation?.region;
                violations.push({
                    method: method || 'UNKNOWN',
                    endpoint,
                    error: message,
                    line: loc?.startLine,
                    column: loc?.startColumn,
                });
            }
        }
    }
    catch (_) {
        // Non-JSON output: not fatal
    }
    return violations;
}
//# sourceMappingURL=sarif.js.map