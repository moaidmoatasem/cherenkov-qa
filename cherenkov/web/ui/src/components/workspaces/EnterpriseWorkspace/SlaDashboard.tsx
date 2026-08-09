import React, { useEffect, useState } from 'react';
import { Activity, Clock, CheckCircle, AlertTriangle } from 'lucide-react';

interface SlaData {
  uptime: number;
  api_response_p99: number;
  total_checks: number;
  failed_checks: number;
  status: string;
}

const SlaDashboard: React.FC = () => {
  const [data, setData] = useState<SlaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSla = async () => {
      try {
        const response = await fetch('/api/enterprise/sla');
        if (!response.ok) throw new Error('Failed to fetch SLA data');
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

  if (loading) return <div className="text-slate-500 animate-pulse">Loading SLA metrics...</div>;
  if (error) return <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-md">Error: {error}</div>;
  if (!data) return null;

  const uptimeColor = data.uptime >= 99.9 ? 'text-green-500' : 'text-amber-500';

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Uptime Card */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <Activity className="w-4 h-4 mr-2" />
            Uptime (30d)
          </div>
          <div className={`text-3xl font-bold ${uptimeColor}`}>{data.uptime}%</div>
          <div className="text-xs text-slate-400 mt-2">Target: 99.9%</div>
        </div>

        {/* Latency Card */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <Clock className="w-4 h-4 mr-2" />
            P99 Response
          </div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{data.api_response_p99} ms</div>
          <div className="text-xs text-slate-400 mt-2">Target: &lt; 200 ms</div>
        </div>

        {/* Total Checks */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <CheckCircle className="w-4 h-4 mr-2" />
            Checks Executed
          </div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{data.total_checks.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-2">Across all environments</div>
        </div>

        {/* Failed Checks */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Failed Checks
          </div>
          <div className="text-3xl font-bold text-red-500">{data.failed_checks.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-2">Requires triage</div>
        </div>
      </div>

      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">API Reliability Trend</h3>
        <div className="h-48 flex items-end space-x-2">
          {/* Mocking a bar chart for the last 30 days */}
          {Array.from({ length: 30 }).map((_, i) => {
            const height = Math.floor(Math.random() * 40) + 60;
            const isToday = i === 29;
            return (
              <div 
                key={i} 
                className={`flex-1 rounded-t-sm ${isToday ? 'bg-indigo-500' : 'bg-indigo-200 dark:bg-indigo-900/50 hover:bg-indigo-300 dark:hover:bg-indigo-800/80 transition-colors'}`}
                style={{ height: `${height}%` }}
                title={`Day ${i + 1}: ${height}% uptime`}
              />
            );
          })}
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-2">
          <span>30 Days Ago</span>
          <span>Today</span>
        </div>
      </div>
    </div>
  );
};

export default SlaDashboard;
