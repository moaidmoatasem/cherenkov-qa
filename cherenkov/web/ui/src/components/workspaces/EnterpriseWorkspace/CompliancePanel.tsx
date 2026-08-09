import React, { useState } from 'react';
import { Shield, FileText, Download, Trash2, CheckCircle2, AlertCircle } from 'lucide-react';

const CompliancePanel: React.FC = () => {
  const [purging, setPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState<string | null>(null);

  const handlePurge = async () => {
    if (!window.confirm("Are you sure you want to trigger a manual GDPR data purge? This action cannot be undone.")) return;
    
    setPurging(true);
    setPurgeResult(null);
    try {
      const res = await fetch('/api/enterprise/gdpr/purge', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setPurgeResult(`Successfully purged ${data.purged_records} records in compliance with retention policy.`);
      } else {
        setPurgeResult(`Error: ${data.message || 'Unknown error'}`);
      }
    } catch (e: any) {
      setPurgeResult(`Failed to trigger purge: ${e.message}`);
    } finally {
      setPurging(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* SOC2 Section */}
      <section className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-indigo-500" />
              SOC 2 Type II Reporting
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
              Generate real-time SOC 2 compliance reports outlining access controls, availability metrics, and processing integrity for your audit requirements.
            </p>
          </div>
          <a
            href="/api/enterprise/soc2/report"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-md transition-colors"
          >
            <Download className="w-4 h-4" />
            Download Latest Report
          </a>
        </div>
        
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <div>
              <div className="text-sm font-medium">Security</div>
              <div className="text-xs text-slate-500">100% Operational</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <div>
              <div className="text-sm font-medium">Availability</div>
              <div className="text-xs text-slate-500">100% Operational</div>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800">
            <AlertCircle className="w-5 h-5 text-amber-500" />
            <div>
              <div className="text-sm font-medium">Privacy</div>
              <div className="text-xs text-slate-500">85% Operational</div>
            </div>
          </div>
        </div>
      </section>

      {/* GDPR Section */}
      <section className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-bold flex items-center gap-2 mb-2">
          <Shield className="w-5 h-5 text-indigo-500" />
          GDPR Data Management
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-2xl mb-6">
          Manage data retention policies and execute manual data purges to satisfy "Right to be Forgotten" requests.
        </p>

        <div className="flex flex-col sm:flex-row gap-6">
          <div className="flex-1 space-y-4">
            <div>
              <div className="text-sm font-medium mb-1">Data Retention Period</div>
              <div className="text-sm text-slate-500 bg-white dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-800">
                90 Days (Default)
              </div>
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Anonymize on Delete</div>
              <div className="text-sm text-slate-500 bg-white dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-800">
                Enabled
              </div>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col justify-center items-start border-l border-slate-200 dark:border-slate-800 pl-6">
            <h3 className="text-sm font-medium mb-2">Manual Actions</h3>
            <button
              onClick={handlePurge}
              disabled={purging}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              {purging ? 'Purging Data...' : 'Trigger Manual Purge'}
            </button>
            {purgeResult && (
              <p className="text-xs mt-3 text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-950 p-2 rounded border border-slate-200 dark:border-slate-800 w-full">
                {purgeResult}
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

export default CompliancePanel;
