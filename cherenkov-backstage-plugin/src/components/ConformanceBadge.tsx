import React from 'react';
import { useEntity } from '@backstage/plugin-catalog-react';
import { useApi } from '@backstage/core-plugin-api';
import { cherenkovApiRef } from '../api/CherenkovClient';

export function ConformanceBadge() {
  const { entity } = useEntity();
  const cherenkovApi = useApi(cherenkovApiRef);
  const targetUrl = entity.metadata.annotations?.['cherenkov.dev/target-url'];
  const [status, setStatus] = React.useState<any>(null);

  React.useEffect(() => {
    if (!targetUrl) return;
    cherenkovApi.getStatus(targetUrl).then(setStatus).catch(() => {});
  }, [targetUrl, cherenkovApi]);

  if (!status) return null;

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 12,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: status.violations === 0 ? '#4caf50' : '#f44336',
        color: '#fff',
      }}
    >
      {status.violations === 0 ? 'PASS' : `FAIL (${status.violations})`}
    </span>
  );
}
