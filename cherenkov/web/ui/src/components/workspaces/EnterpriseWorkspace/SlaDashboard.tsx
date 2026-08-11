import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle, AlertTriangle } from 'lucide-react';

interface TrendPoint {
  date: string;
  runs: number;
  failed: number;
}

interface SlaData {
  window_days: number;
  total_runs: number;
  failed_runs: number;
  pass_rate: number | null;
  measured: boolean;
  trend: TrendPoint[];
}

const SlaDashboard: React.FC = () => {
  const [data, setData] = useState<SlaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSla = async () => {
      try {
        const response = await fetch('/api/enterprise/sla');
        if (!response.ok) throw new Error('Failed to fetch run statistics');
        const json = await response.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSla();
  }, []);

  if (loading) return <div className="text-slate-500 animate-pulse">Loading run statistics...</div>;
  if (error) return <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-md">Error: {error}</div>;
  if (!data) return null;

  // No runs recorded yet is a real state, and saying so is better than
  // rendering zeroes that look like a measurement.
  if (!data.measured) {
    return (
      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">No runs recorded</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Nothing has been recorded in the last {data.window_days} days. Run{' '}
          <code className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-800">cherenkov verify</code>{' '}
          or <code className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-800">cherenkov validate</code>{' '}
          and these statistics will be counted from the local run store.
        </p>
      </div>
    );
  }

  const passRateColor =
    data.pass_rate === null || data.pass_rate >= 90 ? 'text-green-500' : 'text-amber-500';
  const maxRuns = Math.max(...data.trend.map((p) => p.runs), 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <CheckCircle className="w-4 h-4 mr-2" />
            Runs ({data.window_days}d)
          </div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">
            {data.total_runs.toLocaleString()}
          </div>
          <div className="text-xs text-slate-400 mt-2">Counted from the local run store</div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Failed Runs
          </div>
          <div className="text-3xl font-bold text-red-500">{data.failed_runs.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-2">Verdict FAIL</div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <Activity className="w-4 h-4 mr-2" />
            Pass Rate
          </div>
          <div className={`text-3xl font-bold ${passRateColor}`}>
            {data.pass_rate === null ? '—' : `${data.pass_rate}%`}
          </div>
          <div className="text-xs text-slate-400 mt-2">Of runs with a verdict</div>
        </div>
      </div>

      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Runs per day</h3>
        <div className="h-48 flex items-end space-x-1">
          {data.trend.map((point) => {
            const height = point.runs === 0 ? 2 : Math.round((point.runs / maxRuns) * 100);
            const hasFailures = point.failed > 0;
            return (
              <div
                key={point.date}
                className={`flex-1 rounded-t-sm ${
                  hasFailures
                    ? 'bg-red-400 dark:bg-red-800/70'
                    : 'bg-indigo-300 dark:bg-indigo-900/60'
                }`}
                style={{ height: `${height}%` }}
                title={`${point.date}: ${point.runs} run(s), ${point.failed} failed`}
              />
            );
          })}
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-2">
          <span>{data.trend[0]?.date}</span>
          <span>{data.trend[data.trend.length - 1]?.date}</span>
        </div>
      </div>
    </div>
  );
};

export default SlaDashboard;
