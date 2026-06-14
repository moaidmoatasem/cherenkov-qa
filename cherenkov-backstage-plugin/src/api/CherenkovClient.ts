import { createApiRef, DiscoveryApi } from '@backstage/core-plugin-api';

export interface ConformanceStatus {
  service: string;
  violations: number;
  endpointsTested: number;
  lastChecked: string;
  status: 'pass' | 'fail' | 'unknown';
}

export interface ConformanceFinding {
  endpoint: string;
  method: string;
  severity: string;
  summary: string;
  expected: string;
  actual: string;
}

export interface ConformanceReport {
  status: ConformanceStatus;
  findings: ConformanceFinding[];
}

export const cherenkovApiRef = createApiRef<CherenkovClient>({
  id: 'plugin.cherenkov.service',
});

export class CherenkovClient {
  private readonly discoveryApi: DiscoveryApi;

  constructor(opts: { discoveryApi: DiscoveryApi }) {
    this.discoveryApi = opts.discoveryApi;
  }

  private async getBaseUrl(): Promise<string> {
    return this.discoveryApi.getBaseUrl('cherenkov');
  }

  async getStatus(serviceAnnotation: string): Promise<ConformanceStatus> {
    const base = await this.getBaseUrl();
    const resp = await fetch(
      `${base}/api/conformance/status?service=${encodeURIComponent(serviceAnnotation)}`,
    );
    if (!resp.ok) throw new Error(`Cherenkov API error: ${resp.status}`);
    return resp.json();
  }

  async getReport(serviceAnnotation: string): Promise<ConformanceReport> {
    const base = await this.getBaseUrl();
    const resp = await fetch(
      `${base}/api/conformance/report?service=${encodeURIComponent(serviceAnnotation)}`,
    );
    if (!resp.ok) throw new Error(`Cherenkov API error: ${resp.status}`);
    return resp.json();
  }
}
