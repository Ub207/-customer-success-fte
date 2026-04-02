import { useState } from 'react';

// ─── Mock data ────────────────────────────────────────────────────────────────
const MOCK_EMAILS = [
  {
    id: 'msg_001',
    ticket_id: 'TKT-2841',
    from_name: 'Ahmed Khan',
    from_email: 'ahmed@company.com',
    subject: 'Cannot reset my password',
    preview: 'I have been trying to reset my password for the last 2 hours...',
    body: 'I have been trying to reset my password for the last 2 hours. The reset email never arrives in my inbox. I checked spam as well. My account email is ahmed@company.com. This is blocking me from doing my work.',
    received_at: '2026-03-31T09:14:00Z',
    status: 'replied',
    ai_reply: 'Hi Ahmed,\n\nThank you for reaching out! I\'ve looked into your account and can see the issue.\n\nThe reset emails were being filtered by your email provider\'s security rules. I\'ve whitelisted our domain on your account.\n\nPlease try requesting a password reset again — it should arrive within 2 minutes.\n\nIf you still face issues, reply to this email and I\'ll escalate to our account team immediately.\n\nBest regards,\nTechCorp AI Support',
    category: 'account',
    priority: 'high',
    sentiment: 0.35,
    escalated: false,
    latency_ms: 1840,
  },
  {
    id: 'msg_002',
    ticket_id: 'TKT-2842',
    from_name: 'Sara Malik',
    from_email: 'sara@startup.io',
    subject: 'Billing charge question — urgent',
    preview: 'I was charged twice this month for my subscription...',
    body: 'I was charged twice this month for my subscription. My invoice number is INV-9921. Please refund the duplicate charge immediately. This is unacceptable.',
    received_at: '2026-03-31T10:02:00Z',
    status: 'escalated',
    ai_reply: 'Hi Sara,\n\nI sincerely apologize for this billing issue. I\'ve reviewed your account and confirmed the duplicate charge on invoice INV-9921.\n\nThis has been escalated to our Billing Team (billing@techcorp.io) with HIGH priority. They will process your refund within 4 hours and email you a confirmation.\n\nTicket reference: TKT-2842\n\nSorry again for the inconvenience.\n\nTechCorp AI Support',
    category: 'billing',
    priority: 'urgent',
    sentiment: 0.18,
    escalated: true,
    escalated_to: 'billing@techcorp.io',
    latency_ms: 2100,
  },
  {
    id: 'msg_003',
    ticket_id: 'TKT-2843',
    from_name: 'Usman Farooq',
    from_email: 'usman@freelance.pk',
    subject: 'How to add a team member?',
    preview: 'Quick question — I want to add my colleague to my workspace...',
    body: 'Quick question — I want to add my colleague to my workspace. I looked in settings but could not find the option. Can you guide me?',
    received_at: '2026-03-31T11:30:00Z',
    status: 'replied',
    ai_reply: 'Hi Usman,\n\nGreat question! Adding a team member is easy:\n\n1. Go to Settings → Team → Members\n2. Click "Invite Member"\n3. Enter their email address\n4. Choose their role (Admin/Editor/Viewer)\n5. Click Send Invite\n\nThey\'ll receive an email and can join immediately.\n\nLet me know if you need any help!\n\nTechCorp AI Support',
    category: 'general',
    priority: 'low',
    sentiment: 0.82,
    escalated: false,
    latency_ms: 1650,
  },
  {
    id: 'msg_004',
    ticket_id: 'TKT-2844',
    from_name: 'Zainab Ali',
    from_email: 'zainab@enterprise.com',
    subject: 'API rate limit issue in production',
    preview: 'Our integration is hitting 429 errors every 10 minutes...',
    body: 'Our integration is hitting 429 Too Many Requests errors every 10 minutes during peak hours. We are on the Business plan. Is there a way to increase our rate limit? This is affecting our production system.',
    received_at: '2026-03-31T12:45:00Z',
    status: 'processing',
    ai_reply: null,
    category: 'technical',
    priority: 'high',
    sentiment: 0.52,
    escalated: false,
    latency_ms: null,
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-PK', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-PK', { month: 'short', day: 'numeric' });
}

const STATUS_CONFIG = {
  replied:    { label: 'Replied',    bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500'  },
  escalated:  { label: 'Escalated', bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' },
  processing: { label: 'Processing',bg: 'bg-blue-100',   text: 'text-blue-700',   dot: 'bg-blue-500 animate-pulse' },
  pending:    { label: 'Pending',   bg: 'bg-gray-100',   text: 'text-gray-600',   dot: 'bg-gray-400'   },
};

const PRIORITY_CONFIG = {
  urgent: { label: 'Urgent', bg: 'bg-red-100',    text: 'text-red-700'    },
  high:   { label: 'High',   bg: 'bg-orange-100', text: 'text-orange-700' },
  medium: { label: 'Medium', bg: 'bg-yellow-100', text: 'text-yellow-700' },
  low:    { label: 'Low',    bg: 'bg-gray-100',   text: 'text-gray-500'   },
};

function SentimentBar({ score }) {
  const pct = Math.round(score * 100);
  const color = score < 0.3 ? 'bg-red-500' : score < 0.6 ? 'bg-yellow-500' : 'bg-green-500';
  const label = score < 0.3 ? 'Negative' : score < 0.6 ? 'Neutral' : 'Positive';
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Sentiment</span>
        <span className={score < 0.3 ? 'text-red-600' : score < 0.6 ? 'text-yellow-600' : 'text-green-600'}>
          {label} ({pct}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Flow Diagram ─────────────────────────────────────────────────────────────
function FlowDiagram() {
  const steps = [
    { icon: '✉️', label: 'Customer Email', sub: 'customer sends email' },
    { icon: '🔔', label: 'Pub/Sub Notify', sub: 'Google notifies server' },
    { icon: '📥', label: 'Webhook Hit', sub: 'POST /webhooks/gmail' },
    { icon: '🔓', label: 'Decode + Fetch', sub: 'base64 → Gmail API' },
    { icon: '📨', label: 'Kafka Queue', sub: 'gmail_inbound topic' },
    { icon: '🤖', label: 'AI Agent', sub: '5 tools, GPT-4o' },
    { icon: '📤', label: 'Gmail Reply', sub: 'send_gmail_reply()' },
  ];
  return (
    <div className="bg-gray-900 rounded-xl p-5 mb-6">
      <p className="text-xs text-gray-400 mb-3 font-mono uppercase tracking-wider">Gmail Flow — How it works</p>
      <div className="flex flex-wrap items-center gap-1">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className="text-center">
              <div className="bg-gray-800 rounded-lg px-3 py-2 min-w-[80px]">
                <div className="text-lg">{s.icon}</div>
                <div className="text-xs text-white font-medium leading-tight">{s.label}</div>
                <div className="text-xs text-gray-400 leading-tight">{s.sub}</div>
              </div>
            </div>
            {i < steps.length - 1 && (
              <span className="text-gray-500 text-lg font-bold">→</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Email Row ────────────────────────────────────────────────────────────────
function EmailRow({ email, selected, onClick }) {
  const status = STATUS_CONFIG[email.status] || STATUS_CONFIG.pending;
  const priority = PRIORITY_CONFIG[email.priority] || PRIORITY_CONFIG.medium;
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-indigo-50 transition-colors ${
        selected ? 'bg-indigo-50 border-l-4 border-l-indigo-500' : 'border-l-4 border-l-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-semibold text-sm text-gray-900 truncate">{email.from_name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${priority.bg} ${priority.text}`}>
              {priority.label}
            </span>
          </div>
          <p className="text-sm text-gray-700 truncate font-medium">{email.subject}</p>
          <p className="text-xs text-gray-400 truncate mt-0.5">{email.preview}</p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className="text-xs text-gray-400">{formatTime(email.received_at)}</span>
          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${status.bg} ${status.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>
        </div>
      </div>
    </button>
  );
}

// ─── Email Detail ─────────────────────────────────────────────────────────────
function EmailDetail({ email }) {
  const [tab, setTab] = useState('original');
  const status = STATUS_CONFIG[email.status] || STATUS_CONFIG.pending;
  const priority = PRIORITY_CONFIG[email.priority] || PRIORITY_CONFIG.medium;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-5 border-b border-gray-200">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{email.subject}</h2>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
              <span>From:</span>
              <span className="font-medium text-gray-700">{email.from_name}</span>
              <span className="text-gray-400">&lt;{email.from_email}&gt;</span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              {formatDate(email.received_at)} at {formatTime(email.received_at)}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <span className="text-xs font-mono text-indigo-600 bg-indigo-50 px-2 py-1 rounded">
              {email.ticket_id}
            </span>
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-medium ${status.bg} ${status.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
              {status.label}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priority.bg} ${priority.text}`}>
              {priority.label}
            </span>
          </div>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-500">Channel</div>
            <div className="text-sm font-semibold text-gray-800 flex items-center justify-center gap-1">
              ✉️ Gmail
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-500">AI Latency</div>
            <div className="text-sm font-semibold text-gray-800">
              {email.latency_ms ? `${(email.latency_ms / 1000).toFixed(1)}s` : '—'}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-500">Escalated</div>
            <div className="text-sm font-semibold text-gray-800">
              {email.escalated ? `✅ ${email.escalated_to?.split('@')[0]}` : '❌ No'}
            </div>
          </div>
        </div>

        <div className="mt-3">
          <SentimentBar score={email.sentiment} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {['original', 'ai_reply'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-medium transition-colors ${
              tab === t
                ? 'border-b-2 border-indigo-500 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'original' ? '📧 Original Email' : '🤖 AI Reply'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {tab === 'original' ? (
          <div className="bg-gray-50 rounded-xl p-4">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
              {email.body}
            </pre>
          </div>
        ) : email.ai_reply ? (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">AI</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">TechCorp AI Support</p>
                <p className="text-xs text-gray-400">support@techcorp.io → {email.from_email}</p>
              </div>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                {email.ai_reply}
              </pre>
            </div>
            {email.latency_ms && (
              <p className="text-xs text-gray-400 mt-2 text-right">
                Generated in {(email.latency_ms / 1000).toFixed(1)}s via OpenAI Agents SDK
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-40 text-gray-400">
            <div className="w-10 h-10 border-4 border-indigo-300 border-t-indigo-600 rounded-full animate-spin mb-3" />
            <p className="text-sm">AI is processing this email...</p>
            <p className="text-xs mt-1">Kafka worker → Agent → Gmail reply</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────
function StatsBar({ emails }) {
  const total     = emails.length;
  const replied   = emails.filter(e => e.status === 'replied').length;
  const escalated = emails.filter(e => e.status === 'escalated').length;
  const avgMs     = emails.filter(e => e.latency_ms).reduce((a, e) => a + e.latency_ms, 0)
                  / emails.filter(e => e.latency_ms).length;

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {[
        { label: 'Total Emails',     value: total,                      color: 'text-gray-900'   },
        { label: 'AI Replied',       value: replied,                    color: 'text-green-600'  },
        { label: 'Escalated',        value: escalated,                  color: 'text-orange-600' },
        { label: 'Avg Response',     value: `${(avgMs/1000).toFixed(1)}s`, color: 'text-indigo-600' },
      ].map((s) => (
        <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-3 text-center shadow-sm">
          <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function GmailDashboard() {
  const [selected, setSelected] = useState(MOCK_EMAILS[0]);
  const [filter, setFilter]     = useState('all');

  const filtered = filter === 'all'
    ? MOCK_EMAILS
    : MOCK_EMAILS.filter(e => e.status === filter);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Nav */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-gray-900">Gmail Channel</span>
              <span className="ml-2 text-xs text-gray-400">AI Customer Success FTE</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Pub/Sub Active
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-5">
        {/* Flow Diagram */}
        <FlowDiagram />

        {/* Stats */}
        <StatsBar emails={MOCK_EMAILS} />

        {/* Filter tabs */}
        <div className="flex gap-2 mb-3">
          {['all', 'replied', 'escalated', 'processing'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                filter === f
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-600 hover:border-indigo-300'
              }`}
            >
              {f === 'all' ? `All (${MOCK_EMAILS.length})` : f}
            </button>
          ))}
        </div>

        {/* Email split view */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
             style={{ height: '600px', display: 'grid', gridTemplateColumns: '340px 1fr' }}>
          {/* Left: email list */}
          <div className="border-r border-gray-200 overflow-y-auto">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Inbox — {filtered.length} emails
              </p>
            </div>
            {filtered.map(email => (
              <EmailRow
                key={email.id}
                email={email}
                selected={selected?.id === email.id}
                onClick={() => setSelected(email)}
              />
            ))}
          </div>

          {/* Right: detail */}
          <div className="overflow-hidden">
            {selected
              ? <EmailDetail email={selected} />
              : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <p>Select an email to view details</p>
                </div>
              )
            }
          </div>
        </div>

        {/* Code explanation */}
        <div className="mt-6 bg-gray-900 rounded-xl p-5 text-sm font-mono">
          <p className="text-green-400 mb-3"># gmail_handler.py — key functions</p>
          <p className="text-gray-400">
            <span className="text-blue-400">parse_gmail_pubsub</span>
            <span className="text-white">(data)</span>
            <span className="text-gray-500">  # base64 decode → historyId, emailAddress</span>
          </p>
          <p className="text-gray-400 mt-1">
            <span className="text-blue-400">process_notification</span>
            <span className="text-white">(history_id)</span>
            <span className="text-gray-500">  # Gmail API → actual email content</span>
          </p>
          <p className="text-gray-400 mt-1">
            <span className="text-blue-400">send_gmail_reply</span>
            <span className="text-white">(to, subject, body)</span>
            <span className="text-gray-500">  # Google service account → reply</span>
          </p>
          <p className="text-yellow-400 mt-3"># Kafka topics</p>
          <p className="text-gray-400">
            <span className="text-white">gmail_inbound</span>
            <span className="text-gray-500">  → worker picks up → AI Agent processes → </span>
            <span className="text-white">gmail_outbound</span>
          </p>
        </div>
      </div>
    </div>
  );
}
