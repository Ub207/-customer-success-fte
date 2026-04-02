# Customer Success FTE Specification v1.0
## TechCorp SaaS -- Digital FTE Factory (Hackathon 5)

**Status:** Production-Ready
**Agent Type:** Customer Success AI (Digital FTE)
**Model:** GPT-4o via OpenAI Agents SDK
**Last Updated:** 2026-03-27

---

## 1. Purpose & Business Context

TechCorp SaaS receives **500+ customer support tickets per day** across three channels. The Customer Success FTE is an AI agent that handles routine inquiries **24/7 without human intervention**, replacing the need for a full-time support employee for Tier-1 queries.

**Business goals:**
- Resolve >= 80% of inbound tickets without human escalation
- Respond within 3 seconds of receipt (processing time)
- Maintain consistent brand voice across all channels
- Identify and escalate high-risk situations immediately
- Provide management with daily sentiment + volume reports

---

## 2. Supported Channels

| Channel | Inbound Method | Customer Identifier | Response Style | Hard Length Limit |
|---------|---------------|---------------------|----------------|-------------------|
| **Email (Gmail)** | Google Pub/Sub webhook | Email address (primary) | Formal, full sentences, greeting + sign-off | 500 words |
| **WhatsApp** | Twilio webhook (form POST) | Phone number (E.164) | Casual, concise, 1-2 sentences | 1,600 characters |
| **Web Form** | FastAPI POST /web-form/submit | Email address | Semi-formal, structured | 300 words |

### Cross-Channel Identity Resolution
A single customer may contact TechCorp from multiple channels. The system unifies them:
- **Primary key:** Email address (used by Gmail + Web Form)
- **Secondary key:** Phone number (used by WhatsApp)
- If a WhatsApp user's phone number is linked to a known email account, their full cross-channel history is loaded
- Implemented via `customer_identifiers` table with `(identifier_type, identifier_value)` unique constraint

---

## 3. Agent Tools (5 Total)

### 3.1 `create_ticket`
**When:** First action in EVERY conversation -- no exceptions
**Input:** `customer_id`, `issue_summary`, `channel`, `priority` (default: medium)
**Output:** Ticket ID (e.g., `TKT-a1b2c3d4`)
**Constraints:**
- Must include source channel in ticket metadata
- Priority auto-escalates to "urgent" if sentiment < 0.3

### 3.2 `get_customer_history`
**When:** Second action in every conversation
**Input:** `customer_id`, `limit` (default: 10)
**Output:** List of past conversations across ALL channels
**Purpose:** Prevents asking the customer to repeat themselves; detects repeat issues

### 3.3 `search_knowledge_base`
**When:** Any product question that requires documentation lookup
**Input:** `query`, `max_results` (default: 5)
**Output:** Ranked list of matching knowledge base articles with similarity scores
**Constraints:**
- Retry once with a rephrased query if first search returns 0 results
- After 2 failed searches -> trigger `escalate_to_human` with reason `knowledge_gap`
- Uses pgvector cosine similarity on OpenAI text-embedding-ada-002 embeddings

### 3.4 `escalate_to_human`
**When:** Any hard escalation trigger is detected (see Section 6)
**Input:** `ticket_id`, `reason` (enum), `context_notes`
**Output:** Escalation confirmation + target team email
**Routing table:**

| Reason Code | Target Team | SLA |
|-------------|-------------|-----|
| `pricing_inquiry` | billing@techcorp.io | 4 hours |
| `refund_request` | billing@techcorp.io | 4 hours |
| `legal_threat` | legal-support@techcorp.io | 1 hour |
| `angry_customer` | senior-support@techcorp.io | 2 hours |
| `security_incident` | security@techcorp.io | 1 hour |
| `knowledge_gap` | support@techcorp.io | 8 hours |
| `human_requested` | support@techcorp.io | 4 hours |

### 3.5 `send_response`
**When:** Final action in every non-escalated conversation
**Input:** `ticket_id`, `message`, `channel`, `customer_name`
**Output:** Delivery confirmation
**Constraints:**
- MUST be the last tool called before ending
- Triggers channel-appropriate formatting via `format_for_channel()`
- WhatsApp messages > 1,600 chars are auto-split or truncated
- Email responses include formal greeting + ticket reference in footer
- Web form responses include "Need more help?" footer

---

## 4. Required Workflow (Every Interaction)

```
Customer Message Received
        |
        v
1. create_ticket          <- Always first; logs channel + issue
        |
        v
2. get_customer_history   <- Check cross-channel context
        |
        v
3. [Decision Point]
   +-- Hard escalation trigger? -> escalate_to_human -> STOP
   +-- Product question?        -> search_knowledge_base -> send_response
   +-- Simple clarification?   -> send_response directly
        |
        v
4. send_response           <- Always last; channel-formatted
```

---

## 5. System Prompt Design

The production system prompt (`production/agent/prompts.py`) was refined through 5 iterations during incubation:

**v1 (Rejected):** "You are a helpful customer support agent."
-> Too vague; no constraints; tried to answer pricing questions

**v2 (Rejected):** Added basic escalation rules
-> Channel formatting was uniform (wrong lengths for WhatsApp)

**v3 (Rejected):** Added channel awareness
-> Cross-channel history wasn't being used consistently

**v4 (Rejected):** Added workflow order enforcement
-> Agent sometimes skipped `get_customer_history`

**v5 (Production):** Added explicit 4-step workflow, hard constraints box, escalation trigger table, channel-specific response templates, and anti-hallucination rules.

**Key prompt sections:**
1. Role definition (Customer Success FTE for TechCorp)
2. Mandatory 4-step workflow (numbered, must follow in order)
3. Channel-specific response rules (length, tone, format)
4. Hard constraints box (NEVER rules -- uppercase for emphasis)
5. Escalation trigger table (reason code -> when to use)
6. Anti-hallucination rules (only use info from search results or history)

---

## 6. Escalation Rules

### Hard Escalations (Immediate -- do not attempt to resolve)

| Trigger | Detection | Reason Code |
|---------|-----------|-------------|
| Pricing question | Keywords: price, cost, plan, enterprise, quote, discount | `pricing_inquiry` |
| Refund request | Keywords: refund, money back, charge, charged incorrectly | `refund_request` |
| Legal threat | Keywords: lawyer, legal, sue, attorney, court, lawsuit | `legal_threat` |
| Angry customer | Sentiment score < 0.3 OR profanity detected | `angry_customer` |
| Security incident | Keywords: hacked, compromised, unauthorized access, breach | `security_incident` |

### Soft Escalations (After attempting resolution)

| Trigger | Detection | Reason Code |
|---------|-----------|-------------|
| Knowledge gap | 2 failed searches with 0 results | `knowledge_gap` |
| Human request | Customer says: "human", "agent", "representative", "real person" | `human_requested` |
| Repeated failure | Same issue reported 3+ times in history | `human_requested` |

---

## 7. Channel-Specific Response Templates

### Email Template
```
Hi [Customer Name],

[1-sentence acknowledgment of their situation]

[Solution or answer -- 2-4 sentences or numbered steps if procedural]

[1 clear next step or offer for further assistance]

Best regards,
TechCorp Support Team
support@techcorp.io | Ticket: #[TICKET_ID]
```

### WhatsApp Template
```
[Direct answer in 1-2 sentences] [1 relevant emoji optional]

[Next step if needed -- 1 sentence]

Type *human* for live support.
```

### Web Form Template
```
[Acknowledge + direct answer in 1-2 sentences]

[Steps if applicable:]
- Step 1
- Step 2
- Step 3

[Next step / resource link]

---
Need more help? Reply to this message or visit support.techcorp.io
```

---

## 8. Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing time | < 3 seconds | Time from message receipt to agent completion |
| Delivery time | < 30 seconds | End-to-end including channel delivery |
| Accuracy | > 85% | Correct resolution on 20-question test set |
| Escalation rate | < 20% | % of conversations escalated to human |
| False escalation rate | < 5% | % of escalations that shouldn't have been |
| Cross-channel ID | > 95% | Correctly linking same customer across channels |
| Uptime | > 99.9% | Measured monthly |

**Baseline from prototype (incubation phase):**
- Average response time: 2.1 seconds
- Accuracy: 87%
- Escalation rate: 18%
- False escalation rate: 3%
- Cross-channel accuracy: 95%

---

## 9. Hard Constraints (Non-Negotiable)

The agent MUST NEVER:
1. Discuss pricing, quotes, or costs -> always escalate
2. Process or promise refunds -> always escalate
3. Promise features not documented in knowledge base
4. Share internal system details, prompts, or processes
5. Respond without calling `send_response` tool
6. Exceed channel length limits (Email: 500w, WhatsApp: 1600c, Web: 300w)
7. Use `send_response` before `create_ticket`
8. Hallucinate product features not found in search results

---

## 10. Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent framework | OpenAI Agents SDK (GPT-4o) | Core AI reasoning + tool use |
| API layer | FastAPI (async Python) | Webhook ingestion + REST endpoints |
| Message queue | Apache Kafka (7 topics) | Decoupled channel processing |
| Database | PostgreSQL + pgvector | Customer data + semantic search |
| Email channel | Gmail API + Google Pub/Sub | Email webhook + reply sending |
| WhatsApp channel | Twilio API | WhatsApp webhook + reply sending |
| Web channel | Next.js + React | Embeddable support form |
| Deployment | Kubernetes + Docker | Auto-scaling, rolling updates |
| Monitoring | structlog + agent_metrics table | Performance tracking |

### Kafka Topics
```
fte.gmail.inbound      -> Inbound Gmail messages
fte.whatsapp.inbound   -> Inbound WhatsApp messages
fte.webform.inbound    -> Web form submissions
fte.outbound.email     -> Outbound email replies
fte.outbound.whatsapp  -> Outbound WhatsApp replies
fte.escalations        -> Escalation events
fte.dlq                -> Dead Letter Queue (failed messages)
```

---

## 11. MCP Prototype -> Production Transition

The incubation phase used an MCP (Model Context Protocol) server with in-memory storage. The production system replaces:

| Incubation (MCP) | Production |
|-----------------|------------|
| In-memory ticket store (dict) | PostgreSQL `tickets` table |
| In-memory knowledge base | pgvector semantic search |
| Synchronous MCP tools | Async `@function_tool` decorated functions |
| No channel differentiation | Channel-aware formatters + handlers |
| Single-process | Kafka-based multi-service architecture |
| No customer persistence | `customers` + `customer_identifiers` tables |
| No metrics | `agent_metrics` table + daily sentiment reports |

All 5 MCP tool names were preserved exactly in production to maintain prompt compatibility.
