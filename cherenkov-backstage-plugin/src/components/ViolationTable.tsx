import React, { useEffect, useState } from 'react';
import { Table, TableColumn, Progress } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';
import { useApi } from '@backstage/core-plugin-api';
import { cherenkovApiRef, ConformanceReport } from '../api/CherenkovClient';

export function ViolationTable() {
  const { entity } = useEntity();
  const cherenkovApi = useApi(cherenkovApiRef);
  const targetUrl = entity.metadata.annotations?.['cherenkov.dev/target-url'];

  const [report, setReport] = useState<ConformanceReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!targetUrl) {
      setLoading(false);
      return;
    }
    cherenkovApi
      .getReport(targetUrl)
      .then(r => {
        setReport(r);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [targetUrl, cherenkovApi]);

  if (loading) return <Progress />;

  const columns: TableColumn[] = [
    { title: 'Endpoint', field: 'endpoint', render: (row: any) => <code>{row.endpoint}</code> },
    { title: 'Method', field: 'method' },
    { title: 'Severity', field: 'severity' },
    { title: 'Expected', field: 'expected' },
    { title: 'Actual', field: 'actual' },
    { title: 'Summary', field: 'summary' },
  ];

  return (
    <Table
      title="Conformance Findings"
      options={{ paging: true, pageSize: 20 }}
      columns={columns}
      data={report?.findings ?? []}
    />
  );
}
