/** @license SPDX-License-Identifier: Apache-2.0 */

import React, { useState } from 'react';
import { Brain, Search, Database } from 'lucide-react';
import { Card, PageHeader, MockBadge, EmptyState, Skeleton } from './ui';
import { queryKnowledge } from '../lib/api';

export default function KnowledgeExplorerScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await queryKnowledge(query.trim());
      setResults(data || []);
    } catch (err) {
      setError((err as Error).message);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="knowledge-screen">
      <PageHeader
        title="Knowledge Explorer"
        description="Query the Second Brain knowledge mesh for insights, learnings, and patterns."
      />
      <MockBadge />

      <form onSubmit={handleSubmit} className="flex gap-3 items-start">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7D8DA1]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the knowledge mesh..."
            className="w-full bg-black/30 text-text-primary text-sm pl-10 pr-4 py-2.5 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition placeholder:text-[#7D8DA1]/60"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-5 py-2.5 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold text-xs rounded-xl uppercase font-mono tracking-wider transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Brain className="w-4 h-4" />
          <span>Query</span>
        </button>
      </form>

      {error && (
        <EmptyState
          icon={<Database />}
          title="Query Failed"
          description={error}
          primaryAction={{
            label: "Retry",
            onClick: () => handleSubmit({ preventDefault: () => {} } as React.FormEvent)
          }}
        />
      )}

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-5 space-y-3">
              <Skeleton className="h-4 w-24 rounded" />
              <Skeleton className="h-3 w-full rounded" />
              <Skeleton className="h-3 w-3/4 rounded" />
            </Card>
          ))}
        </div>
      )}

      {!isLoading && !error && results.length === 0 && query && (
        <EmptyState
          icon={<Brain />}
          title="No Results"
          description="Your query returned no results. Try a different search term."
        />
      )}

      {!isLoading && !error && results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((item: any, idx: number) => (
            <Card key={item.id || idx} className="p-5 space-y-3 hover:border-glow-blue/30 transition-all duration-200">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-glow-bright">
                  {item.source || 'knowledge'}
                </span>
                {item.confidence !== undefined && (
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                    item.confidence >= 0.8
                      ? 'bg-green-500/10 text-green-400 border-green-500/20'
                      : item.confidence >= 0.5
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-red-500/10 text-red-400 border-red-500/20'
                  }`}>
                    {Math.round(item.confidence * 100)}%
                  </span>
                )}
              </div>
              <p className="text-sm text-text-primary leading-relaxed">
                {typeof item.data === 'string' ? item.data : item.data?.text || item.data?.content || JSON.stringify(item.data)}
              </p>
              {item.metadata && (
                <div className="text-[10px] text-[#7D8DA1]/75 font-mono">
                  {item.metadata.endpoint && <span>Endpoint: {item.metadata.endpoint}</span>}
                  {item.metadata.timestamp && <span className="ml-2">{item.metadata.timestamp}</span>}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
