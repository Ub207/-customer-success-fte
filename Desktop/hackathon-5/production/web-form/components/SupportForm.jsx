import { useState } from 'react';

const CATEGORIES = [
  { value: 'general', label: 'General Question' },
  { value: 'technical', label: 'Technical Issue' },
  { value: 'billing', label: 'Billing & Payments' },
  { value: 'account', label: 'Account & Login' },
  { value: 'bug', label: 'Bug Report' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'other', label: 'Other' },
];

const PRIORITIES = [
  { value: 'low', label: 'Low - General inquiry' },
  { value: 'medium', label: 'Medium - Affecting my work' },
  { value: 'high', label: 'High - Blocking me right now' },
  { value: 'urgent', label: 'Urgent - Critical business impact' },
];

const MESSAGE_MAX = 2000;

function SuccessCard({ ticketId, estimatedTime, onReset }) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 text-center max-w-md mx-auto">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Request Received!</h2>
      <p className="text-gray-600 mb-4">
        Our AI support agent has received your message and will respond shortly.
      </p>
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-500 mb-1">Your Ticket ID</p>
        <p className="text-lg font-mono font-semibold text-indigo-600 break-all">{ticketId}</p>
      </div>
      <div className="bg-blue-50 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-700">
          <span className="font-semibold">Estimated response:</span> {estimatedTime}
        </p>
      </div>
      <button
        onClick={onReset}
        className="text-indigo-600 hover:text-indigo-700 text-sm font-medium underline"
      >
        Submit another request
      </button>
    </div>
  );
}

function SupportForm({ apiUrl = '/api/support/submit' }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    category: 'general',
    priority: 'medium',
    message: '',
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [serverError, setServerError] = useState('');

  const validate = () => {
    const newErrors = {};

    if (!formData.name.trim() || formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters.';
    }

    if (!formData.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address.';
    }

    if (!formData.subject.trim() || formData.subject.trim().length < 5) {
      newErrors.subject = 'Subject must be at least 5 characters.';
    }

    if (!formData.message.trim() || formData.message.trim().length < 10) {
      newErrors.message = 'Message must be at least 10 characters.';
    }

    if (formData.message.length > MESSAGE_MAX) {
      newErrors.message = `Message must be under ${MESSAGE_MAX} characters.`;
    }

    return newErrors;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error on change
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
    setServerError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setServerError('');

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Submission failed. Please try again.');
      }

      setSubmitResult(data);
    } catch (err) {
      setServerError(
        err.message || 'Something went wrong. Please try again or email us at support@techcorp.io.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setSubmitResult(null);
    setFormData({
      name: '',
      email: '',
      subject: '',
      category: 'general',
      priority: 'medium',
      message: '',
    });
    setErrors({});
    setServerError('');
  };

  if (submitResult) {
    return (
      <SuccessCard
        ticketId={submitResult.ticket_id}
        estimatedTime={submitResult.estimated_response_time}
        onReset={handleReset}
      />
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Contact Support</h2>
        <p className="text-gray-500 mt-1 text-sm">
          Our AI assistant responds 24/7. Typically within minutes.
        </p>
      </div>

      {serverError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-700 text-sm">{serverError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* Name + Email row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="John Smith"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                errors.name ? 'border-red-400 bg-red-50' : 'border-gray-300'
              }`}
            />
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email Address <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@company.com"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                errors.email ? 'border-red-400 bg-red-50' : 'border-gray-300'
              }`}
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
          </div>
        </div>

        {/* Subject */}
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
            Subject <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleChange}
            placeholder="Brief description of your issue"
            className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
              errors.subject ? 'border-red-400 bg-red-50' : 'border-gray-300'
            }`}
          />
          {errors.subject && <p className="text-red-500 text-xs mt-1">{errors.subject}</p>}
        </div>

        {/* Category + Priority row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white transition"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white transition"
            >
              {PRIORITIES.map((pri) => (
                <option key={pri.value} value={pri.value}>
                  {pri.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Message */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label htmlFor="message" className="block text-sm font-medium text-gray-700">
              Message <span className="text-red-500">*</span>
            </label>
            <span
              className={`text-xs ${
                formData.message.length > MESSAGE_MAX * 0.9 ? 'text-red-500' : 'text-gray-400'
              }`}
            >
              {formData.message.length} / {MESSAGE_MAX}
            </span>
          </div>
          <textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleChange}
            rows={6}
            placeholder="Describe your issue in detail. Include any error messages, steps to reproduce, and what you've already tried."
            className={`w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none transition ${
              errors.message ? 'border-red-400 bg-red-50' : 'border-gray-300'
            }`}
          />
          {errors.message && <p className="text-red-500 text-xs mt-1">{errors.message}</p>}
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 text-sm"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Sending...
            </span>
          ) : (
            'Send Message'
          )}
        </button>

        <p className="text-xs text-gray-400 text-center">
          Powered by TechCorp AI Support — available 24/7
        </p>
      </form>
    </div>
  );
}

export default SupportForm;
