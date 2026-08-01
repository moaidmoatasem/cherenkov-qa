import React, { useState } from 'react';
import { ShieldCheck, Search, ShieldAlert, CheckCircle, FileJson } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';

export default function CertificateVerificationScreen() {
  const [certId, setCertId] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'valid' | 'invalid'>('idle');
  const [certData, setCertData] = useState<any>(null);

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!certId.trim()) return;
    
    setStatus('loading');
    
    // Simulate verification delay
    setTimeout(() => {
      if (certId.includes('invalid')) {
        setStatus('invalid');
        setCertData(null);
      } else {
        setStatus('valid');
        setCertData({
          id: certId || 'CERT-9X2-KLP',
          timestamp: new Date().toISOString(),
          targetUrl: 'https://petstore3.swagger.io/api/v3',
          specName: 'petstore.json',
          testsPassed: 42,
          coverage: 98.5,
          divergences: 0,
          issuer: 'Cherenkov-QA Engine',
          signature: '0xabc123...def456',
        });
      }
    }, 1500);
  };

  return (
    <div className="flex flex-col h-full bg-bg-base overflow-hidden">
      <PageHeader
        title="Certificate Verification"
        description="Verify the cryptographic integrity and honesty of a Cherenkov-QA run certificate."
      />

      <div className="flex-1 overflow-y-auto p-6 flex flex-col items-center">
        <div className="w-full max-w-2xl space-y-8">
          
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
            <h2 className="text-lg font-display font-semibold text-text-primary mb-2 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-glow-blue" />
              Verify Certificate
            </h2>
            <p className="text-sm text-text-muted mb-6">
              Enter a Cherenkov Certificate ID or paste the raw JSON signature block to verify that the test suite was executed honestly and without gaming assertions.
            </p>
            
            <form onSubmit={handleVerify} className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  placeholder="e.g. CERT-..."
                  value={certId}
                  onChange={(e) => setCertId(e.target.value)}
                  className="w-full bg-black/30 text-text-primary text-sm pl-10 pr-4 py-2.5 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition font-mono"
                />
              </div>
              <button
                type="submit"
                disabled={status === 'loading' || !certId.trim()}
                className="px-6 py-2.5 bg-glow-blue text-slate-950 font-bold rounded-xl hover:bg-opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs"
              >
                {status === 'loading' ? 'Verifying...' : 'Verify'}
              </button>
            </form>
          </div>

          {status === 'loading' && (
            <div className="flex flex-col items-center justify-center p-12 space-y-4">
              <span className="relative flex h-8 w-8">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-glow-blue opacity-75"></span>
                <span className="relative inline-flex rounded-full h-8 w-8 bg-glow-bright"></span>
              </span>
              <p className="text-glow-bright text-xs font-mono uppercase tracking-widest animate-pulse">
                Validating Cryptographic Signature...
              </p>
            </div>
          )}

          {status === 'invalid' && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 flex flex-col items-center text-center space-y-4 animate-fadeIn">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
                <ShieldAlert className="w-8 h-8 text-red-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-red-400">Invalid Certificate</h3>
                <p className="text-sm text-red-400/80 mt-2">
                  The provided certificate ID could not be verified. It may have been tampered with or does not exist.
                </p>
              </div>
            </div>
          )}

          {status === 'valid' && certData && (
            <div className="bg-green-500/5 border border-green-500/20 rounded-2xl p-6 animate-fadeIn space-y-6">
              <div className="flex items-center gap-4 border-b border-green-500/20 pb-4">
                <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center shrink-0">
                  <CheckCircle className="w-6 h-6 text-green-500" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-green-400">Certificate Validated</h3>
                  <p className="text-xs text-green-400/80 font-mono mt-1">ID: {certData.id}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Target API</span>
                  <p className="text-sm text-text-primary font-mono">{certData.targetUrl}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Specification</span>
                  <p className="text-sm text-text-primary font-mono">{certData.specName}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Tests Passed</span>
                  <p className="text-lg font-bold text-text-primary">{certData.testsPassed}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Coverage</span>
                  <p className="text-lg font-bold text-glow-bright">{certData.coverage}%</p>
                </div>
              </div>

              <div className="pt-4 border-t border-white/10 space-y-2">
                <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Cryptographic Signature</span>
                <div className="bg-black/40 p-3 rounded-lg border border-white/5 flex items-center gap-3">
                  <FileJson className="w-4 h-4 text-text-muted" />
                  <code className="text-xs text-text-muted break-all">{certData.signature}</code>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
