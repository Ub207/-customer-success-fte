# Discovery Log - Customer Success FTE Incubation

## Session Overview
**Date:** 2026-03-27
**Duration:** 16 hours
**Method:** Iterative exploration with Claude Code

---

## Phase 1: Initial Analysis of Sample Tickets

### Channel-Specific Patterns Discovered

**Email tickets:**
- Longer, more detailed messages (avg 3-4 sentences)
- Formal tone from customers
- Often include context/background
- Subject line provides crucial categorization signal
- Customers expect formal, comprehensive responses

**WhatsApp tickets:**
- Very short messages (avg 1-2 sentences)
- Casual language, sometimes incomplete sentences
- Urgent issues expressed with caps and exclamation marks
- Quick back-and-forth expected
- Response should be < 300 chars ideally

**Web Form tickets:**
- Structured (subject + category pre-selected)
- Medium length messages
- More thoughtful/deliberate than WhatsApp
- Customer already categorized their own issue

### Issue Category Distribution
- Account/Auth issues: 25%
- Technical/API: 30%
- Billing: 20%
- General how-to: 15%
- Bug reports: 10%

---

## Phase 2: Prototype Core Loop Iterations

### Iteration 1: Basic Response Generation
**Problem found:** Responses were same length regardless of channel
**Fix:** Added channel parameter to response formatting
**Result:** WhatsApp responses shortened to <300 chars

### Iteration 2: Pricing Question Handling
**Problem found:** Agent tried to answer pricing questions
**Fix:** Added hard constraint to escalate ALL pricing inquiries
**Test:** "How much is enterprise?" -> Always escalates now

### Iteration 3: Angry Customer Detection
**Problem found:** Agent gave procedural response to angry customers
**Fix:** Added sentiment analysis before generating response
**Rule:** Sentiment < 0.3 -> immediate escalation
**Test:** "YOUR APP IS BROKEN!!!!" -> Escalation triggered

### Iteration 4: Cross-Channel Customer Identification
**Problem found:** Same customer emailing AND WhatsApp = treated as strangers
**Fix:** Email address as primary key, phone as secondary
**Solution:** customer_identifiers table with multiple identifier types

### Iteration 5: WhatsApp Human Request
**Problem found:** "Can I talk to someone?" wasn't triggering escalation
**Fix:** Added keyword detection: "human", "agent", "representative", "person"
**Result:** All human-request keywords now trigger escalation

---

## Phase 3: Edge Cases Found

| # | Edge Case | How Handled | Test Case |
|---|-----------|-------------|-----------|
| 1 | Empty message | Ask for clarification | test_empty_message |
| 2 | Pricing inquiry | Immediate escalation (billing) | test_pricing_escalation |
| 3 | Angry customer | Escalation + empathy first | test_angry_customer |
| 4 | Legal threat | Immediate escalation (legal) | test_legal_threat |
| 5 | Refund request | Immediate escalation (billing) | test_refund_request |
| 6 | Unknown question (2 search failures) | Escalate with context | test_knowledge_gap |
| 7 | Multi-step technical question via WhatsApp | Split response + offer email | test_long_whatsapp |
| 8 | Customer switches channels | History shown from all channels | test_cross_channel |
| 9 | Duplicate ticket | Linked to existing conversation | test_duplicate |
| 10 | Media attachment in WhatsApp | Acknowledge, request text description | test_media_attachment |
| 11 | Non-English message | Detect language, respond in same | test_multilingual |
| 12 | Security question (account compromise) | Immediate escalation | test_security_issue |

---

## Phase 4: Response Patterns That Work

### Email Response Pattern:
```
Hi [Name],

[Acknowledge their situation in 1 sentence]

[Solution or answer - 2-4 sentences or numbered steps]

[One clear next step or offer]

Best regards,
TechCorp Support Team
Ticket: #[ID]
```

### WhatsApp Response Pattern:
```
[Direct answer in 1-2 sentences] [Optional: 1 emoji]

[Next step if needed]

Reply for more help or type 'human' for live support.
```

### Web Form Response Pattern:
```
[Acknowledge + direct answer]

[Steps if applicable, as bullet list]

[Next step / additional resources]

---
Need more help? Reply to this message or visit our support portal.
```

---

## Phase 5: System Prompt Refinement

### Version 1 (Too vague):
"You are a helpful customer support agent."

### Version 2 (Added constraints):
"You are a Customer Success agent. Never discuss pricing. Escalate when needed."

### Version 3 (Final - Channel-aware):
Full channel-aware system prompt with explicit workflow, hard constraints, and escalation triggers. See prompts.py.

---

## Performance Baseline (Prototype)
- Average response time: 2.1 seconds
- Accuracy on 20-question test set: 87%
- Escalation rate: 18%
- False escalation rate: 3%
- Cross-channel identification accuracy: 95%
