/** @license SPDX-License-Identifier: Apache-2.0 */

import React, { useState, useEffect } from 'react';
import { Cpu, Monitor, Wifi, WifiOff, CheckCircle, XCircle } from 'lucide-react';
import { Card, PageHeader, MockBadge, EmptyState, Skeleton } from './ui';
import { fetchDoctor, DoctorCheck } from '../lib/api';

export default function DeviceManagerScreen() {
  const [doctorData, setDoctorData] = useState<any>({ checks: [], ready: false });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchDoctor();
        setDoctorData(data);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
        <EmptyState
          icon={Cpu}
          title="Failed to Load Doctor Checks"
          description={`Could not fetch device information: ${error}`}
          primaryAction={{
            label: "Retry",
            onClick: () => window.location.reload()
          }}
        />
      </div>
    );
  }

  const checks: DoctorCheck[] = doctorData.checks || [];
  const passedCount = checks.filter(c => c.status === 'passed').length;
  const failedCount = checks.filter(c => c.status === 'failed').length;
  const isReady = doctorData.ready ?? false;

  const statusIcon = (status: string) => {
    switch (status) {
      case 'passed': return <CheckCircle className="w-3 h-3" />;
      case 'failed': return <XCircle className="w-3 h-3" />;
      case 'warning': return <XCircle className="w-3 h-3" />;
      default: return <XCircle className="w-3 h-3" />;
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="devices-screen">
      <PageHeader
        title="Device & Provider Manager"
        description="VLM device detection, provider tiers, and runtime health checks."
      />
      <MockBadge />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="flex flex-col p-6">
          <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Monitor className="w-4 h-4 text-glow-blue" />
            <span>Device Status</span>
          </h3>
          <div className="mt-4 flex items-center gap-3">
            {isLoading ? (
              <Skeleton className="h-12 w-full rounded-xl" />
            ) : (
              <>
                {isReady ? (
                  <Wifi className="w-8 h-8 text-green-400" />
                ) : (
                  <WifiOff className="w-8 h-8 text-red-400" />
                )}
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    {isReady ? 'Online' : 'Degraded'}
                  </p>
                  <p className="text-xs text-[#7D8DA1]">
                    {passedCount}/{checks.length} checks passed
                  </p>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card className="flex flex-col p-6">
          <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Cpu className="w-4 h-4 text-glow-blue" />
            <span>Check Summary</span>
          </h3>
          <div className="mt-4 space-y-2">
            {isLoading ? (
              <>
                <Skeleton className="h-6 w-full rounded" />
                <Skeleton className="h-6 w-full rounded" />
              </>
            ) : (
              <>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-text-primary">{passedCount} Passed</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <span className="text-text-primary">{failedCount} Failed</span>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card className="flex flex-col p-6">
          <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">VLM Tier</h3>
          <div className="mt-4">
            {isLoading ? (
              <Skeleton className="h-8 w-full rounded" />
            ) : (
              <p className="text-lg font-bold font-mono text-glow-bright">
                {isReady ? 'small / deep / vision' : 'unknown'}
              </p>
            )}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted mb-4">Doctor Checks</h3>
        <div className="space-y-2">
          {isLoading ? (
            <>
              <Skeleton className="h-10 w-full rounded-xl" />
              <Skeleton className="h-10 w-full rounded-xl" />
              <Skeleton className="h-10 w-full rounded-xl" />
            </>
          ) : checks.length === 0 ? (
            <p className="text-xs text-[#7D8DA1] text-center py-4">No doctor checks available.</p>
          ) : (
            checks.map(check => (
              <div
                key={check.id}
                className="flex items-center justify-between p-3 rounded-xl bg-black/20 border border-white/5 text-xs"
              >
                <div>
                  <p className="font-semibold text-text-primary">{check.name}</p>
                  {check.message && (
                    <p className="text-[#7D8DA1] mt-0.5">{check.message}</p>
                  )}
                </div>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono font-bold uppercase ${
                    check.status === 'passed'
                      ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                      : check.status === 'failed'
                      ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                      : check.status === 'warning'
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                  }`}
                >
                  {statusIcon(check.status)}
                  {check.status}
                </span>
              </div>
            ))
          )}
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted mb-4">Provider Status</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {isLoading ? (
            <>
              <Skeleton className="h-16 w-full rounded-xl" />
              <Skeleton className="h-16 w-full rounded-xl" />
            </>
          ) : (
            ['LocalAI', 'Ollama', 'OpenAI'].map(provider => {
              const check = checks.find(
                c => c.name.toLowerCase().includes(provider.toLowerCase())
              );
              const isOnline = check?.status === 'passed' || check?.status === 'warning';
              return (
                <div
                  key={provider}
                  className="flex items-center gap-3 p-3 rounded-xl bg-black/20 border border-white/5 hover:border-white/10 transition"
                >
                  {isOnline ? (
                    <Wifi className="w-5 h-5 text-green-400 shrink-0" />
                  ) : (
                    <WifiOff className="w-5 h-5 text-red-400 shrink-0" />
                  )}
                  <div>
                    <p className="text-xs font-semibold text-text-primary">{provider}</p>
                    <p className={`text-[10px] font-mono ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
                      {isOnline ? 'Connected' : 'Unreachable'}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>
    </div>
  );
}
