/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Shield, Award, CheckCircle, Download, FileText } from 'lucide-react';
import { Card, PageHeader, StatusDot, MockBadge } from './ui';
import { fetchGovernance } from '../lib/api';
import { useToast } from './ui/Toast';

export default function GovernanceScreen() {
  const [MOCK_GOVERNANCE, setGov] = useState<any>({ score: 100, issues: [] });
  useEffect(() => {
    fetchGovernance().then(setGov);
  }, []);
  const { addToast } = useToast();

  const handleExport = () => {
    addToast('Compliance audit log export initialized successfully.', 'success');
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="governance-screen">
      <MockBadge />
      <PageHeader
        title="Governance & Model Certification"
        description="Verify LLM model performance tier bounds, audit compliance reports, and trace generated Playwright files to original intents."
        primaryAction={{
          label: 'Export Compliance Log',
          onClick: handleExport,
        }}
      />
      <div className="flex justify-end -mt-4 mb-2">
        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border bg-amber-500/10 text-amber-400 border-amber-500/30">
          MOCK DATA
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* KPI metrics */}
        <Card className="p-5 space-y-4">
          <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Shield className="w-4 h-4 text-glow-blue" />
            <span>Defect Escape & False Positives</span>
          </h3>
          <div className="grid grid-cols-2 gap-4 text-center font-mono">
            <div className="bg-black/20 p-4 border border-white/5 rounded-xl">
              <span className="block text-[10px] text-[#7D8DA1] uppercase">Defect Escape Rate</span>
              <span className="block text-2xl font-bold text-red-400 mt-2">{MOCK_GOVERNANCE.defectEscapeRate}%</span>
            </div>
            <div className="bg-black/20 p-4 border border-white/5 rounded-xl">
              <span className="block text-[10px] text-[#7D8DA1] uppercase">FP Validation Rate</span>
              <span className="block text-2xl font-bold text-[#3FB950] mt-2">{MOCK_GOVERNANCE.falsePositiveRate * 100}%</span>
            </div>
          </div>
        </Card>

        {/* Model Certification */}
        <Card className="p-5 space-y-4">
          <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Award className="w-4 h-4 text-glow-blue" />
            <span>Model Capabilities Certification</span>
          </h3>

          <div className="space-y-3 font-mono text-xs text-[#7D8DA1]">
            {MOCK_GOVERNANCE.modelCertification.map((cert, idx) => (
              <div key={idx} className="flex justify-between items-center p-2.5 rounded border border-white/5 bg-black/10">
                <span className="text-text-primary font-semibold">{cert.tier} Capability Tier</span>
                <div className="flex items-center gap-3">
                  <span>Pass Rate: {cert.passRate}%</span>
                  <StatusDot status="reproduced" />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Traceability log list */}
      <Card className="p-6 space-y-4">
        <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <FileText className="w-4 h-4 text-glow-blue" />
          <span>Artifact Traceability Explorer</span>
        </h3>

        <div className="space-y-3 font-mono text-xs">
          {MOCK_GOVERNANCE.traceability.map((log, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-white/5 bg-black/20 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-glow-bright font-semibold">{log.artifact}</span>
                <span className="text-[10px] text-[#7D8DA1]">Model: {log.model}</span>
              </div>
              <p className="text-text-primary leading-normal">Prompt Intent: {log.prompt}</p>
              <div className="text-[10px] text-[#7D8DA1] pt-1.5 border-t border-white/5">
                Claims Verified count: {log.claimsVerified}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
