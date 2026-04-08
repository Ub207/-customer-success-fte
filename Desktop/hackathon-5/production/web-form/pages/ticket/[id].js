import Head from 'next/head';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

const STATUS_STYLES = {
  open:        { bg: 'bg-yellow-50',  border: 'border-yellow-300', text: 'text-yellow-800',  dot: 'bg-yellow-400',  label: 'Open' },
  processing:  { bg: 'bg-blue-50',    border: 'border-blue-300',   text: 'text-blue-800',    dot: 'bg-blue-400',    label: 'Processing' },
  resolved:    { bg: 'bg-green-50',   border: 'border-green-300',  text: 'text-green-800',   dot: 'bg-green-500',   label: 'Resolved' },
  escalated:   { bg: 'bg-red-50',     border: 'border-red-300',    text: 'text-red-800',     dot: 'bg-red-500',     label: 'Escalated to Human' },
  closed:      { bg: 'bg-gray-50',    border: 'border-gray-300',   text: 'text-gray-700',    dot: 'bg-gray-400',    label: 'Closed' },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.open;
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium border ${s.bg} ${s.border} ${s.text}`}>
      <span className={`w-2 h-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function MessageBubble({ msg }) {
  const isAgent = msg.role === 'agent';
  return (
    <div className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap shadow-sm ${
          isAgent
            ? 'bg-white border border-gray-200 text-gray-800'
            : 'bg-indigo-600 text-white'
        }`}
      >
        <p className={`text-xs mb-1 font-medium ${isAgent ? 'text-gray-400' : 'text-indigo-200'}`}>
          {isAgent ? 'AI Support Agent' : 'You'} &bull;{' '}
          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
        </p>
        {msg.content}
      </div>
    </div>
  );
}

export default function TicketStatusPage() {
  const router = useRouter();
  const { id } = router.query;

  const [ticket, setTicket]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  async function fetchTicket() {
    if (!id) return;
    try {
      const res = await fetch(`${API_URL}/web-form/ticket/${id}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setTicket(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Initial fetch + auto-refresh every 15 s while ticket is open/processing
  useEffect(() => {
    fetchTicket();
  }, [id]);

  useEffect(() => {
    if (!ticket) return;
    if (ticket.status === 'resolved' || ticket.status === 'closed') return;
    const interval = setInterval(fetchTicket, 15_000);
    return () => clearInterval(interval);
  }, [ticket]);

  return (
    <>
      <Head>
        <title>Ticket {id ? id.slice(0, 8) : '...'} — TechCorp Support</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 shadow-sm">
          <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="font-bold text-gray-900 text-lg">TechCorp Support</span>
            </div>
            <a href="/" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              New Request
            </a>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-10">
          {loading && (
            <div className="text-center py-20 text-gray-500">
              <svg className="animate-spin h-8 w-8 text-indigo-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading ticket...
            </div>
          )}

          {error && !loading && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
              <p className="text-red-700 font-medium mb-2">Could not load ticket</p>
              <p className="text-red-600 text-sm mb-4">{error}</p>
              <button
                onClick={fetchTicket}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          )}

          {ticket && !loading && (
            <div className="space-y-6">
              {/* Ticket header card */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                <div className="flex items-start justify-between flex-wrap gap-4">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Ticket ID</p>
                    <p className="font-mono text-sm font-semibold text-gray-700 break-all">{id}</p>
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>

                <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Channel</p>
                    <p className="font-medium text-gray-700 capitalize">{ticket.channel?.replace('_', ' ') || 'Web Form'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Created</p>
                    <p className="font-medium text-gray-700">
                      {ticket.created_at ? new Date(ticket.created_at).toLocaleString() : '—'}
                    </p>
                  </div>
                  {ticket.last_updated && (
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Last Update</p>
                      <p className="font-medium text-gray-700">{new Date(ticket.last_updated).toLocaleString()}</p>
                    </div>
                  )}
                </div>

                {ticket.status !== 'resolved' && ticket.status !== 'closed' && (
                  <div className="mt-4 flex items-center gap-2 text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-2">
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Auto-refreshing every 15 seconds…
                  </div>
                )}
              </div>

              {/* Conversation thread */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                <h2 className="text-sm font-semibold text-gray-700 mb-4">Conversation</h2>
                {ticket.messages && ticket.messages.length > 0 ? (
                  <div className="space-y-4">
                    {ticket.messages.map((msg, i) => (
                      <MessageBubble key={msg.id || i} msg={msg} />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 text-center py-6">
                    Your message has been received. Our AI agent is reviewing it now.
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3 justify-center">
                <a
                  href="/"
                  className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors"
                >
                  Submit Another Request
                </a>
                <button
                  onClick={fetchTicket}
                  className="px-5 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Refresh Now
                </button>
              </div>
            </div>
          )}
        </main>

        <footer className="text-center pb-8 text-xs text-gray-400">
          <p>
            Need immediate help?{' '}
            <a href="mailto:support@techcorp.io" className="text-indigo-500 hover:underline">
              support@techcorp.io
            </a>
          </p>
          <p className="mt-1">&copy; {new Date().getFullYear()} TechCorp SaaS. All rights reserved.</p>
        </footer>
      </div>
    </>
  );
}
