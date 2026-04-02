# TechCorp Customer Success - Escalation Rules

## Immediate Escalation Triggers (Escalate Without Attempting to Resolve)

### Legal/Compliance
- Customer mentions "lawyer", "attorney", "sue", "legal action", "court"
- GDPR/privacy data deletion requests
- Data breach reports
- Regulatory compliance questions (SOC2, HIPAA, FedRAMP)
- **Escalate to:** legal-support@techcorp.io

### Billing & Financial
- Any pricing inquiry or quote request
- Refund requests of any amount
- Billing disputes
- Contract negotiation
- **Escalate to:** billing@techcorp.io

### Negative Sentiment / Angry Customers
- Sentiment score < 0.3 (very negative)
- Profanity or aggressive language
- Threats to cancel or switch to competitor
- Executive-level frustration ("I'm the CTO and this is unacceptable")
- **Escalate to:** senior-support@techcorp.io

### Account Security
- Suspected account compromise
- Requests to change account ownership
- Unauthorized access reports
- **Escalate to:** security@techcorp.io

## Conditional Escalation (Attempt Resolution First)

### Knowledge Gaps
- If after 2 searches in knowledge base, no relevant information found
- Questions about unreleased features or roadmap
- **First:** Acknowledge the gap, **Then:** Escalate with full context

### Complex Technical Issues
- API issues affecting multiple customers (check Slack #incidents first)
- Data loss or corruption reports
- Sync failures persisting > 24 hours
- **First:** Try standard troubleshooting, **Then:** Escalate if unresolved

### Explicit Human Request
- Customer says "I want to speak to a human"
- Customer says "Can I talk to someone?"
- WhatsApp: Customer sends "human", "agent", "representative", "person"
- **Escalate immediately with full conversation context**

## Escalation Process

1. Acknowledge the customer: "I'm connecting you with our specialized team..."
2. Create escalation record with:
   - Full conversation history
   - Customer identifier (email/phone)
   - Source channel
   - Reason for escalation
   - Urgency level (low/normal/high/critical)
3. Notify appropriate team via Kafka escalation topic
4. Confirm escalation to customer with expected response time

## SLA After Escalation
- **Critical (legal, security):** 1 hour
- **High (angry customer, refund):** 2 hours
- **Normal:** 4 hours (business hours)
- **Low:** Next business day
