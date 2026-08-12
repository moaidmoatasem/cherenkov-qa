import React, { useState } from 'react';
import { Shield, Activity, Users, Settings } from 'lucide-react';
import SlaDashboard from './SlaDashboard';
import CompliancePanel from './CompliancePanel';
import SupportPortal from './SupportPortal';

type Tab = 'sla' | 'compliance' | 'support';

const EnterpriseWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('sla');

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 p-6 overflow-y-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-indigo-500" />
          Enterprise Command Center
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Manage SLA, SOC2, GDPR, and Multi-tenant settings for your organization.
        </p>
      </header>

      <div className="flex space-x-1 border-b border-slate-200 dark:border-slate-800 mb-6">
        <button
          onClick={() => setActiveTab('sla')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'sla'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            SLA Dashboard
          </div>
        </button>
        <button
          onClick={() => setActiveTab('compliance')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'compliance'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Compliance (SOC2 / GDPR)
          </div>
        </button>
        <button
          onClick={() => setActiveTab('support')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'support'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Support Portal
          </div>
        </button>
      </div>

      <div className="flex-1 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-6 shadow-sm">
        {activeTab === 'sla' && <SlaDashboard />}
        {activeTab === 'compliance' && <CompliancePanel />}
        {activeTab === 'support' && <SupportPortal />}
      </div>
    </div>
  );
};

export default EnterpriseWorkspace;
