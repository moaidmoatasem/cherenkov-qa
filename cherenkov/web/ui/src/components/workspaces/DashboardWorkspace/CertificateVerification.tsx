/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, FileJson } from 'lucide-react';
import { Card } from '../../ui';
import { verifyCertificate, CertificateVerifyResult } from '../../../lib/api';

type Status = 'idle' | 'loading' | 'done' | 'error';

const VERDICT_STYLE: Record<string, string> = {
  PASS: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  WARN: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  FAIL: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
};

export const CertificateVerification: React.FC = () => {
  const [raw, setRaw] = useState('');
  const [signingKey, setSigningKey] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<CertificateVerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!raw.trim()) return;

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setStatus('error');
      setError('Not valid JSON — paste the full certificate produced by `cherenkov certify --output cert.json`.');
      setResult(null);
      return;
    }

    setStatus('loading');
    setError(null);
    try {
      const res = await verifyCertificate(parsed, signingKey.trim() || undefined);
      setResult(res);
      setStatus('done');
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
      setStatus('error');
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="certificate-verification">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>Verify Certificate</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Paste a certificate produced by <code className="font-mono">cherenkov certify --output cert.json</code> to
          check its SHA-256 fingerprint (and HMAC signature, if signed) for tampering.
        </p>
      </div>

      <form onSubmit={handleVerify} className="space-y-3">
        <textarea
          data-testid="certificate-json-input"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder='{ "cert_id": "...", "fingerprint": "...", ... }'
          rows={5}
          className="w-full bg-black/30 text-text-primary text-xs font-mono pl-3 pr-3 py-2.5 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition resize-y"
        />
        <div className="flex gap-3">
          <input
            type="text"
            value={signingKey}
            onChange={(e) => setSigningKey(e.target.value)}
            placeholder="Signing key (hex, optional)"
            className="flex-1 bg-black/30 text-text-primary text-xs pl-3 pr-3 py-2 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition font-mono"
          />
          <button
            type="submit"
            disabled={status === 'loading' || !raw.trim()}
            className="px-6 py-2 bg-glow-blue text-slate-950 font-bold rounded-xl hover:bg-opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs"
          >
            {status === 'loading' ? 'Verifying...' : 'Verify'}
          </button>
        </div>
      </form>

      {status === 'error' && error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 flex items-start gap-3 text-sm text-rose-400">
          <ShieldX className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {status === 'done' && result && (
        <div
          className={`rounded-xl border p-4 space-y-3 ${
            result.valid ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-rose-500/30 bg-rose-500/5'
          }`}
          data-testid="certificate-result"
        >
          <div className="flex items-center gap-3">
            {result.valid ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-rose-400" />
            )}
            <div>
              <p className={`text-sm font-bold ${result.valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                {result.valid ? 'Fingerprint intact' : 'Tampered or invalid'}
              </p>
              <p className="text-[10px] text-text-muted font-mono">{result.cert_id}</p>
            </div>
            <span
              className={`ml-auto text-[10px] font-bold px-2 py-1 rounded-full border uppercase tracking-wider ${
                VERDICT_STYLE[result.verdict] || ''
              }`}
            >
              {result.verdict}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Subject</span>
              <p className="text-text-primary font-mono truncate">{result.subject.base_url}</p>
            </div>
            <div>
              <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Divergences</span>
              <p className="text-text-primary font-mono">
                {result.summary.total} (HIGH={result.summary.high} MED={result.summary.medium} LOW=
                {result.summary.low})
              </p>
            </div>
            <div>
              <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Issued</span>
              <p className="text-text-primary font-mono">{result.issued_at}</p>
            </div>
            <div>
              <span className="text-[10px] uppercase text-text-muted font-bold tracking-wider">Signature</span>
              <p className="text-text-primary font-mono">{result.signature_present ? 'present' : 'unsigned'}</p>
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

export default CertificateVerification;
