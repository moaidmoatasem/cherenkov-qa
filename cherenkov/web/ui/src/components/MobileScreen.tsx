import React, { useState, useEffect } from 'react';
import { Smartphone, CheckCircle, XCircle, Play } from 'lucide-react';
import { Card, PageHeader, EmptyState, Skeleton } from './ui';
import { API_BASE } from '../lib/api';

interface MobileDevice {
  id: string;
  name: string;
  platform: string;
  connected: boolean;
  state?: string;
}

interface RunnerStatus {
  maestro: boolean;
  appium: boolean;
}

export default function MobileScreen() {
  const [devices, setDevices] = useState<MobileDevice[]>([]);
  const [runners, setRunners] = useState<RunnerStatus>({ maestro: false, appium: false });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/mobile/devices`);
        if (!res.ok) throw new Error(`Device inventory unavailable (HTTP ${res.status})`);
        const data = await res.json();
        if (mounted) {
          setDevices(data.devices ?? []);
          setRunners(data.runners ?? { maestro: false, appium: false });
        }
      } catch (e) {
        if (mounted) setError((e as Error).message);
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="mobile-screen">
        <PageHeader
          title="Mobile Testing"
          description="Connect and run tests on physical or emulated mobile devices."
        />
        <EmptyState icon={Smartphone} title="Mobile Testing Unavailable" description={error} />
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="mobile-screen">
      <PageHeader
        title="Mobile Testing"
        description="Connect and run tests on physical or emulated mobile devices."
      />

      {/* Runner availability */}
      {!isLoading && (
        <div className="flex gap-3" data-testid="runner-status">
          {(['maestro', 'appium'] as const).map(runner => (
            <span
              key={runner}
              data-testid={`runner-${runner}`}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono uppercase tracking-wider ${
                runners[runner]
                  ? 'border-[#3FB950]/30 bg-[#3FB950]/10 text-[#3FB950]'
                  : 'border-white/10 bg-white/5 text-[#7D8DA1]'
              }`}
            >
              {runners[runner] ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {runner}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading &&
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="p-4 space-y-3">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-3 w-48" />
              <Skeleton className="h-3 w-24" />
            </Card>
          ))}
        {!isLoading &&
          devices.map((device) => (
            <Card key={device.id} data-testid={`device-card-${device.id}`} className="p-4 space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Smartphone className="w-5 h-5 text-[#7D8DA1]" />
                  <span className="font-semibold text-sm">{device.name}</span>
                </div>
                {device.connected ? (
                  <span data-testid={`device-status-${device.id}`} className="flex items-center gap-1 text-xs text-[#3FB950]">
                    <CheckCircle className="w-3 h-3" /> Connected
                  </span>
                ) : (
                  <span data-testid={`device-status-${device.id}`} className="flex items-center gap-1 text-xs text-[#F85149]">
                    <XCircle className="w-3 h-3" /> {device.state || 'Disconnected'}
                  </span>
                )}
              </div>
              <div className="flex gap-4 text-xs text-[#7D8DA1]">
                <span>{device.platform}</span>
                <span className="font-mono">{device.id}</span>
              </div>
              {device.connected && (
                <div className="flex items-center gap-3 pt-2 border-t border-white/5">
                  <button className="ml-auto flex items-center gap-1 px-3 py-1 bg-glow-blue/20 border border-glow-blue/30 rounded-lg text-xs text-glow-bright hover:bg-glow-blue/30 transition cursor-pointer disabled:opacity-30">
                    <Play className="w-3 h-3" /> Run
                  </button>
                </div>
              )}
            </Card>
          ))}
      </div>

      {!isLoading && devices.length === 0 && (
        <EmptyState
          icon={Smartphone}
          title="No Devices Connected"
          description="Connect an Android device or start an emulator (visible to ADB), then reload. iOS devices run through Maestro."
        />
      )}

      {!isLoading && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center space-y-3">
          <p className="text-sm text-[#7D8DA1]">
            Mobile testing requires ADB (Android) or Maestro (iOS) to be installed and devices connected.
          </p>
        </div>
      )}
    </div>
  );
}
