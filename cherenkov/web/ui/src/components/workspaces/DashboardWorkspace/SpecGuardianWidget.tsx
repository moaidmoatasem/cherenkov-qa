/**
 * SpecGuardianWidget — surfaces real drift events from the SpecGuardianDaemon
 * (#764, #765, #772 — Phase 14: Spec Guardian).
 *
 * Reads from /api/v1/guardian/* which proxies to DriftStore (SQLite).
 * When the daemon is not running, the widget still shows historical data.
 */

import React, { useEffect, useState, useCallback } from "react";
import { Shield, AlertTriangle, CheckCircle2, RefreshCw, Activity } from "lucide-react";
import {
  getGuardianStatus,
  listGuardianEvents,
  GuardianStatus,
  DriftEvent,
} from "../../../lib/api";

const SEV_COLORS: Record<string, string> = {
  critical: "text-rose-400",
  warning:  "text-amber-400",
  info:     "text-blue-400",
};

const SEV_DOT: Record<string, string> = {
  critical: "bg-rose-500",
  warning:  "bg-amber-400",
  info:     "bg-blue-400",
};

function SeverityBadge({ severity }: { severity: string }) {
  const colorClass = SEV_COLORS[severity] ?? "text-text-muted";
  const dotClass   = SEV_DOT[severity]   ?? "bg-white/20";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase ${colorClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass} inline-block`} />
      {severity}
    </span>
  );
}

export const SpecGuardianWidget: React.FC = () => {
  const [status, setStatus]   = useState<GuardianStatus | null>(null);
  const [events, setEvents]   = useState<DriftEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [s, e] = await Promise.all([getGuardianStatus(), listGuardianEvents(20)]);
    setStatus(s);
    setEvents(e);
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const trend = status?.trend_24h;
  const hasCritical = (trend?.critical_events ?? 0) > 0;

  return (
    <div className="ds-glass-panel rounded-xl p-5 flex flex-col gap-4" data-testid="spec-guardian-widget">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <Shield className={`w-5 h-5 shrink-0 ${hasCritical ? "text-rose-400" : "text-emerald-400"}`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-none text-text-primary">Spec Guardian</p>
          <p className="text-xs text-text-muted mt-0.5">Continuous API drift monitoring — Phase 14</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-white/5 transition-colors text-text-muted hover:text-text-primary disabled:opacity-40"
          data-testid="guardian-refresh-btn"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Trend 24h KPIs */}
      {trend && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Events (24h)", value: trend.total_events, color: "text-text-primary" },
            { label: "Critical",     value: trend.critical_events, color: "text-rose-400" },
            { label: "Warning",      value: trend.warning_events,  color: "text-amber-400" },
          ].map((kpi) => (
            <div key={kpi.label} className="bg-white/3 rounded-lg p-3 text-center border border-white/8">
              <p className={`text-xl font-bold font-mono ${kpi.color}`}>{kpi.value}</p>
              <p className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">{kpi.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recent events */}
      <div className="flex-1 min-h-0">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2 flex items-center gap-1.5">
          <Activity className="w-3 h-3" />
          Recent events
        </p>

        {events.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-text-muted py-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            No drift events recorded.
            {" "}
            {loading ? "Loading…" : "Run the guardian daemon to start monitoring."}
          </div>
        ) : (
          <div className="divide-y divide-white/5 max-h-48 overflow-y-auto">
            {events.map((evt, i) => (
              <div key={i} className="flex items-start gap-2 py-2">
                <SeverityBadge severity={evt.severity} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-text-primary truncate">
                    {evt.method} {evt.endpoint}
                  </p>
                  <p className="text-[10px] text-text-muted truncate">{evt.message}</p>
                </div>
                <p className="text-[9px] text-text-muted shrink-0 tabular-nums">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Daemon start hint */}
      {events.length === 0 && !loading && (
        <div className="p-3 rounded-lg bg-blue-500/8 border border-blue-500/20 text-[11px] text-blue-300 font-mono">
          cherenkov guardian --spec &lt;spec.json&gt; --target &lt;url&gt;
        </div>
      )}
    </div>
  );
};

export default SpecGuardianWidget;
