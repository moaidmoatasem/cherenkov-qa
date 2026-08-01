import React, { useState } from 'react';
import { Award, FileText } from 'lucide-react';
import { PageHeader, Card, MockBadge } from '../components/ui';
import IntegrityHeatmap from '../components/IntegrityHeatmap';

export default function CoverageScreen() {
  const [certHistory] = useState<any[]>([
    { id: 'cert-1', date: '2026-07-28', score: 92, target: 'prod-eu-west', status: 'valid' },
    { id: 'cert-2', date: '2026-07-25', score: 85, target: 'staging-01', status: 'superseded' },
  ]);

  // TODO(Phase B): the /api/v1/integrity/audit endpoint already exists (cherenkov/integrity/api.py)
  // and is not yet wired here — this is static placeholder data, not a backend gap.
  const endpoints = [
    { id: '1', path: '/api/v1/users', method: 'GET', integrityScore: 95, driftCount: 0 },
    { id: '2', path: '/api/v1/users', method: 'POST', integrityScore: 88, driftCount: 1 },
    { id: '3', path: '/api/v1/projects', method: 'GET', integrityScore: 100, driftCount: 0 },
    { id: '4', path: '/api/v1/projects/{id}', method: 'GET', integrityScore: 65, driftCount: 3 },
    { id: '5', path: '/api/v1/auth/login', method: 'POST', integrityScore: 40, driftCount: 5 },
    { id: '6', path: '/api/v1/billing', method: 'GET', integrityScore: 75, driftCount: 2 },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
      <MockBadge />
      <div className="flex items-start justify-between">
        <PageHeader
          title="Coverage & Certification"
          description="The source of truth for your API's integrity. View heatmaps of test coverage and issue verifiable certificates."
          primaryAction={{ label: 'Run Audit', onClick: () => {} }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main Coverage Heatmap (Spans 2 columns) */}
        <div className="lg:col-span-2 space-y-6">
          <IntegrityHeatmap endpoints={endpoints} />
        </div>

        {/* Right side: Certification History */}
        <Card className="p-6 flex flex-col h-full">
          <div className="flex items-center gap-2 mb-4">
            <Award className="w-5 h-5 text-glow-blue" />
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-primary">
              Run Certificates
            </h2>
          </div>
          <p className="text-xs text-text-muted mb-6">
            Signed cryptographic proofs of API integrity, guardrailed against false positives.
          </p>

          <div className="space-y-3 flex-1">
            {certHistory.map((cert) => (
              <div key={cert.id} className="p-3 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-glow-bright">{cert.score}% Integrity</span>
                    {cert.status === 'valid' ? (
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">VALID</span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold uppercase bg-gray-500/10 text-gray-400 border border-gray-500/20">OLD</span>
                    )}
                  </div>
                  <div className="text-[10px] text-text-muted font-mono">{cert.date} · {cert.target}</div>
                </div>
                <button className="p-1.5 rounded-md hover:bg-white/10 text-text-muted hover:text-white transition">
                  <FileText className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <button className="w-full mt-6 py-2 border border-glow-blue/50 bg-glow-blue/10 rounded-xl text-xs font-mono font-semibold text-glow-bright hover:bg-glow-blue/20 transition flex items-center justify-center gap-2 cursor-pointer">
            <Award className="w-3.5 h-3.5" />
            <span>Generate Certificate</span>
          </button>
        </Card>
      </div>
    </div>
  );
}
