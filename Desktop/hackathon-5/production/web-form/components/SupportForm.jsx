/**
 * SupportForm — Redesigned SaaS-style UI
 * Style: Clean, modern, Stripe/Linear inspired.
 * Fields: Name, Email, Subject, Category, Message
 */
import { useState } from 'react';

// ─── Constants ───────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: '',          label: 'Select a category' },
  { value: 'general',   label: 'General Question' },
  { value: 'technical', label: 'Technical Issue' },
  { value: 'billing',   label: 'Billing & Payments' },
  { value: 'account',   label: 'Account & Login' },
  { value: 'bug',       label: 'Bug Report' },
  { value: 'feedback',  label: 'Feedback' },
  { value: 'other',     label: 'Other' },
];

const INITIAL_STATE = {
  name: '',
  email: '',
  subject: '',
  category: '',
  message: '',
};

const MAX_MESSAGE_LENGTH = 2000;

// ─── UI Components ───────────────────────────────────────────────────────────

/**
 * Label component with optional hint
 */
function Label({ htmlFor, children, hint }) {
  return (
    <div className="flex items-center justify-between mb-1.5">
      <label htmlFor={htmlFor} className="text-[13px] font-medium text-slate-700">
        {children}
      </label>
      {hint && <span className="text-[11px] text-slate-400 font-normal">{hint}</span>}
    </div>
  );
}

/**
 * Shared input styling
 */
const inputClasses = (error) => `
  block w-full rounded-lg border px-3.5 py-2.5 text-sm transition-all duration-200
  placeholder:text-slate-400 focus:outline-none focus:ring-2
  ${error 
    ? 'border-red-300 bg-red-50/30 text-red-900 focus:ring-red-500/10 focus:border-red-500' 
    : 'border-slate-200 bg-white text-slate-900 focus:ring-brand-500/10 focus:border-brand-500 hover:border-slate-300 shadow-sm'}
`;

/**
 * Field Error Message with small icon
 */
function FieldError({ msg }) {
  if (!msg) return null;
  return (
    <p role="alert" className="mt-1.5 flex items-center gap-1.5 text-[12px] text-red-500 animate-fade-up">
      <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm-.75 3.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zm.75 7a.875.875 0 110-1.75.875.875 0 010 1.75z" />
      </svg>
      {msg}
    </p>
  );
}

/**
 * Success Screen — Compact and clean
 */
function SuccessScreen({ ticketId, eta, onReset }) {
  return (
    <div className="animate-fade-up flex flex-col items-center text-center py-6">
      <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-4 shadow-sm">
        <svg className="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h3 className="text-lg font-bold text-slate-900 mb-2">Request received</h3>
      <p className="text-sm text-slate-500 mb-8 max-w-[280px] leading-relaxed">
        Our support team has been notified. We usually reply in {eta}.
      </p>

      <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 mb-8 text-left">
        <div className="flex items-center justify-between mb-1">
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Ticket Reference</p>
          <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <p className="font-mono text-[13px] font-semibold text-brand-600 break-all">{ticketId}</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 w-full">
        <button
          onClick={() => window.location.href = `/ticket/${ticketId}`}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold shadow-sm transition-all"
        >
          Track Status
          <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 8h10M9 4l4 4-4 4" />
          </svg>
        </button>
        <button
          onClick={onReset}
          className="flex-1 inline-flex items-center justify-center px-4 py-2.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-semibold transition-all"
        >
          New Ticket
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function SupportForm({ apiUrl = '/api/support/submit' }) {
  const [form, setForm] = useState(INITIAL_STATE);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState('');

  // Validation logic
  const validate = () => {
    const e = {};
    if (form.name.trim().length < 2) 
      e.name = 'Please enter your full name.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) 
      e.email = 'Enter a valid email address.';
    if (form.subject.trim().length < 5) 
      e.subject = 'Subject is too short (min 5 chars).';
    if (!form.category) 
      e.category = 'Please select a category.';
    if (form.message.trim().length < 10) 
      e.message = 'Please provide more details (min 10 chars).';
    if (form.message.length > MAX_MESSAGE_LENGTH)
      e.message = `Max ${MAX_MESSAGE_LENGTH} characters allowed.`;
    return e;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    if (apiError) setApiError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setSubmitting(true);
    setApiError('');

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, priority: 'medium' }), // Defaulting priority
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Something went wrong. Please try again.');
      }
      setResult(data);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setForm(INITIAL_STATE);
    setErrors({});
    setApiError('');
  };

  if (result) {
    return (
      <SuccessScreen
        ticketId={result.ticket_id}
        eta={result.estimated_response_time || '5-10 minutes'}
        onReset={handleReset}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6 animate-fade-up">
      
      {/* Global API Error */}
      {apiError && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/50 p-4 animate-fade-up">
          <svg className="mt-0.5 w-4 h-4 shrink-0 text-red-500" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm-.75 3.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zm.75 7a.875.875 0 110-1.75.875.875 0 010 1.75z" />
          </svg>
          <p className="text-[13px] font-medium text-red-800 leading-tight">{apiError}</p>
        </div>
      )}

      {/* Row: Name + Email */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="name">Full Name</Label>
          <input
            id="name" name="name" type="text"
            value={form.name} onChange={handleChange}
            placeholder="Jane Smith" autoComplete="name"
            className={inputClasses(errors.name)}
          />
          <FieldError msg={errors.name} />
        </div>
        <div>
          <Label htmlFor="email">Email Address</Label>
          <input
            id="email" name="email" type="email"
            value={form.email} onChange={handleChange}
            placeholder="jane@example.com" autoComplete="email"
            className={inputClasses(errors.email)}
          />
          <FieldError msg={errors.email} />
        </div>
      </div>

      {/* Subject */}
      <div>
        <Label htmlFor="subject">Subject</Label>
        <input
          id="subject" name="subject" type="text"
          value={form.subject} onChange={handleChange}
          placeholder="What's your request about?"
          className={inputClasses(errors.subject)}
        />
        <FieldError msg={errors.subject} />
      </div>

      {/* Category */}
      <div>
        <Label htmlFor="category">Category</Label>
        <div className="relative">
          <select
            id="category" name="category"
            value={form.category} onChange={handleChange}
            className={`${inputClasses(errors.category)} appearance-none pr-10`}
          >
            {CATEGORIES.map(cat => (
              <option key={cat.value} value={cat.value} disabled={cat.value === ''}>
                {cat.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3.5">
            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        <FieldError msg={errors.category} />
      </div>

      {/* Message */}
      <div>
        <Label htmlFor="message" hint={`${form.message.length}/${MAX_MESSAGE_LENGTH}`}>
          Message
        </Label>
        <textarea
          id="message" name="message" rows={5}
          value={form.message} onChange={handleChange}
          placeholder="Tell us more about your issue..."
          className={`${inputClasses(errors.message)} resize-none leading-relaxed`}
        />
        <FieldError msg={errors.message} />
      </div>

      {/* Submit Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-3.5 text-sm font-bold text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {submitting ? (
            <>
              <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Processing...</span>
            </>
          ) : (
            <>
              <span>Send Request</span>
              <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2 8h12M9 3l5 5-5 5" />
              </svg>
            </>
          )}
        </button>
      </div>

    </form>
  );
}
