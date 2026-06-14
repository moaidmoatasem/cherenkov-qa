import React, { useEffect, useState } from 'react';
import { InfoCard, Progress, ResponseErrorPanel } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';
import { useApi } from '@backstage/core-plugin-api';
import { cherenkovApiRef, ConformanceStatus } from '../api/CherenkovClient';

const CHERENKOV_ANNOTATION = 'cherenkov.dev/target-url';

export function ConformanceCard() {
  const { entity } = useEntity();
  const cherenkovApi = useApi(cherenkovApiRef);
  const targetUrl = entity.metadata.annotations?.[CHERENKOV_ANNOTATION];

  const [status, setStatus] = useState<ConformanceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!targetUrl) {
      setLoading(false);
      return;
    }
    cherenkovApi
      .getStatus(targetUrl)
      .then(s => {
        setStatus(s);
        setLoading(false);
      })
      .catch(e => {
        setError(e);
        setLoading(false);
      });
  }, [targetUrl, cherenkovApi]);

  if (!targetUrl) return null;
  if (loading) return <Progress />;
  if (error) return <ResponseErrorPanel error={error} />;

  const icon = status?.violations === 0 ? '✅' : '⚠️';

  return (
    <InfoCard title="API Conformance">
      <div style={{ display: 'flex', gap: 16 }}>
        <div>
          <strong>{icon}</strong> {status?.violations ?? '?'} violations
        </div>
        <div>Tested: {status?.endpointsTested ?? '?'} endpoints</div>
        <div>
          Last checked:{' '}
          {status?.lastChecked
            ? new Date(status.lastChecked).toLocaleString()
            : 'never'}
        </div>
      </div>
    </InfoCard>
  );
}
