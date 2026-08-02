/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card, Skeleton, EmptyState } from '../../ui';
import {
  fetchReviewQueue,
  approveTestScenario,
  rejectTestScenario,
  explainTestScenario,
  editTestScenario,
  ReviewQueueItem,
  REJECTION_REASONS,
} from '../../../lib/api';
import { CheckSquare, CheckCircle2, XCircle, AlertTriangle, Sparkles, RefreshCw, Code } from 'lucide-react';

export const HitlReviewQueue: React.FC = () => {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<string>(REJECTION_REASONS[0].value);
  const [rejectNote, setRejectNote] = useState('');
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [editingCode, setEditingCode] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);

  const loadQueue = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchReviewQueue();
      setItems(data || []);
      if (data && data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
        setEditingCode(data[0].generated_test || '');
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const selectedItem = items.find((i) => i.id === selectedId) || items[0];

  const handleApprove = async (id: string) => {
    try {
      await approveTestScenario(id);
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status: 'approved' } : item)));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectTestScenario(id, rejectReason, rejectNote);
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status: 'rejected' } : item)));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleExplain = async (id: string) => {
    setIsExplaining(true);
    try {
      const res = await explainTestScenario(id);
      setAiExplanation(res.explanation);
    } catch (err) {
      setAiExplanation((err as Error).message);
    } finally {
      setIsExplaining(false);
    }
  };

  const handleSaveEdit = async (id: string) => {
    try {
      await editTestScenario(id, editingCode);
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, generated_test: editingCode } : item))
      );
      setIsEditing(false);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="hitl-review-queue">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-cyan-400" />
            <span>HITL Test Review Queue</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Human-In-The-Loop review gate connected to <code className="font-mono">/api/v1/review/*</code>.
          </p>
        </div>
        <button
          onClick={loadQueue}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Refresh Review Queue"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Queue error: {error}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title="Review Queue Empty"
          description="All generated test scenarios have been reviewed and approved."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Queue List (Left Column) */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setSelectedId(item.id);
                  setEditingCode(item.generated_test || '');
                  setAiExplanation(null);
                }}
                className={`w-full text-left p-3 rounded-xl border text-xs font-mono transition cursor-pointer ${
                  item.id === selectedItem?.id
                    ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                    : 'bg-black/20 border-white/5 hover:bg-white/5 text-text-primary'
                }`}
                data-testid={`review-item-${item.id}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold uppercase text-glow-bright">{item.method}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                      item.status === 'approved'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : item.status === 'rejected'
                        ? 'bg-rose-500/20 text-rose-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <p className="truncate font-semibold">{item.endpoint}</p>
                <p className="text-[10px] text-text-muted mt-1">
                  Confidence: {Math.round((item.confidence || 0.5) * 100)}%
                </p>
              </button>
            ))}
          </div>

          {/* Selected Item Review & Action Details (Right Column) */}
          {selectedItem && (
            <div className="lg:col-span-2 space-y-4 p-4 rounded-xl bg-black/30 border border-white/10 text-xs font-mono">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div>
                  <span className="text-glow-bright font-bold uppercase mr-2">{selectedItem.method}</span>
                  <span className="font-bold text-text-primary">{selectedItem.endpoint}</span>
                </div>
                <span className="text-text-muted text-[10px]">ID: {selectedItem.id}</span>
              </div>

              {/* Code Preview / Editor */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase text-text-muted">Generated Test Code:</span>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="text-[10px] text-cyan-400 hover:underline"
                  >
                    {isEditing ? 'Cancel Edit' : 'Edit Code'}
                  </button>
                </div>
                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      rows={6}
                      value={editingCode}
                      onChange={(e) => setEditingCode(e.target.value)}
                      className="w-full bg-black/50 text-emerald-400 p-3 rounded-lg border border-cyan-500/30 text-xs font-mono focus:outline-none"
                    />
                    <button
                      onClick={() => handleSaveEdit(selectedItem.id)}
                      className="px-3 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded text-xs"
                    >
                      Save Code Edits
                    </button>
                  </div>
                ) : (
                  <pre className="p-3 bg-black/50 text-emerald-400 rounded-lg max-h-48 overflow-y-auto text-[11px] leading-relaxed">
                    <code>{selectedItem.generated_test || `// Scenario for ${selectedItem.method} ${selectedItem.endpoint}`}</code>
                  </pre>
                )}
              </div>

              {/* AI Explanation & Actions */}
              {aiExplanation && (
                <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-text-primary text-xs">
                  <p className="font-bold text-cyan-400 flex items-center gap-1 mb-1">
                    <Sparkles className="w-3.5 h-3.5" /> AI Explanation:
                  </p>
                  <p className="text-[11px] leading-relaxed">{aiExplanation}</p>
                </div>
              )}

              <div className="flex items-center gap-2 pt-2 border-t border-white/10">
                <button
                  onClick={() => handleApprove(selectedItem.id)}
                  className="flex-1 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40 rounded-lg font-bold flex items-center justify-center gap-1 transition"
                  data-testid="btn-approve-scenario"
                >
                  <CheckCircle2 className="w-4 h-4" /> Approve
                </button>
                <button
                  onClick={() => handleReject(selectedItem.id)}
                  className="flex-1 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/40 rounded-lg font-bold flex items-center justify-center gap-1 transition"
                  data-testid="btn-reject-scenario"
                >
                  <XCircle className="w-4 h-4" /> Reject
                </button>
                <button
                  onClick={() => handleExplain(selectedItem.id)}
                  disabled={isExplaining}
                  className="px-3 py-2 bg-white/5 hover:bg-white/10 text-cyan-400 border border-white/10 rounded-lg font-bold flex items-center gap-1 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Explain
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default HitlReviewQueue;
