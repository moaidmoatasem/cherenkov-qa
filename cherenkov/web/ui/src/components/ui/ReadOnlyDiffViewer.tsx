/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useMemo } from 'react';
import { Copy, Download, X, CheckCircle, Terminal } from 'lucide-react';

interface ReadOnlyDiffViewerProps {
  original: string;
  proposed: string;
  testName?: string;
  onDismiss?: () => void;
}

function buildUnifiedDiff(original: string, proposed: string, fileName: string): string {
  const origLines = original.split('\n');
  const propLines = proposed.split('\n');
  const header = `--- a/${fileName}\n+++ b/${fileName}\n@@ -1,${origLines.length} +1,${propLines.length} @@\n`;
  const removals = origLines.map(l => `-${l}`).join('\n');
  const additions = propLines.map(l => `+${l}`).join('\n');
  return header + removals + '\n' + additions;
}

export function ReadOnlyDiffViewer({ original, proposed, testName = 'test', onDismiss }: ReadOnlyDiffViewerProps) {
  const [copied, setCopied] = React.useState(false);

  const fileName = `${testName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.spec.ts`;

  const diffText = useMemo(() => buildUnifiedDiff(original, proposed, fileName), [original, proposed, fileName]);

  const origLines = original.split('\n');
  const propLines = proposed.split('\n');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(diffText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([diffText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${testName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.patch`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderDiffLine = (line: string, idx: number, type: 'removal' | 'addition') => {
    const isRemoval = type === 'removal';
    return (
      <div
        key={idx}
        className={`flex gap-2 font-mono text-xs px-3 py-0.5 ${
          isRemoval
            ? 'bg-rose-500/10 text-rose-400 border-l-2 border-rose-500'
            : 'bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500'
        }`}
      >
        <span className="select-none w-4 shrink-0">{isRemoval ? '-' : '+'}</span>
        <span className="break-all">{line}</span>
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-white/10 bg-black/30 backdrop-blur-xl overflow-hidden" id="read-only-diff-viewer" data-testid="read-only-diff-viewer">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold font-mono uppercase tracking-wider text-amber-400">⚠ Suggest Only — Review Before Applying</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="btn-diff-copy-cmd"
            data-testid="btn-diff-copy-cmd"
            onClick={async () => {
              const cmd = `cat << 'EOF' | git apply\n${diffText}\nEOF`;
              await navigator.clipboard.writeText(cmd);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-text-primary hover:bg-sky-500/20 hover:border-sky-500/50 hover:text-sky-300 transition cursor-pointer"
            title="Copy command to apply patch via terminal"
          >
            {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Terminal className="w-3.5 h-3.5" />}
            Copy CLI
          </button>
          <button
            id="btn-diff-copy"
            data-testid="btn-diff-copy"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-text-primary hover:bg-glow-blue/20 hover:border-glow-blue/50 hover:text-glow-bright transition cursor-pointer"
          >
            {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy Patch'}
          </button>
          <button
            id="btn-diff-download"
            data-testid="btn-diff-download"
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-text-primary hover:bg-violet-500/20 hover:border-violet-500/50 hover:text-violet-300 transition cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Download .patch
          </button>
          {onDismiss && (
            <button
              id="btn-diff-dismiss"
              data-testid="btn-diff-dismiss"
              onClick={onDismiss}
              className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted hover:text-text-primary transition cursor-pointer"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Diff Body */}
      <div className="max-h-96 overflow-y-auto">
        <div className="py-2">
          {origLines.map((line, i) => renderDiffLine(line, i, 'removal'))}
          <div className="border-t border-white/5 my-1" />
          {propLines.map((line, i) => renderDiffLine(line, i, 'addition'))}
        </div>
      </div>

      {/* Footer note */}
      <div className="px-4 py-2 border-t border-white/10 bg-white/5">
        <p className="text-[10px] text-text-muted font-mono">
          D7 INVARIANT: This diff is read-only. Copy the patch and apply it manually in your editor. CHERENKOV never auto-writes test files.
        </p>
      </div>
    </div>
  );
}
