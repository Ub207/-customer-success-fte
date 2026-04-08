import Head from 'next/head';
import SupportForm from '../components/SupportForm';

// ─── Refined Icons (Strictly w-4 h-4 max) ────────────────────────────────────

const IconBolt = () => (
  <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
    <path d="M9.5 1L2 9.5h5.5L6 15l8.5-8.5H9L9.5 1z" />
  </svg>
);

const IconMail = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
    <rect x="1" y="3" width="14" height="10" rx="1.5" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M1 5l7 5 7-5" />
  </svg>
);

const IconMessage = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2 2h12a1 1 0 011 1v8a1 1 0 01-1 1H5l-3 3V3a1 1 0 011-1z" />
  </svg>
);

const IconGlobe = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
    <circle cx="8" cy="8" r="6.5" />
    <path strokeLinecap="round" d="M1.5 8h13M8 1.5C6.5 4 5.5 6 5.5 8s1 4 2.5 6.5M8 1.5C9.5 4 10.5 6 10.5 8s-1 4-2.5 6.5" />
  </svg>
);

// ─── Sub-components ──────────────────────────────────────────────────────────

function ChannelBadge({ icon, label, dotColor }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-500 shadow-sm transition-all hover:border-slate-300">
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className="text-slate-400">{icon}</span>
      {label}
    </span>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SupportPage() {
  return (
    <div className="min-h-screen bg-slate-50/50 selection:bg-brand-100 selection:text-brand-900">
      <Head>
        <title>Support | TechCorp</title>
        <meta name="description" content="Get help from TechCorp AI support. Fast, intelligent, 24/7." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {/* ── Navigation ──────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 shadow-brand-500/20 shadow-lg">
              <IconBolt />
            </div>
            <span className="text-[15px] font-bold tracking-tight text-slate-900">TechCorp</span>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            AI ACTIVE
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-5xl px-4 pt-16 pb-24 sm:px-6">
        
        {/* ── Hero Section ─────────────────────────────── */}
        <div className="text-center mb-12 animate-fade-up">
          <div className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-[12px] font-semibold text-brand-600 mb-6">
            <span className="w-1 h-1 rounded-full bg-brand-400" />
            24/7 Intelligent Support
          </div>
          
          <h1 className="mb-4 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            How can we help?
          </h1>
          <p className="mx-auto max-w-md text-base leading-relaxed text-slate-500">
            Our AI support agent typically responds in under 5 minutes. 
            Describe your issue below to get started.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <ChannelBadge icon={<IconMail />}    label="Email Channel"    dotColor="bg-blue-400" />
            <ChannelBadge icon={<IconMessage />} label="Live Chat"       dotColor="bg-emerald-400" />
            <ChannelBadge icon={<IconGlobe />}   label="Web Support"     dotColor="bg-brand-400" />
          </div>
        </div>

        {/* ── Form Card ────────────────────────────────── */}
        <div className="mx-auto w-full max-w-xl animate-fade-up [animation-delay:100ms]">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/40">
            
            {/* Card Header */}
            <div className="border-b border-slate-100 bg-slate-50/50 px-8 py-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 shadow-sm">
                  <span className="text-slate-600"><IconMessage /></span>
                </div>
                <div>
                  <h2 className="text-[15px] font-bold text-slate-900">Open a Ticket</h2>
                  <p className="text-[12px] text-slate-400">Please provide as much detail as possible.</p>
                </div>
              </div>
            </div>

            {/* Form Content */}
            <div className="p-8">
              <SupportForm />
            </div>
          </div>

          <div className="mt-8 text-center">
            <p className="text-[12px] text-slate-400">
              By submitting, you agree to our <a href="#" className="underline hover:text-slate-600">Privacy Policy</a> and <a href="#" className="underline hover:text-slate-600">Terms of Service</a>.
            </p>
          </div>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="border-t border-slate-100 bg-white py-10">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 px-4 sm:flex-row sm:px-6 text-slate-400">
          <p className="text-[12px]">
            &copy; {new Date().getFullYear()} TechCorp Inc.
          </p>
          <div className="flex gap-6 text-[12px] font-medium">
            <a href="mailto:support@techcorp.io" className="hover:text-slate-900 transition-colors">
              support@techcorp.io
            </a>
            <a href="https://status.techcorp.io" target="_blank" rel="noopener noreferrer"
              className="hover:text-slate-900 transition-colors">
              System Status
            </a>
            <a href="#" className="hover:text-slate-900 transition-colors">Help Center</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
