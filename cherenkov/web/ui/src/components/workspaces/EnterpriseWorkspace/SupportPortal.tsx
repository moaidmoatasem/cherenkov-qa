import React, { useState } from 'react';
import { LifeBuoy, FileDown, Send, MessageSquare } from 'lucide-react';

const SupportPortal: React.FC = () => {
  const [ticketMsg, setTicketMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketMsg.trim()) return;

    setSubmitting(true);
    setResult(null);

    try {
      const res = await fetch('/api/enterprise/support/ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: ticketMsg }),
      });
      const data = await res.json();
      if (!res.ok) {
        // The endpoint answers 501: there is no ticketing backend. It previously
        // returned a random UUID and this component reported "created successfully",
        // so the user was told their message had reached someone when it had not.
        // Surface the server's explanation instead of inventing success.
        setResult(data?.detail ?? `Support ticketing is unavailable (HTTP ${res.status}).`);
        return;
      }
      setResult(`Ticket ${data.ticket_id} created successfully.`);
      setTicketMsg('');
    } catch (e: any) {
      setResult(`Failed to create ticket: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center mb-10">
        <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/50 rounded-full flex items-center justify-center mx-auto mb-4">
          <LifeBuoy className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
        </div>
        <h2 className="text-2xl font-bold">Enterprise Support Portal</h2>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          Priority 24/7 technical support and diagnostic tools for enterprise customers.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Diagnostic Bundle */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2 mb-2">
              <FileDown className="w-5 h-5 text-indigo-500" />
              Diagnostic Bundle
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
              Download a complete diagnostic archive containing obfuscated logs, configuration snapshots, and telemetry to attach to your support requests.
            </p>
          </div>
          <button className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium rounded-md transition-colors">
            <FileDown className="w-4 h-4" />
            Generate Debug Bundle
          </button>
        </div>

        {/* Create Ticket */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-2">
            <MessageSquare className="w-5 h-5 text-indigo-500" />
            Open a Ticket
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Our SLA guarantees a response within 1 hour for critical issues.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <textarea
              className="w-full h-32 p-3 text-sm bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md focus:ring-2 focus:ring-indigo-500 outline-none"
              placeholder="Describe your issue..."
              value={ticketMsg}
              onChange={(e) => setTicketMsg(e.target.value)}
              disabled={submitting}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">
                {result ? (
                  <span className={result.includes('Failed') ? 'text-red-500' : 'text-green-500'}>
                    {result}
                  </span>
                ) : 'Markdown supported.'}
              </span>
              <button
                type="submit"
                disabled={submitting || !ticketMsg.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
              >
                <Send className="w-4 h-4" />
                {submitting ? 'Submitting...' : 'Submit Ticket'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SupportPortal;
