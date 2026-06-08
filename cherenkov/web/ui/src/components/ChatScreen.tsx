/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare, Bot, User, Loader2 } from 'lucide-react';
import { PageHeader } from './ui';
import { createChatSession } from '../lib/api';

interface ChatMessage {
  role: string;
  content: string;
}

export default function ChatScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    createChatSession()
      .then((data) => setSessionId(data.session_id))
      .catch(() => setError('Failed to create chat session'));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const sendMessage = async () => {
    if (!sessionId || !input.trim() || isStreaming) return;

    const userMessage: ChatMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setError(null);

    const assistantMessage: ChatMessage = { role: 'assistant', content: '' };
    setMessages((prev) => [...prev, assistantMessage]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`/api/v1/chat/sessions/${sessionId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userMessage.content }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Stream request failed: ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          let eventType = '';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }

          if (eventType === 'token' && eventData) {
            try {
              const parsed = JSON.parse(eventData);
              const token = parsed.token || '';
              accumulated += token;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: 'assistant', content: accumulated };
                return updated;
              });
            } catch {
              accumulated += eventData;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: 'assistant', content: accumulated };
                return updated;
              });
            }
          }

          if (eventType === 'complete') {
            setIsStreaming(false);
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to send message');
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: 'An error occurred. Please try again.',
          };
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="h-full flex flex-col grid-bg bg-transparent relative z-10" id="chat-screen">
      <PageHeader
        title="Chat"
        description="Interact with the CHERENKOV assistant using natural language via SSE streaming."
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-60">
            <MessageSquare className="w-12 h-12 text-[#7D8DA1]" />
            <p className="text-sm text-[#7D8DA1]">
              Start a conversation with the CHERENKOV assistant.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-8 h-8 rounded-full bg-glow-blue/10 border border-glow-blue/30 flex items-center justify-center">
                <Bot className="w-4 h-4 text-glow-bright" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-glow-blue/20 border border-glow-blue/30 text-text-primary'
                  : 'bg-white/5 border border-white/10 text-[#E6EDF3]'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === 'assistant' && isStreaming && idx === messages.length - 1 && (
                <span className="inline-block w-1.5 h-4 bg-glow-bright animate-pulse ml-0.5 align-middle" />
              )}
            </div>
            {msg.role === 'user' && (
              <div className="shrink-0 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
                <User className="w-4 h-4 text-[#7D8DA1]" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="px-6 pb-2">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      <div className="p-4 border-t border-white/10 bg-black/20 backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-3 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={sessionId ? 'Type a message...' : 'Initializing session...'}
            disabled={!sessionId || isStreaming}
            className="flex-1 bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-sm text-text-primary placeholder-[#7D8DA1] focus:outline-none focus:border-glow-blue/50 transition disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!sessionId || !input.trim() || isStreaming}
            className="shrink-0 w-11 h-11 rounded-xl bg-glow-blue hover:bg-opacity-90 text-slate-950 flex items-center justify-center transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
