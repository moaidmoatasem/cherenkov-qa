/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, FileJson } from 'lucide-react';
import { Card } from '../../ui';
import { verifyCertificate, CertificateVerifyResult } from '../../../lib/api';

type Status = 'idle' | 'loading' | 'done' | 'error';

export const CertificateVerificationPanel: React.FC = () => {
  const [raw, setRaw] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<CertificateVerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!raw.trim()) return;

    let parsed: object;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setStatus('error');
      setError('Not valid JSON — paste the full certificate object produced by `cherenkov certify`.');
      setResult(null);
      return;
    }

    setStatus('loading');
    setError(null);
    try {
      const verdict = await verifyCertificate(parsed);
      setResult(verdict);
      setStatus('done');
    } catch (err) {
      setStatus('error');
      setError((err as Error).message);
      setResult(null);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="certificate-verification-panel">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>Certificate Verification</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Paste a Cherenkov certificate (from <code>cherenkov certify</code>) to re-derive its SHA-256
          fingerprint and confirm it hasn&apos;t been tampered with.
        </p>
      </div>

      <form onSubmit={handleVerify} className="space-y-3">
        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder='{"cert_id": "...", "run_id": "...", "fingerprint": "...", ...}'
          rows={5}
          className="w-full bg-black/30 text-text-primary text-xs font-mono p-3 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition resize-y"
        />
        <button
          type="submit"
          disabled={status === 'loading' || !raw.trim()}
          className="px-6 py-2.5 bg-glow-blue text-slate-950 font-bold rounded-xl hover:bg-opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs"
        >
          {status === 'loading' ? 'Verifying...' : 'Verify'}
        </button>
      </form>

      {status === 'error' && error && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-start gap-3">
          <ShieldX className="w-5 h-5 text-rose-400 shrink-0" />
          <p className="text-sm text-rose-400/90">{error}</p>
        </div>
      )}

      {status === 'done' && result && (
        <div
          className={`rounded-xl p-4 border space-y-3 ${
            result.valid
              ? 'bg-[#3FB950]/5 border-[#3FB950]/20'
              : 'bg-rose-500/10 border-rose-500/20'
          }`}
        >
          <div className="flex items-center gap-3">
            {result.valid ? (
              <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0" />
            ) : (
              <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0" />
            )}
            <div>
              <h3 className={`text-sm font-bold ${result.valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                {result.valid ? 'Fingerprint verified — not tampered' : 'Fingerprint mismatch — do not trust this certificate'}
              </h3>
              <p className="text-[10px] font-mono text-text-muted mt-0.5">
                cert_id={result.cert_id} · run_id={result.run_id}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="block text-[10px] uppercase text-text-muted tracking-wider">Verdict</span>
              <span className="font-mono font-bold text-text-primary">{result.verdict}</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase text-text-muted tracking-wider">Issued</span>
              <span className="font-mono text-text-primary">{new Date(result.issued_at).toLocaleString()}</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase text-text-muted tracking-wider">Divergences</span>
              <span className="font-mono text-text-primary">{result.summary.total}</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase text-text-muted tracking-wider">Signed</span>
              <span className="font-mono text-text-primary">{result.signed ? 'Yes (HMAC)' : 'No'}</span>
            </div>
          </div>

          <div className="pt-2 border-t border-white/10 flex items-center gap-2">
            <FileJson className="w-3.5 h-3.5 text-text-muted shrink-0" />
            <code className="text-[10px] text-text-muted break-all">{result.fingerprint}</code>
          </div>
        </div>
      )}
    </Card>
  );
};

export default CertificateVerificationPanel;
