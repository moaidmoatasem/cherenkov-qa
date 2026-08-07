/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Skeleton, EmptyState } from '../../ui';
import { queryKnowledge } from '../../../lib/api';
import { Brain, Search, Database, FilePenLine } from 'lucide-react';

export const KnowledgeGraphExplorer: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // J3: turn a knowledge node into a natural-language authoring intent and
  // deep-link into the Authoring workspace, which pre-fills its prompt.
  const authorPattern = (item: any) => {
    const raw =
      typeof item.data === 'string'
        ? item.data
        : item.data?.text || item.text || item.content || item.source || '';
    const firstSentence = raw.split(/[.?!]\s/)[0]?.slice(0, 140) || raw.slice(0, 140);
    return `Author a check derived from knowledge: ${firstSentence}`.slice(0, 220);
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await queryKnowledge(query.trim());
      setResults(data?.data || data?.results || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="knowledge-graph-explorer">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <span>GraphRAG Second Brain Knowledge Explorer</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Query the GraphRAG Second Brain knowledge mesh via <code className="font-mono">/api/v1/knowledge/query</code>.
        </p>
      </div>

      <form onSubmit={handleQuery} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search API concepts, past test failures, or domain graph..."
            className="w-full bg-bg-base text-text-primary text-xs pl-9 pr-3 py-2 rounded-lg border border-white/10 focus:outline-none focus:border-cyan-400 font-mono"
            data-testid="knowledge-search-input"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-lg text-xs font-mono font-bold flex items-center gap-1"
        >
          <Brain className="w-4 h-4" /> Query Mesh
        </button>
      </form>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Knowledge Query Failed: {error}
        </div>
      ) : results.length === 0 ? (
        <EmptyState
          icon={Brain}
          title="No Knowledge Matches"
          description="Type a search query above to inspect GraphRAG memory nodes."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto">
          {results.map((item: any, idx: number) => (
            <div key={idx} className="p-3 rounded-xl bg-black/30 border border-white/10 space-y-1 font-mono text-xs">
              <div className="flex items-center justify-between text-[10px] text-cyan-400 font-bold uppercase">
                <span>{item.source || 'Graph Node'}</span>
                <span>{item.confidence ? `${Math.round(item.confidence * 100)}%` : 'Active'}</span>
              </div>
              <p className="text-text-primary text-xs leading-relaxed">
                {typeof item.data === 'string' ? item.data : item.text || item.content || JSON.stringify(item)}
              </p>
              <div className="pt-2">
                <button
                  onClick={() => navigate(`/authoring?intent=${encodeURIComponent(authorPattern(item))}`)}
                  className="px-2.5 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px] font-mono font-bold flex items-center gap-1.5 transition cursor-pointer"
                  data-testid="btn-author-this-check"
                >
                  <FilePenLine className="w-3 h-3" />
                  Author this check
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export default KnowledgeGraphExplorer;
