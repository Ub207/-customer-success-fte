import { useState } from 'react';

// ─── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_CHATS = [
  {
    id: 'chat_001',
    ticket_id: 'TKT-3101',
    phone: '+92 300 1234567',
    profile_name: 'Bilal Raza',
    last_message: 'JazakAllah! Issue resolved.',
    last_time: '2026-03-31T10:45:00Z',
    status: 'resolved',
    is_human_request: false,
    messages: [
      { from: 'customer', text: 'Assalam o alaikum! My dashboard is not loading since morning.', time: '2026-03-31T10:30:00Z', delivery: 'read' },
      { from: 'ai',       text: 'Walaikum Assalam Bilal! I can see the issue — our CDN had a brief outage this morning between 9:00–10:15 AM PKT.\n\nThe service is fully restored now. Please try:\n1. Clear your browser cache (Ctrl+Shift+R)\n2. Reload the dashboard\n\nLet me know if it still doesn\'t work!', time: '2026-03-31T10:30:02Z', delivery: 'read' },
      { from: 'customer', text: 'It worked! JazakAllah! Issue resolved.', time: '2026-03-31T10:45:00Z', delivery: 'read' },
    ],
  },
  {
    id: 'chat_002',
    ticket_id: 'TKT-3102',
    phone: '+92 321 9876543',
    profile_name: 'Hina Shah',
    last_message: 'I want to talk to a human agent please',
    last_time: '2026-03-31T11:15:00Z',
    status: 'escalated',
    is_human_request: true,
    escalated_to: 'senior-support@techcorp.io',
    messages: [
      { from: 'customer', text: 'My account was hacked and someone changed my email!', time: '2026-03-31T11:10:00Z', delivery: 'read' },
      { from: 'ai',       text: 'Hi Hina! This is serious and I\'m treating it as urgent.\n\nImmediate actions I\'ve taken:\n• Flagged your account for security review\n• Locked suspicious login sessions\n\nTicket: TKT-3102 (Priority: URGENT)\n\nOur security team has been notified.', time: '2026-03-31T11:10:03Z', delivery: 'read' },
      { from: 'customer', text: 'I want to talk to a human agent please', time: '2026-03-31T11:15:00Z', delivery: 'read' },
      { from: 'ai',       text: 'Absolutely understood. I\'ve escalated to our Senior Support team right now.\n\n📞 A human agent will contact you within 2 hours.\n📧 security@techcorp.io has been notified.\n\nStay safe — don\'t click any suspicious links.', time: '2026-03-31T11:15:02Z', delivery: 'delivered' },
    ],
  },
  {
    id: 'chat_003',
    ticket_id: 'TKT-3103',
    phone: '+1 555 4445566',
    profile_name: 'John Miller',
    last_message: 'How many users can I add on Pro plan?',
    last_time: '2026-03-31T12:00:00Z',
    status: 'replied',
    is_human_request: false,
    messages: [
      { from: 'customer', text: 'How many users can I add on Pro plan?', time: '2026-03-31T12:00:00Z', delivery: 'read' },
      { from: 'ai',       text: 'Hi John! On the Pro plan you can add up to *25 team members*.\n\nHere\'s a quick comparison:\n• Starter: 3 users\n• Pro: 25 users\n• Business: Unlimited\n\nNeed to upgrade? Reply "upgrade" or visit your billing settings. 🚀', time: '2026-03-31T12:00:02Z', delivery: 'read' },
    ],
  },
  {
    id: 'chat_004',
    ticket_id: 'TKT-3104',
    phone: '+92 333 7778899',
    profile_name: 'Ayesha Noor',
    last_message: 'API key not working after reset',
    last_time: '2026-03-31T12:30:00Z',
    status: 'processing',
    is_human_request: false,
    messages: [
      { from: 'customer', text: 'I reset my API key but the old one still seems to work and new one gives 401', time: '2026-03-31T12:30:00Z', delivery: 'read' },
    ],
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString('en-PK', { hour: '2-digit', minute: '2-digit' });
}

const STATUS_CFG = {
  resolved:   { label: 'Resolved',   bg: 'bg-green-100',  text: 'text-green-700'  },
  replied:    { label: 'Replied',    bg: 'bg-blue-100',   text: 'text-blue-700'   },
  escalated:  { label: 'Escalated', bg: 'bg-orange-100', text: 'text-orange-700' },
  processing: { label: 'Processing',bg: 'bg-gray-100',   text: 'text-gray-500'   },
};

function DeliveryTick({ status }) {
  if (status === 'read')      return <span className="text-blue-400 text-xs">✓✓</span>;
  if (status === 'delivered') return <span className="text-gray-400 text-xs">✓✓</span>;
  return <span className="text-gray-300 text-xs">✓</span>;
}

// ─── Flow Diagram ─────────────────────────────────────────────────────────────
function FlowDiagram() {
  const steps = [
    { icon: '💬', label: 'Customer WA', sub: 'sends message' },
    { icon: '📡', label: 'Twilio', sub: 'receives it' },
    { icon: '📥', label: 'Webhook', sub: 'POST /webhooks/whatsapp' },
    { icon: '🔍', label: 'Normalize', sub: 'parse form-data' },
    { icon: '🚨', label: 'Human Check', sub: 'detect_human_request()' },
    { icon: '📨', label: 'Kafka', sub: 'whatsapp_inbound' },
    { icon: '🤖', label: 'AI Agent', sub: 'process + reply' },
    { icon: '📤', label: 'Twilio Send', sub: 'send_whatsapp_reply()' },
  ];
  return (
    <div className="bg-gray-900 rounded-xl p-4 mb-5">
      <p className="text-xs text-gray-400 mb-3 font-mono uppercase tracking-wider">WhatsApp Flow — Twilio → Kafka → AI → Twilio</p>
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

// ─── Chat Bubble ──────────────────────────────────────────────────────────────
function Bubble({ msg }) {
  const isAI = msg.from === 'ai';
  return (
    <div className={`flex ${isAI ? 'justify-start' : 'justify-end'} mb-2`}>
      {isAI && (
        <div className="w-7 h-7 rounded-full bg-green-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0">
          AI
        </div>
      )}
      <div className={`max-w-[75%] rounded-2xl px-3 py-2 shadow-sm ${
        isAI ? 'bg-white text-gray-800 rounded-tl-sm' : 'bg-green-500 text-white rounded-tr-sm'
      }`}>
        <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">{msg.text}</pre>
        <div className={`flex items-center justify-end gap-1 mt-1 ${isAI ? 'text-gray-400' : 'text-green-100'}`}>
          <span className="text-xs">{fmtTime(msg.time)}</span>
          {!isAI && <DeliveryTick status={msg.delivery} />}
        </div>
      </div>
    </div>
  );
}

// ─── Chat List Item ───────────────────────────────────────────────────────────
function ChatItem({ chat, selected, onClick }) {
  const cfg = STATUS_CFG[chat.status] || STATUS_CFG.processing;
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-green-50 transition-colors ${
        selected ? 'bg-green-50 border-l-4 border-l-green-500' : 'border-l-4 border-l-transparent'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-green-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
          {chat.profile_name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-sm text-gray-900">{chat.profile_name}</span>
            <span className="text-xs text-gray-400">{fmtTime(chat.last_time)}</span>
          </div>
          <div className="flex items-center justify-between mt-0.5">
            <p className="text-xs text-gray-500 truncate flex-1 mr-2">{chat.last_message}</p>
            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium shrink-0 ${cfg.bg} ${cfg.text}`}>
              {cfg.label}
            </span>
          </div>
          {chat.is_human_request && (
            <span className="text-xs text-orange-600 font-medium">⚠ Human requested</span>
          )}
        </div>
      </div>
    </button>
  );
}

// ─── Chat Window ──────────────────────────────────────────────────────────────
function ChatWindow({ chat }) {
  const cfg = STATUS_CFG[chat.status] || STATUS_CFG.processing;
  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div className="bg-green-700 text-white px-4 py-3 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-green-500 flex items-center justify-center font-bold">
          {chat.profile_name.charAt(0)}
        </div>
        <div className="flex-1">
          <p className="font-semibold text-sm">{chat.profile_name}</p>
          <p className="text-xs text-green-200">{chat.phone}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs font-mono bg-green-800 px-2 py-0.5 rounded">{chat.ticket_id}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.bg} ${cfg.text}`}>
            {cfg.label}
          </span>
        </div>
      </div>

      {/* Special badges */}
      {(chat.is_human_request || chat.escalated_to) && (
        <div className="bg-orange-50 border-b border-orange-200 px-4 py-2 flex items-center gap-2">
          <span className="text-orange-600 text-sm">⚠</span>
          <span className="text-xs text-orange-700 font-medium">
            {chat.is_human_request ? 'Customer requested human agent' : ''}
            {chat.escalated_to ? ` — Escalated to: ${chat.escalated_to}` : ''}
          </span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-[#e5ddd5] p-4"
           style={{ backgroundImage: 'url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAB3RJTUUH2AsLDisBFPalagAAAABJRU5ErkJggg==")' }}>
        {chat.messages.map((m, i) => <Bubble key={i} msg={m} />)}
        {chat.status === 'processing' && (
          <div className="flex justify-start mb-2">
            <div className="w-7 h-7 rounded-full bg-green-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1">AI</div>
            <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex items-center gap-1.5">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>

      {/* Info footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-2 grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-xs text-gray-500">Channel</div>
          <div className="text-xs font-semibold text-green-700">WhatsApp</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Messages</div>
          <div className="text-xs font-semibold text-gray-800">{chat.messages.length}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Max Length</div>
          <div className="text-xs font-semibold text-gray-800">1600 chars</div>
        </div>
      </div>
    </div>
  );
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function Stats({ chats }) {
  const resolved   = chats.filter(c => c.status === 'resolved').length;
  const escalated  = chats.filter(c => c.status === 'escalated').length;
  const humanReqs  = chats.filter(c => c.is_human_request).length;
  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {[
        { label: 'Total Chats',       value: chats.length, color: 'text-gray-900'   },
        { label: 'Resolved by AI',    value: resolved,     color: 'text-green-600'  },
        { label: 'Escalated',         value: escalated,    color: 'text-orange-600' },
        { label: 'Human Requested',   value: humanReqs,    color: 'text-red-600'    },
      ].map(s => (
        <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-3 text-center shadow-sm">
          <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function WhatsAppDashboard() {
  const [selected, setSelected] = useState(MOCK_CHATS[0]);
  const [filter, setFilter]     = useState('all');

  const filtered = filter === 'all' ? MOCK_CHATS : MOCK_CHATS.filter(c => c.status === filter);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <header className="bg-green-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-green-700" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-white">WhatsApp Channel</span>
              <span className="ml-2 text-xs text-green-300">AI Customer Success FTE</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-green-200 font-medium">
            <span className="w-2 h-2 bg-green-300 rounded-full animate-pulse" />
            Twilio Active
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-5">
        <FlowDiagram />
        <Stats chats={MOCK_CHATS} />

        {/* Filters */}
        <div className="flex gap-2 mb-3">
          {['all', 'resolved', 'replied', 'escalated', 'processing'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                filter === f ? 'bg-green-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-green-400'
              }`}>
              {f === 'all' ? `All (${MOCK_CHATS.length})` : f}
            </button>
          ))}
        </div>

        {/* Split view */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
             style={{ height: '600px', display: 'grid', gridTemplateColumns: '300px 1fr' }}>
          {/* Left: chat list */}
          <div className="border-r border-gray-200 overflow-y-auto">
            <div className="px-4 py-2 bg-green-700">
              <p className="text-xs font-semibold text-green-200 uppercase tracking-wider">
                Conversations — {filtered.length}
              </p>
            </div>
            {filtered.map(chat => (
              <ChatItem key={chat.id} chat={chat} selected={selected?.id === chat.id} onClick={() => setSelected(chat)} />
            ))}
          </div>

          {/* Right: chat window */}
          <div className="overflow-hidden">
            {selected
              ? <ChatWindow chat={selected} />
              : <div className="flex items-center justify-center h-full text-gray-400">Select a chat</div>
            }
          </div>
        </div>

        {/* Code note */}
        <div className="mt-5 bg-gray-900 rounded-xl p-4 text-sm font-mono">
          <p className="text-green-400 mb-2"># whatsapp_handler.py — key functions</p>
          <p className="text-gray-400"><span className="text-blue-400">detect_human_request</span><span className="text-white">(message)</span><span className="text-gray-500">   # "human", "agent", "person" → escalate</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">normalize</span><span className="text-white">(form_data)</span><span className="text-gray-500">          # Twilio payload → canonical format</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">split_message</span><span className="text-white">(msg, max=1600)</span><span className="text-gray-500">    # Twilio limit — split at sentence boundary</span></p>
          <p className="text-gray-400 mt-1"><span className="text-blue-400">send_whatsapp_reply</span><span className="text-white">(to_phone, body)</span><span className="text-gray-500">  # Twilio REST API → whatsapp:+phone</span></p>
        </div>
      </div>
    </div>
  );
}
