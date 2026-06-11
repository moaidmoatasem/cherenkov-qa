import React, { useState, useEffect } from 'react';
import { Smartphone, Monitor, CheckCircle, XCircle, RotateCw, Play } from 'lucide-react';
import { Card, PageHeader, MockBadge, EmptyState, Skeleton } from './ui';


interface MobileDevice {
  id: string;
  name: string;
  platform: 'iOS' | 'Android';
  osVersion: string;
  connected: boolean;
  resolution: string;
  lastTestRun: string | null;
  testCount: number;
  passRate: number;
}

export default function MobileScreen() {
  const [devices] = useState<MobileDevice[]>([
    { id: 'm1', name: 'iPhone 15 Pro', platform: 'iOS', osVersion: '17.5', connected: false, resolution: '1179×2556', lastTestRun: null, testCount: 0, passRate: 0 },
    { id: 'm2', name: 'Pixel 8', platform: 'Android', osVersion: '14', connected: false, resolution: '1080×2400', lastTestRun: null, testCount: 0, passRate: 0 },
    { id: 'm3', name: 'iPad Air', platform: 'iOS', osVersion: '17.5', connected: false, resolution: '1640×2360', lastTestRun: null, testCount: 0, passRate: 0 },
    { id: 'm4', name: 'Galaxy Tab S9', platform: 'Android', osVersion: '14', connected: false, resolution: '1600×2560', lastTestRun: null, testCount: 0, passRate: 0 },
  ]);
  const [isLoading, setIsLoading] = useState(true);
  const [error] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-4 space-y-3">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-48" />
                <Skeleton className="h-3 w-24" />
              </Card>
            ))
          : devices.map((device) => (
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
                      <XCircle className="w-3 h-3" /> Disconnected
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-[#7D8DA1]">
                  <span>{device.platform} {device.osVersion}</span>
                  <span>{device.resolution}</span>
                </div>
                {device.connected && (
                  <div className="flex items-center gap-3 pt-2 border-t border-white/5">
                    <span className="text-xs text-[#7D8DA1]">{device.testCount} tests</span>
                    <span className="text-xs text-[#3FB950]">{device.passRate}% pass</span>
                    <button className="ml-auto flex items-center gap-1 px-3 py-1 bg-glow-blue/20 border border-glow-blue/30 rounded-lg text-xs text-glow-bright hover:bg-glow-blue/30 transition cursor-pointer disabled:opacity-30">
                      <Play className="w-3 h-3" /> Run
                    </button>
                  </div>
                )}
                <div className="absolute top-2 right-2">
                  <MockBadge />
                </div>
              </Card>
            ))}
      </div>

      {!isLoading && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center space-y-3">
          <p className="text-sm text-[#7D8DA1]">
            Mobile testing requires ADB (Android) or Maestro (iOS) to be installed and devices connected.
          </p>
          <p className="text-xs text-[#7D8DA1] opacity-60">
            Phase 5/6 — Requires dedicated environment with mobile tooling.
          </p>
        </div>
      )}
    </div>
  );
}
