/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Plus, MessageSquare } from 'lucide-react';
import { Card } from '../../ui';
import { createChatSession, fetchChatSessions, fetchChatMessages, streamChatMessage, ChatSessionSummary } from '../../../lib/api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const SseChatAssistant: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    createChatSession('qa_assistant')
      .then((data) => setSessionId(data.session_id))
      .catch(() => setError('Failed to initialize AI Chat session.'));

    fetchChatSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!sessionId || !input.trim() || isStreaming) return;
    const userText = input.trim();
    setInput('');
    setError(null);

    setMessages((prev) => [...prev, { role: 'user', content: userText }, { role: 'assistant', content: '' }]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChatMessage(
        sessionId,
        userText,
        (token) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant') {
              next[next.length - 1] = { role: 'assistant', content: last.content + token };
            }
            return next;
          });
        },
        controller.signal
      );
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        setError(err.message || 'Stream error');
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const handleNewSession = async () => {
    try {
      const data = await createChatSession('qa_assistant');
      setSessionId(data.session_id);
      setMessages([]);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Card className="p-6 space-y-4 flex flex-col h-96" data-testid="sse-chat-assistant">
      <div className="flex items-center justify-between border-b border-white/10 pb-3 shrink-0">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <span>AI Copilot (SSE Streamed Chat)</span>
          </h2>
          <p className="text-[11px] text-text-muted mt-0.5 font-mono">
            Connected to <code className="font-mono">/api/v1/chat/sessions/{sessionId || '...'}</code>
          </p>
        </div>
        <button
          onClick={handleNewSession}
          className="px-2 py-1 bg-white/5 hover:bg-white/10 text-cyan-400 border border-white/10 rounded-lg text-xs font-mono flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" /> New Chat
        </button>
      </div>

      {/* Message Output Box */}
      <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-1">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-text-muted text-xs">
            Ask any question about test coverage, API drift, or Playwright assertions.
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={idx} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role === 'assistant' && (
                <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div
                className={`p-3 rounded-xl max-w-[80%] leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/30'
                    : 'bg-black/30 text-text-primary border border-white/10'
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content || (isStreaming && idx === messages.length - 1 ? '...' : '')}</p>
              </div>
              {m.role === 'user' && (
                <div className="w-6 h-6 rounded-full bg-white/10 text-text-muted flex items-center justify-center shrink-0">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="text-xs text-rose-400 font-mono">{error}</div>}

      {/* Input Bar */}
      <div className="flex gap-2 shrink-0 pt-2 border-t border-white/10">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask AI assistant..."
          disabled={isStreaming}
          className="flex-1 bg-bg-base text-text-primary text-xs p-2.5 rounded-lg border border-white/10 focus:outline-none focus:border-cyan-400 font-mono"
          data-testid="chat-input"
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className="px-4 py-2.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border border-cyan-500/40 rounded-lg text-xs font-mono font-bold flex items-center justify-center"
          data-testid="chat-send-btn"
        >
          {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </Card>
  );
};

export default SseChatAssistant;
