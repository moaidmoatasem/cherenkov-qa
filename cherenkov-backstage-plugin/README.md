# @cherenkov/backstage-plugin

A Backstage plugin that shows CHERENKOV API conformance status on every service catalog page.

## Features

- **ConformanceCard** — Entity overview card showing violation count, endpoints tested, and last-checked time
- **ViolationTable** — Full conformance findings table with endpoint, method, severity, expected/actual values
- **ConformanceBadge** — Inline pass/fail badge for entity lists

## Installation

\`\`\`bash
yarn add --cwd packages/app @cherenkov/backstage-plugin
\`\`\`

## Configuration

### 1. Catalog entity annotation

Add the following annotations to your \`catalog-info.yaml\`:

\`\`\`yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: my-service
  annotations:
    cherenkov.dev/target-url: http://my-service.prod.svc.cluster.local
    cherenkov.dev/spec-path: ./openapi.yaml
spec:
  type: service
  lifecycle: production
\`\`\`

### 2. Register the plugin

In \`packages/app/src/plugins.ts\`:

\`\`\`typescript
export { cherenkovPlugin } from '@cherenkov/backstage-plugin';
\`\`\`

### 3. Add entity content tab

In \`packages/app/src/components/catalog/EntityPage.tsx\`:

\`\`\`typescript
import { ConformanceCard, ViolationTable } from '@cherenkov/backstage-plugin';

// Add to entity overview:
<Grid item md={6}>
  <ConformanceCard />
</Grid>

// Add entity content tab:
const ConformancePage = () => <ViolationTable />;
// Register in entity page tabs
\`\`\`

## Prerequisites

- CHERENKOV backend must be running and accessible
- \`/api/conformance/status\` and \`/api/conformance/report\` endpoints must be available
- Service catalog entities must have \`cherenkov.dev/target-url\` annotation
