import { useState } from 'react';

// ─── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_TICKETS = [
  {
    id: 'WEB-A1B2C3D4',
    db_id: 'a1b2c3d4-0000-0000-0000-000000000001',
    name: 'Fatima Khan',
    email: 'fatima@techstartup.pk',
    subject: 'Integration not working with Zapier',
    message: 'We are trying to connect TechCorp to Zapier but the OAuth flow fails at the authorization step. We get error: "redirect_uri_mismatch". We have tried multiple redirect URIs listed in the docs but none work. Our team is blocked.',
    category: 'technical',
    priority: 'high',
    status: 'resolved',
    submitted_at: '2026-03-31T08:00:00Z',
    resolved_at: '2026-03-31T08:00:02Z',
    sla: '4 hours',
    latency_ms: 1920,
    ai_response: 'Hi Fatima,\n\nThanks for the detailed report. The redirect_uri_mismatch error happens when the URI in your Zapier app settings doesn\'t exactly match what\'s registered in TechCorp.\n\nFix:\n1. Go to TechCorp Developer Settings → OAuth Apps\n2. Add this exact URI: https://zapier.com/dashboard/auth/oauth/return/TechCorp/\n3. Save and retry the Zapier flow\n\nThis is the most common cause. If it still fails, please share a screenshot of your OAuth app settings.\n\nTicket: WEB-A1B2C3D4\nTechCorp AI Support',
    smtp_status: 'sent',
    kafka_topic: 'webform_inbound',
  },
  {
    id: 'WEB-E5F6G7H8',
    db_id: 'e5f6g7h8-0000-0000-0000-000000000002',
    name: 'Omar Siddiqui',
    email: 'omar@agency.com',
    subject: 'Request for bulk discount',
    message: 'We are an agency managing 15 client accounts. We want to know if there is a reseller or bulk discount program available. We are currently paying individually for each account.',
    category: 'billing',
    priority: 'medium',
    status: 'escalated',
    submitted_at: '2026-03-31T09:30:00Z',
    resolved_at: null,
    sla: '8 hours',
    latency_ms: 2050,
    ai_response: 'Hi Omar,\n\nThank you for your interest in our bulk program!\n\nYour request has been forwarded to our Billing Team who handles agency partnerships. They will reach out within 4 hours with pricing details for your 15 accounts.\n\nEscalated to: billing@techcorp.io\nTicket: WEB-E5F6G7H8\n\nTechCorp AI Support',
    smtp_status: 'sent',
    kafka_topic: 'webform_inbound',
    escalated_to: 'billing@techcorp.io',
  },
  {
    id: 'WEB-I9J0K1L2',
    db_id: 'i9j0k1l2-0000-0000-0000-000000000003',
    name: 'Maryam Butt',
    email: 'maryam@nonprofit.org',
    subject: 'Data export feature missing',
    message: 'I cannot find the data export button that was available last month. I need to export all my customer data to CSV for our quarterly report. Is this feature removed?',
    category: 'bug',
    priority: 'medium',
    status: 'resolved',
    submitted_at: '2026-03-31T10:15:00Z',
    resolved_at: '2026-03-31T10:15:02Z',
    sla: '8 hours',
    latency_ms: 1750,
    ai_response: 'Hi Maryam,\n\nThe export button was moved in our latest update (v2.4). New location:\n\nSettings → Data Management → Export → Export to CSV\n\nYou can also export directly from any data table using the "⋮" menu on the right → Export.\n\nFor your quarterly report, I recommend using the "Date Range" filter first to select Q1 2026 before exporting.\n\nLet me know if you need help!\nTechCorp AI Support',
    smtp_status: 'sent',
    kafka_topic: 'webform_inbound',
  },
  {
    id: 'WEB-M3N4O5P6',
    db_id: 'm3n4o5p6-0000-0000-0000-000000000004',
    name: 'Imran Hussain',
    email: 'imran@ecom.pk',
    subject: 'Slow response times on API',
    message: 'Our API calls are taking 8-12 seconds to respond when they used to take under 1 second. This started 2 days ago. Our region is ap-south-1. Is there a known issue?',
    category: 'technical',
    priority: 'urgent',
    status: 'processing',
    submitted_at: '2026-03-31T12:00:00Z',
    resolved_at: null,
    sla: '2 hours',
    latency_ms: null,
    ai_response: null,
    smtp_status: 'pending',
    kafka_topic: 'webform_inbound',
  },
];

const SLA_MAP = {
  urgent: { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Urgent' },
  high:   { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High'   },
  medium: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Medium' },
  low:    { bg: 'bg-gray-100',   text: 'text-gray-500',   label: 'Low'    },
};

const STATUS_MAP = {
  resolved:   { bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500',               label: 'Resolved'   },
  escalated:  { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500',               label: 'Escalated'  },
  processing: { bg: 'bg-blue-100',   text: 'text-blue-700',   dot: 'bg-blue-500 animate-pulse',   label: 'Processing' },
  queued:     { bg: 'bg-gray-100',   text: 'text-gray-600',   dot: 'bg-gray-400',                 label: 'Queued'     },
};

const CAT_ICONS = {
  technical: '⚙️', billing: '💳', account: '👤',
  bug: '🐛', general: '💬', feedback: '⭐', other: '📋',
};

function fmtTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-PK', { hour: '2-digit', minute: '2-digit' });
}
function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-PK', { month: 'short', day: 'numeric' });
}

// ─── Flow Diagram ─────────────────────────────────────────────────────────────
function FlowDiagram() {
  const steps = [
    { icon: '🌐', label: 'Web Form', sub: 'Next.js UI' },
    { icon: '📋', label: 'Validate', sub: 'Pydantic model' },
    { icon: '📨', label: 'Kafka', sub: 'webform_inbound' },
    { icon: '🤖', label: 'AI Agent', sub: 'GPT-4o / Groq' },
    { icon: '🗄️', label: 'PostgreSQL', sub: 'ticket saved' },
    { icon: '📧', label: 'SMTP Reply', sub: 'email customer' },
    { icon: '✅', label: 'Status API', sub: 'GET /ticket/{id}' },
  ];
  return (
    <div className="bg-gray-900 rounded-xl p-4 mb-5">
      <p className="text-xs text-gray-400 mb-3 font-mono uppercase tracking-wider">Web Form Flow — Submit → Kafka → AI → SMTP → Status</p>
      <div className="flex flex-wrap items-center gap-1">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className="bg-gray-800 rounded-lg px-2.5 py-1.5 text-center min-w-[72px]">
              <div className="text-base">{s.icon}</div>
              <div className="text-xs text-white font-medium leading-tight">{s.label}</div>
              <div className="text-xs text-gray-400 leading-tight">{s.sub}</div>
            </div>
            {i < steps.length - 1 && <span className="text-gray-500 font-bold">→</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function Stats({ tickets }) {
  const resolved   = tickets.filter(t => t.status === 'resolved').length;
  const escalated  = tickets.filter(t => t.status === 'escalated').length;
  const avgMs      = tickets.filter(t => t.latency_ms).reduce((a, t) => a + t.latency_ms, 0)
                   / tickets.filter(t => t.latency_ms).length;
  const sent       = tickets.filter(t => t.smtp_status === 'sent').length;
  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {[
        { label: 'Total Tickets',  value: tickets.length,                    color: 'text-gray-900'   },
        { label: 'Resolved',       value: resolved,                          color: 'text-green-600'  },
        { label: 'Escalated',      value: escalated,                         color: 'text-orange-600' },
        { label: 'Emails Sent',    value: sent,                              color: 'text-indigo-600' },
      ].map(s => (
        <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-3 text-center shadow-sm">
          <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Ticket Row ───────────────────────────────────────────────────────────────
function TicketRow({ ticket, selected, onClick }) {
  const st = STATUS_MAP[ticket.status] || STATUS_MAP.queued;
  const pr = SLA_MAP[ticket.priority]  || SLA_MAP.medium;
  return (
    <button onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-indigo-50 transition-colors ${
        selected ? 'bg-indigo-50 border-l-4 border-l-indigo-500' : 'border-l-4 border-l-transparent'
      }`}>
      <div className="flex items-start gap-2">
        <span className="text-lg mt-0.5">{CAT_ICONS[ticket.category] || '📋'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-sm text-gray-900 truncate">{ticket.name}</span>
            <span className="text-xs text-gray-400 shrink-0 ml-2">{fmtTime(ticket.submitted_at)}</span>
          </div>
          <p className="text-xs font-medium text-gray-700 truncate">{ticket.subject}</p>
          <div className="flex items-center gap-1.5 mt-1">
            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${pr.bg} ${pr.text}`}>{pr.label}</span>
            <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full font-medium ${st.bg} ${st.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />{st.label}
            </span>
            <span className="text-xs font-mono text-indigo-500">{ticket.id}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ─── Ticket Detail ────────────────────────────────────────────────────────────
function TicketDetail({ ticket }) {
  const [tab, setTab] = useState('submission');
  const st = STATUS_MAP[ticket.status] || STATUS_MAP.queued;
  const pr = SLA_MAP[ticket.priority]  || SLA_MAP.medium;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h2 className="text-base font-bold text-gray-900">{ticket.subject}</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              <span className="font-medium text-gray-700">{ticket.name}</span>
              {' '}&lt;{ticket.email}&gt;
            </p>
            <p className="text-xs text-gray-400">{fmtDate(ticket.submitted_at)} at {fmtTime(ticket.submitted_at)}</p>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <span className="text-xs font-mono text-indigo-600 bg-indigo-50 px-2 py-1 rounded">{ticket.id}</span>
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${st.bg} ${st.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />{st.label}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${pr.bg} ${pr.text}`}>
              {pr.label} — SLA: {ticket.sla}
            </span>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Category',   value: `${CAT_ICONS[ticket.category]} ${ticket.category}` },
            { label: 'Kafka Topic',value: ticket.kafka_topic },
            { label: 'AI Latency', value: ticket.latency_ms ? `${(ticket.latency_ms/1000).toFixed(1)}s` : '⏳ processing' },
            { label: 'SMTP Status',value: ticket.smtp_status === 'sent' ? '✅ Sent' : ticket.smtp_status === 'pending' ? '⏳ Pending' : ticket.smtp_status },
          ].map(m => (
            <div key={m.label} className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-500">{m.label}</div>
              <div className="text-xs font-semibold text-gray-800 capitalize mt-0.5">{m.value}</div>
            </div>
          ))}
        </div>

        {ticket.escalated_to && (
          <div className="mt-2 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
            <p className="text-xs text-orange-700">
              <span className="font-semibold">Escalated to:</span> {ticket.escalated_to}
            </p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {['submission', 'ai_response', 'journey'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors capitalize ${
              tab === t ? 'border-b-2 border-indigo-500 text-indigo-600' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'submission' ? '📋 Submission' : t === 'ai_response' ? '🤖 AI Response' : '🗺 Journey'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'submission' && (
          <div className="space-y-3">
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Customer Message</p>
              <p className="text-sm text-gray-700 leading-relaxed">{ticket.message}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Pydantic Validation Passed</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { k: 'name',     v: ticket.name     },
                  { k: 'email',    v: ticket.email    },
                  { k: 'category', v: ticket.category },
                  { k: 'priority', v: ticket.priority },
                  { k: 'subject',  v: ticket.subject  },
                ].map(({k, v}) => (
                  <div key={k} className="flex gap-1">
                    <span className="text-gray-400 font-mono">{k}:</span>
                    <span className="text-green-700 font-medium">✓ {v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'ai_response' && (
          ticket.ai_response ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">AI</span>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">TechCorp AI Support</p>
                  <p className="text-xs text-gray-400">support@techcorp.io → {ticket.email}</p>
                </div>
                <span className="ml-auto text-xs text-gray-400">
                  {ticket.latency_ms ? `${(ticket.latency_ms/1000).toFixed(1)}s` : ''}
                </span>
              </div>
              <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {ticket.ai_response}
                </pre>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  ticket.smtp_status === 'sent' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  SMTP: {ticket.smtp_status}
                </span>
                <span className="text-xs text-gray-400">Delivered to {ticket.email}</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-gray-400">
              <div className="w-10 h-10 border-4 border-indigo-300 border-t-indigo-600 rounded-full animate-spin mb-3" />
              <p className="text-sm">Kafka worker processing...</p>
              <p className="text-xs mt-1">webform_inbound → Agent → PostgreSQL → SMTP</p>
            </div>
          )
        )}

        {tab === 'journey' && (
          <div className="space-y-1">
            {[
              { done: true,  time: fmtTime(ticket.submitted_at), icon: '🌐', title: 'Form Submitted',       sub: `POST /web-form/submit` },
              { done: true,  time: fmtTime(ticket.submitted_at), icon: '✅', title: 'Pydantic Validated',   sub: 'name, email, message, priority, category' },
              { done: true,  time: fmtTime(ticket.submitted_at), icon: '📨', title: 'Queued to Kafka',      sub: `topic: ${ticket.kafka_topic}` },
              { done: true,  time: fmtTime(ticket.submitted_at), icon: '🎟', title: 'Ticket ID Generated',  sub: ticket.id },
              { done: !!ticket.ai_response, time: ticket.resolved_at ? fmtTime(ticket.resolved_at) : '⏳', icon: '🤖', title: 'AI Agent Processed', sub: ticket.latency_ms ? `${(ticket.latency_ms/1000).toFixed(1)}s response` : 'in progress...' },
              { done: !!ticket.ai_response, time: ticket.resolved_at ? fmtTime(ticket.resolved_at) : '⏳', icon: '🗄️', title: 'Saved to PostgreSQL', sub: `ticket, conversation, message rows` },
              { done: ticket.smtp_status === 'sent', time: ticket.resolved_at ? fmtTime(ticket.resolved_at) : '⏳', icon: '📧', title: 'Email Sent via SMTP', sub: `→ ${ticket.email}` },
              { done: ticket.status === 'resolved' || ticket.status === 'escalated', time: '—', icon: '🏁', title: 'Ticket Closed', sub: ticket.status },
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 ${
                  step.done ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  {step.done ? step.icon : '⏳'}
                </div>
                <div className="flex-1 pb-3 border-b border-gray-100 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium ${step.done ? 'text-gray-800' : 'text-gray-400'}`}>{step.title}</span>
                    <span className="text-xs text-gray-400">{step.time}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{step.sub}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function WebFormDashboard() {
  const [selected, setSelected] = useState(MOCK_TICKETS[0]);
  const [filter, setFilter]     = useState('all');

  const filtered = filter === 'all' ? MOCK_TICKETS : MOCK_TICKETS.filter(t => t.status === filter);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-gray-900">Web Form Channel</span>
              <span className="ml-2 text-xs text-gray-400">AI Customer Success FTE</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-indigo-600 font-medium">
            <span className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse" />
            FastAPI Active
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-5">
        <FlowDiagram />
        <Stats tickets={MOCK_TICKETS} />

        <div className="flex gap-2 mb-3">
          {['all', 'resolved', 'escalated', 'processing'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                filter === f ? 'bg-indigo-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-indigo-300'
              }`}>
              {f === 'all' ? `All (${MOCK_TICKETS.length})` : f}
            </button>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
             style={{ height: '620px', display: 'grid', gridTemplateColumns: '340px 1fr' }}>
          <div className="border-r border-gray-200 overflow-y-auto">
            <div className="px-4 py-2 bg-indigo-600">
              <p className="text-xs font-semibold text-indigo-200 uppercase tracking-wider">Tickets — {filtered.length}</p>
            </div>
            {filtered.map(t => (
              <TicketRow key={t.id} ticket={t} selected={selected?.id === t.id} onClick={() => setSelected(t)} />
            ))}
          </div>
          <div className="overflow-hidden">
            {selected
              ? <TicketDetail ticket={selected} />
              : <div className="flex items-center justify-center h-full text-gray-400">Select a ticket</div>
            }
          </div>
        </div>

        <div className="mt-5 bg-gray-900 rounded-xl p-4 text-sm font-mono">
          <p className="text-green-400 mb-2"># web_form_handler.py — key functions</p>
          <p className="text-gray-400"><span className="text-blue-400">SupportFormSubmission</span><span className="text-gray-500">     # Pydantic — validates name, email, message, priority, category</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">submit_support_form</span><span className="text-gray-500">       # POST /web-form/submit → Kafka → returns ticket_id + SLA</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">get_ticket_status</span><span className="text-gray-500">         # GET /web-form/ticket/{"{id}"} → PostgreSQL lookup</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">send_web_form_reply</span><span className="text-gray-500">       # SMTP (smtplib) → email reply to customer</span></p>
          <p className="text-yellow-400 mt-2"># SLA by priority</p>
          <p className="text-gray-400"><span className="text-white">urgent</span><span className="text-gray-500">→2h  </span><span className="text-white">high</span><span className="text-gray-500">→4h  </span><span className="text-white">medium</span><span className="text-gray-500">→8h  </span><span className="text-white">low</span><span className="text-gray-500">→24h</span></p>
        </div>
      </div>
    </div>
  );
}
