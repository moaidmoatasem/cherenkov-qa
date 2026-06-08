/** @license SPDX-License-Identifier: Apache-2.0 */

import React from 'react';
import { Activity, Cpu, Box } from 'lucide-react';
import { fetchHealth } from '../lib/api';

export default function HealthWidget() {
  const [health, setHealth] = React.useState<{ status: string; device: string; gen_model: string } | null>(null);
  const [lastPolled, setLastPolled] = React.useState<Date | null>(null);

  React.useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const data = await fetchHealth();
        if (!mounted) return;
        setHealth({ status: data.status, device: data.device, gen_model: data.gen_model });
        setLastPolled(new Date());
      } catch {
        if (!mounted) return;
        setHealth(null);
        setLastPolled(new Date());
      }
    };
    poll();
    const id = window.setInterval(poll, 30000);
    return () => { mounted = false; window.clearInterval(id); };
  }, []);

  const secondsAgo = lastPolled ? Math.round((Date.now() - lastPolled.getTime()) / 1000) : null;

  return (
    <div
      style={{ maxWidth: 300 }}
      className="flex items-center gap-2 px-3 py-1 rounded bg-white/5 border border-white/10 text-xs font-mono"
    >
      <div className="flex items-center gap-1 text-[#7D8DA1]">
        <Activity className="w-3 h-3" />
        <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ backgroundColor: health?.status === 'online' ? '#3FB950' : '#ef4444' }} />
      </div>
      {health?.device && health.device !== 'unknown' && (
        <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/5 text-[#7D8DA1]">
          <Cpu className="w-2.5 h-2.5" />
          {health.device}
        </span>
      )}
      {health?.gen_model && (
        <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/5 text-[#7D8DA1]">
          <Box className="w-2.5 h-2.5" />
          {health.gen_model}
        </span>
      )}
      {secondsAgo !== null && (
        <span className="text-[#7D8DA1]/60">{secondsAgo}s ago</span>
      )}
    </div>
  );
}
