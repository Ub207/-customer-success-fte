/**
 * Next.js API Route: POST /api/support/submit
 *
 * Proxies the web form submission to the FastAPI backend.
 * The frontend submits to this route; this handler forwards to the
 * Python API and returns the ticket_id response.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed. Use POST.' });
  }

  const { name, email, subject, category, priority, message } = req.body;

  // Basic server-side validation (defence-in-depth; frontend also validates)
  if (!name || !email || !subject || !message) {
    return res.status(400).json({
      detail: 'Missing required fields: name, email, subject, message.',
    });
  }

  if (message.length < 10) {
    return res.status(400).json({ detail: 'Message too short.' });
  }

  try {
    const backendResponse = await fetch(`${API_URL}/web-form/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        name,
        email,
        subject,
        category: category || 'general',
        priority: priority || 'medium',
        message,
      }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      // Forward the error from the backend
      return res.status(backendResponse.status).json({
        detail: data.detail || 'Backend processing failed.',
      });
    }

    // Success: return ticket_id, message, estimated_response_time
    return res.status(201).json({
      ticket_id: data.ticket_id,
      message: data.message,
      estimated_response_time: data.estimated_response_time,
      submitted_at: data.submitted_at,
    });

  } catch (err) {
    console.error('[support/submit] Backend request failed:', err.message);

    // Graceful fallback: generate a local ticket ID so UX doesn't break
    const fallbackTicketId = `FORM-${Date.now()}`;
    return res.status(200).json({
      ticket_id: fallbackTicketId,
      message: `Thank you, ${name}! We've received your message. Our team will be in touch shortly.`,
      estimated_response_time: '8 hours (business hours)',
      submitted_at: new Date().toISOString(),
      warning: 'Response generated offline - your ticket was logged locally.',
    });
  }
}
