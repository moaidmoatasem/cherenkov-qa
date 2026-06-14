import React, { useState, useEffect, useRef } from 'react';
import {
  PageHeader,
  Card,
  SeverityPill,
  StatusDot,
  ProvenanceChip,
  Drawer,
  useToast,
  EmptyState
} from './ui';
import { fetchDivergences, actOnDivergence } from '../lib/api';
import { Divergence, SeverityType, StatusType } from '../types';
import { Search, ShieldAlert, ArrowRight, BookOpen, ExternalLink, HelpCircle, Copy, CheckCircle } from 'lucide-react';

export default function DivergencesScreen() {
  const { toast } = useToast();
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [selectedDiv, setSelectedDiv] = useState<Divergence | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  // Filters
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const listRef = useRef<HTMLDivElement>(null);

  const [linkCopied, setLinkCopied] = useState(false);

  // Load divergences
  useEffect(() => {
    fetchDivergences().then(data => {
      setDivergences(data);
      const params = new URLSearchParams(window.location.search);
      const divId = params.get('divergence');
      if (divId) {
        const found = data.find(d => d.id === divId);
        if (found) {
          setSelectedDiv(found);
        }
      }
    });
  }, []);

  // Filter logic
  const filtered = divergences.filter((d) => {
    const safeDClass = d.divergenceClass ? String(d.divergenceClass).trim().toUpperCase() : '';
    const safeCFilter = classFilter ? classFilter.trim().toUpperCase() : 'ALL';
    const matchesClass = safeCFilter === 'ALL' || safeDClass === safeCFilter;

    const safeDSeverity = d.severity ? String(d.severity).trim().toLowerCase() : '';
    const safeSFilter = severityFilter ? severityFilter.trim().toLowerCase() : 'all';
    const matchesSeverity = safeSFilter === 'all' || safeDSeverity === safeSFilter;

    const safeDStatus = d.status ? String(d.status).trim().toLowerCase() : '';
    const safeStFilter = statusFilter ? statusFilter.trim().toLowerCase() : 'all';
    const matchesStatus = safeStFilter === 'all' || safeDStatus === safeStFilter;

    const matchesSearch = !searchQuery || searchQuery.trim() === '' ||
      (d.endpoint && d.endpoint.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (d.claimB && d.claimB.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesClass && matchesSeverity && matchesStatus && matchesSearch;
  });

  // Keyboard navigation (j/k to move focus, Enter to open)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // If modal or drawer or input has focus, ignore
      if (document.activeElement?.tagName === 'INPUT' || selectedDiv) return;

      if (e.key === 'j') {
        e.preventDefault();
        setFocusedIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : prev));
      } else if (e.key === 'k') {
        e.preventDefault();
        setFocusedIndex((prev) => (prev > 0 ? prev - 1 : 0));
      } else if (e.key === 'Enter') {
        if (focusedIndex >= 0 && filtered[focusedIndex]) {
          e.preventDefault();
          setSelectedDiv(filtered[focusedIndex]);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filtered, focusedIndex, selectedDiv]);

  // Actions
  const handleAction = async (id: string, action: 'close_with_test' | 'mark_intended' | 'reject', reason?: string) => {
    // Capture previous state for rollback
    const previousState = divergences.find(d => d.id === id)?.status;
    const targetStatus: StatusType = action === 'mark_intended' ? 'rejected' : 'pending';

    setDivergences((prev) =>
      prev.map((d) => (d.id === id ? { ...d, status: targetStatus } : d))
    );

    try {
      await actOnDivergence(id, action, reason);

      if (action === 'close_with_test') {
        toast(`Divergence resolved by emitting client test suite.`, 'success');
      } else if (action === 'mark_intended') {
        toast(`Divergence resolved: marked intended behaviour.`, 'success');
      } else {
        toast(`Divergence rejected. Reflector will filter this noise.`, 'info');
      }

      // Close drawer on action
      setSelectedDiv(null);
    } catch (err) {
      toast(`Action failed: unable to update divergence state.`, 'danger');
      if (previousState) {
        // Rollback state immediately
        setDivergences((prev) =>
          prev.map((d) => (d.id === id ? { ...d, status: previousState } : d))
        );
      }
    }
  };

  const getDivergenceClassLabel = (c: string) => {
    const mapping: Record<string, string> = {
      D1: 'D1: Spec ↔ Code',
      D2: 'D2: Code ↔ Prod',
      D3: 'D3: UI ↔ Spec',
      D4: 'D4: DB ↔ Code',
      D5: 'D5: Spec ↔ Prod'
    };
    return mapping[c] || c;
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-bg-base text-text-primary" data-testid="divergences-screen">
      <PageHeader
        title="Divergence Triage Hub"
        description="Review and resolve inconsistencies between system components, specifications, and databases."
      />

      {/* Filter Bar */}
      <div className="border-b border-border-custom bg-bg-panel p-4 flex flex-col md:flex-row gap-4 items-center justify-between z-10 shrink-0">
        <div className="relative w-full md:max-w-xs">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
          <input
            id="divergences-search"
            name="divergences-search"
            type="text"
            placeholder="Search endpoints or details..."
            value={searchQuery}
            data-testid="search-input"
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setFocusedIndex(-1);
            }}
            className="w-full pl-9 pr-4 py-2 bg-white/5 border border-border-custom rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-glow-blue/50 text-text-primary"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Class filter */}
          <select
            value={classFilter}
            onChange={(e) => { setClassFilter(e.target.value); setFocusedIndex(-1); }}
            data-testid="class-filter"
            className="px-3 py-1.5 bg-white/5 border border-border-custom rounded-lg text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-glow-blue/50 text-text-primary cursor-pointer"
          >
            <option value="ALL" className="bg-bg-base">ALL CLASSES</option>
            <option value="D1" className="bg-bg-base">D1: SPEC ↔ CODE</option>
            <option value="D2" className="bg-bg-base">D2: CODE ↔ PROD</option>
            <option value="D3" className="bg-bg-base">D3: UI ↔ SPEC</option>
            <option value="D4" className="bg-bg-base">D4: DB ↔ CODE</option>
            <option value="D5" className="bg-bg-base">D5: SPEC ↔ PROD</option>
          </select>

          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setFocusedIndex(-1); }}
            data-testid="severity-filter"
            className="px-3 py-1.5 bg-white/5 border border-border-custom rounded-lg text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-glow-blue/50 text-text-primary cursor-pointer"
          >
            <option value="ALL" className="bg-bg-base">ALL SEVERITIES</option>
            <option value="critical" className="bg-bg-base">CRITICAL</option>
            <option value="high" className="bg-bg-base">HIGH</option>
            <option value="medium" className="bg-bg-base">MEDIUM</option>
            <option value="low" className="bg-bg-base">LOW</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setFocusedIndex(-1); }}
            className="px-3 py-1.5 bg-white/5 border border-border-custom rounded-lg text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-glow-blue/50 text-text-primary cursor-pointer"
          >
            <option value="ALL" className="bg-bg-base">ALL STATUSES</option>
            <option value="reproduced" className="bg-bg-base">REPRODUCED</option>
            <option value="pending" className="bg-bg-base">PENDING</option>
            <option value="rejected" className="bg-bg-base">REJECTED</option>
          </select>
        </div>
      </div>

      {/* Main List */}
      <div ref={listRef} className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="divergence-list">
        <div className="flex justify-between items-center text-xs text-text-muted mb-2 select-none font-mono">
          <span>Keyboard: Navigate list with <kbd className="px-1 text-[10px] bg-white/5 border rounded">j</kbd>/<kbd className="px-1 text-[10px] bg-white/5 border rounded">k</kbd>, open with <kbd className="px-1 text-[10px] bg-white/5 border rounded">Enter</kbd></span>
          <span>Showing {filtered.length} of {divergences.length} active findings</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={ShieldAlert}
            title="No Divergences Match Filters"
            description="Adjust your search query or dropdown filter selections to find other items."
            primaryAction={{
              label: 'Reset Filters',
              onClick: () => {
                setClassFilter('ALL');
                setSeverityFilter('ALL');
                setStatusFilter('ALL');
                setSearchQuery('');
              }
            }}
          />
        ) : (
          filtered.map((d, index) => {
            const isFocused = index === focusedIndex;
            return (
              <Card
                key={d.id}
                hoverable
                onClick={() => {
                  setSelectedDiv(d);
                  setFocusedIndex(index);
                }}
                className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 border transition-all duration-150
                  ${isFocused ? 'border-glow-blue bg-white/[0.08] shadow-[0_0_12px_rgba(34,211,238,0.15)]' : 'border-border-custom'}`}
              >
                <div className="flex items-start gap-4 min-w-0">
                  <div className="flex flex-col gap-1.5 shrink-0 mt-0.5">
                    <SeverityPill severity={d.severity} />
                    <span className="text-[10px] font-mono font-bold text-text-muted text-center">
                      {d.id}
                    </span>
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-glow-bright bg-cyan-950/40 px-2 py-0.5 rounded border border-glow-blue/20">
                        {getDivergenceClassLabel(d.divergenceClass)}
                      </span>
                      <span className="text-sm font-mono font-semibold text-text-primary truncate">
                        {d.endpoint}
                      </span>
                    </div>
                    <p className="text-sm text-text-muted line-clamp-1">
                      {d.claimB}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                  <ProvenanceChip type={d.divergenceClass === 'D1' ? 'spec' : d.divergenceClass === 'D4' ? 'db' : d.divergenceClass === 'D3' ? 'code' : 'traffic'} />
                  <StatusDot status={d.status} showLabel />
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-primary transition-colors hidden sm:block" />
                </div>
              </Card>
            );
          })
        )}
      </div>

      {/* Drawer details */}
      <Drawer
        isOpen={!!selectedDiv}
        onClose={() => setSelectedDiv(null)}
        title={`Divergence Detail · ${selectedDiv?.id || ''}`}
      >
        {selectedDiv && (
          <div className="space-y-6">
            {/* Header info */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <SeverityPill severity={selectedDiv.severity} />
                <StatusDot status={selectedDiv.status} showLabel />
                <ProvenanceChip type={selectedDiv.divergenceClass === 'D1' ? 'spec' : selectedDiv.divergenceClass === 'D4' ? 'db' : selectedDiv.divergenceClass === 'D3' ? 'code' : 'traffic'} />
              </div>
              <button
                onClick={async () => {
                  const url = new URL(window.location.href);
                  url.searchParams.set('divergence', selectedDiv.id);
                  await navigator.clipboard.writeText(url.toString());
                  setLinkCopied(true);
                  setTimeout(() => setLinkCopied(false), 2000);
                  toast('Divergence link copied to clipboard.', 'success');
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white/5 border border-white/10 hover:bg-glow-blue/20 hover:border-glow-blue/50 hover:text-glow-bright text-xs font-semibold text-text-primary transition cursor-pointer"
                title="Copy link to divergence"
              >
                {linkCopied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                Share
              </button>
            </div>

            {/* Confidence Bar */}
            {selectedDiv.confidence !== undefined && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[10px] text-[#7D8DA1] font-mono tracking-wider uppercase">
                  <span>Engine Confidence</span>
                  <span className={selectedDiv.confidence > 0.8 ? 'text-emerald-400' : selectedDiv.confidence > 0.5 ? 'text-amber-400' : 'text-rose-400'}>
                    {Math.round(selectedDiv.confidence * 100)}%
                  </span>
                </div>
                <div className="w-full bg-black/40 h-1.5 rounded-full overflow-hidden border border-white/10">
                  <div
                    style={{ width: `${Math.round(selectedDiv.confidence * 100)}%` }}
                    className={`h-full rounded-full transition-all duration-500 ${selectedDiv.confidence > 0.8 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : selectedDiv.confidence > 0.5 ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]'}`}
                  />
                </div>
              </div>
            )}

            {/* Path description */}
            <div>
              <h3 className="text-xs font-bold font-mono text-[#7D8DA1] tracking-wider uppercase mb-1">Target Endpoint</h3>
              <p className="text-sm font-mono font-bold text-text-primary bg-white/5 px-3 py-1.5 rounded-lg border border-border-custom">
                {selectedDiv.endpoint}
              </p>
            </div>

            {/* Claim A vs Claim B */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-border-custom rounded-xl p-4 bg-white/[0.02]">
                <h4 className="text-xs font-bold font-mono text-glow-bright tracking-wider uppercase mb-2">Claim A (Expected)</h4>
                <pre className="text-xs font-mono text-text-primary whitespace-pre-wrap break-all bg-black/25 p-2 rounded border border-white/5">
                  {selectedDiv.claimA}
                </pre>
              </div>
              <div className="border border-border-custom rounded-xl p-4 bg-white/[0.02]">
                <h4 className="text-xs font-bold font-mono text-danger-custom tracking-wider uppercase mb-2">Claim B (Actual Behaviour)</h4>
                <p className="text-xs text-text-primary leading-relaxed mb-2">
                  {selectedDiv.claimB}
                </p>
              </div>
            </div>

            {/* Evidence Diff */}
            <div>
              <h3 className="text-xs font-bold font-mono text-[#7D8DA1] tracking-wider uppercase mb-2">Evidence payload</h3>
              <div className="border border-border-custom rounded-xl p-4 bg-bg-panel font-mono text-xs text-danger-custom whitespace-pre overflow-x-auto">
                {selectedDiv.evidence}
              </div>
            </div>

            {/* Repro Steps */}
            <div>
              <h3 className="text-xs font-bold font-mono text-[#7D8DA1] tracking-wider uppercase mb-2">Independent Repro Steps</h3>
              <div className="border border-border-custom rounded-xl p-4 bg-black/40 font-mono text-xs text-text-primary whitespace-pre overflow-x-auto relative group">
                {selectedDiv.reproSteps}
              </div>
            </div>

            {/* Actions panel */}
            <div className="pt-4 border-t border-border-custom flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => handleAction(selectedDiv.id, 'close_with_test')}
                className="flex-1 py-2 px-4 rounded-lg bg-glow-blue hover:bg-glow-bright text-bg-base font-semibold text-sm transition-all shadow-[0_0_12px_rgba(34,211,238,0.2)] cursor-pointer"
              >
                Close with Test
              </button>

              <button
                onClick={() => handleAction(selectedDiv.id, 'mark_intended')}
                className="flex-1 py-2 px-4 rounded-lg border border-border-custom bg-white/5 hover:bg-white/10 text-text-primary font-semibold text-sm transition-all cursor-pointer"
              >
                Mark Intended
              </button>

              <button
                onClick={() => handleAction(selectedDiv.id, 'reject')}
                className="py-2 px-4 rounded-lg border border-danger-custom/30 bg-danger-custom/10 hover:bg-danger-custom/20 text-danger-custom font-semibold text-sm transition-all cursor-pointer"
              >
                Reject (Noise)
              </button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
