/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card, Skeleton } from '../../ui';
import { fetchHealth, fetchDoctor, fetchMobilePilotStatus, startMobilePilot, DoctorCheck, PilotStatus } from '../../../lib/api';
import { Cpu, Monitor, Wifi, WifiOff, CheckCircle2, XCircle, Smartphone, Play, RefreshCw } from 'lucide-react';

export const DeviceManager: React.FC = () => {
  const [doctorChecks, setDoctorChecks] = useState<DoctorCheck[]>([]);
  const [isReady, setIsReady] = useState(false);
  const [pilotStatus, setPilotStatus] = useState<PilotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadDeviceStatus = async () => {
    try {
      setIsLoading(true);
      const [docData, pilotData] = await Promise.all([
        fetchDoctor().catch(() => ({ checks: [], ready: false })),
        fetchMobilePilotStatus().catch(() => null),
      ]);
      setDoctorChecks(docData.checks || []);
      setIsReady(docData.ready);
      setPilotStatus(pilotData);
    } catch {
      setDoctorChecks([]);
      setIsReady(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDeviceStatus();
  }, []);

  const handleStartPilot = async () => {
    try {
      await startMobilePilot();
      loadDeviceStatus();
    } catch {
      // handled
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="device-manager">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Monitor className="w-4 h-4 text-cyan-400" />
            <span>Hardware & VLM Device Diagnostics</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Real hardware liveness, VLM model routing, and Maestro mobile pilot status.
          </p>
        </div>
        <button
          onClick={loadDeviceStatus}
          className="p-1.5 rounded-lg border border-border-subtle text-text-muted hover:text-text-primary transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-24 w-full rounded-xl" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex items-center gap-3 font-mono text-xs">
            {isReady ? <Wifi className="w-8 h-8 text-emerald-400" /> : <WifiOff className="w-8 h-8 text-rose-400" />}
            <div>
              <p className="font-bold text-text-primary">{isReady ? 'VLM Hardware Online' : 'Hardware Degraded'}</p>
              <p className="text-[10px] text-text-muted">
                {doctorChecks.filter((c) => c.status === 'passed').length}/{doctorChecks.length} checks passed
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between font-mono text-xs">
            <p className="text-[10px] text-text-muted uppercase">VLM Model Routing Tier</p>
            <p className="text-base font-bold text-cyan-400">LocalAI (Qwen2-VL / MiniGPT-4)</p>
            <p className="text-[10px] text-text-muted">Zero external API dependencies</p>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between font-mono text-xs">
            <div>
              <p className="text-[10px] text-text-muted uppercase">Maestro Mobile Pilot</p>
              <p className="text-sm font-bold text-amber-400">{pilotStatus?.status || 'IDLE'}</p>
              <p className="text-[10px] text-text-muted">
                {pilotStatus ? `${pilotStatus.current_step}/${pilotStatus.total_steps} steps` : 'ADB / Maestro 2.6.1'}
              </p>
            </div>
            <button
              onClick={handleStartPilot}
              className="px-2.5 py-1.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-bold flex items-center gap-1"
            >
              <Play className="w-3 h-3" /> Pilot Run
            </button>
          </div>
        </div>
      )}
    </Card>
  );
};

export default DeviceManager;
