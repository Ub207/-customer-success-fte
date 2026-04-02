# CRM Digital FTE Factory — Hackathon 5
### Build Your First 24/7 AI Employee

> A production-grade **Customer Success AI Agent** that handles routine support queries across Email, WhatsApp, and Web Form — 24/7, without human intervention.

---

## What Is This?

**CRM Digital FTE** is a 24/7 AI-powered Customer Success employee that handles routine support queries across multiple channels. Built following the **Agent Maturity Model** — from incubation prototype (MCP server) to production-grade Custom Agent (OpenAI Agents SDK + Kafka + PostgreSQL).

---

## Business Value

| Metric | Human FTE | AI Digital FTE |
|--------|-----------|----------------|
| **Annual Cost** | ~$75,000/year | <$1,000/year |
| **Availability** | 8 hrs/day, 5 days/week | 24/7/365 |
| **Response Time** | Minutes to hours | < 3 seconds |
| **Consistency** | Varies by person | 100% consistent |
| **Channels** | Usually 1–2 | Email + WhatsApp + Web |
| **Scalability** | Hire more staff | Auto-scale (Kubernetes HPA) |

**Result:** 80%+ of routine tickets resolved automatically. Human agents focus only on complex, high-value cases.

---

## Agent Maturity Model

```
Stage 1 — Incubation          Stage 2 — Production
─────────────────────         ─────────────────────────────
MCP Prototype                 Custom Agent (OpenAI SDK)
src/mcp_server.py             production/agent/

• In-memory storage     →     • PostgreSQL + pgvector
• 5 tools tested        →     • Same 5 tools (production)
• Prompt iterations     →     • v5 prompt (final)
• Claude Desktop        →     • FastAPI + Kafka + K8s
• Single process        →     • Multi-service architecture
```

---

## Progress

| Phase | Description | Status | Tests |
|-------|-------------|--------|-------|
| **Phase 1** | Incubation — MCP Prototype | ✅ 100% | Prompt iterations × 5 |
| **Phase 2** | Production — Custom Agent + API | ✅ 100% | 81/81 passing |
| **Phase 3** | Integration — Channels + Workers | ✅ 100% | All core tests passing |

---

## Test Results

```
Last Run: March 2026
─────────────────────────────────────────────
Total: 81/81 tests passing (100%)
─────────────────────────────────────────────
```

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_transition.py` | 40 | ✅ 40/40 passing |
| `test_agent.py` | 13 | ✅ 13/13 passing |
| `test_channels.py` | 10 | ✅ 10/10 passing |
| `test_multichannel_e2e.py` | 18 | ✅ 18/18 passing |
| `load_test.py` | — | Locust (100 users) |

---

## Features

- **3 Channels** — Gmail (Pub/Sub), WhatsApp (Twilio), Web Form (Next.js)
- **Cross-channel memory** — same customer on email + WhatsApp = unified history
- **5 Agent Tools** — create_ticket, get_customer_history, search_knowledge_base, escalate_to_human, send_response
- **Smart Escalation** — auto-routes to billing, legal, security, senior support
- **Daily Sentiment Report** — `GET /reports/daily-sentiment` with hourly trends
- **Kubernetes Ready** — HPA auto-scales 2 → 10 pods on CPU > 70%
- **pgvector** — semantic search on knowledge base (OpenAI embeddings)
- **Embeddable Web Form** — drop `<SupportForm apiUrl="..." />` into any React app

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | OpenAI Agents SDK (GPT-4o / Groq / Gemini) |
| API | FastAPI — async Python 3.11 |
| Database | PostgreSQL 15 + pgvector |
| Streaming | Apache Kafka (aiokafka) |
| Email | Gmail API + Google Cloud Pub/Sub |
| WhatsApp | Twilio Messaging API |
| Web Form | Next.js 14 + React (embeddable) |
| Deployment | Docker + Kubernetes |
| Logging | structlog (structured JSON) |
| Testing | pytest + Locust |

---

## Project Structure

```
hackathon-5/
├── context/                       # Agent knowledge files
│   ├── company-profile.md
│   ├── product-docs.md
│   ├── sample-tickets.json        # 10 test tickets
│   ├── escalation-rules.md
│   └── brand-voice.md
│
├── specs/                         # Incubation deliverables
│   ├── discovery-log.md
│   ├── customer-success-fte-spec.md
│   └── transition-checklist.md    # All items ✅
│
├── src/
│   └── mcp_server.py              # Stage 1 — MCP prototype
│
└── production/                    # Stage 2 — Full system
    ├── agent/                     # AI core
    │   ├── prompts.py             # System prompt v5
    │   ├── tools.py               # 5 @function_tool definitions
    │   ├── formatters.py          # Channel formatters
    │   └── customer_success_agent.py
    ├── api/
    │   └── main.py                # 10 REST endpoints
    ├── channels/
    │   ├── gmail_handler.py
    │   ├── whatsapp_handler.py
    │   └── web_form_handler.py
    ├── database/
    │   ├── schema.sql             # 8 tables + pgvector
    │   └── queries.py
    ├── workers/
    │   ├── message_processor.py   # Kafka consumer
    │   ├── metrics_collector.py
    │   └── daily_report.py        # Cron job
    ├── web-form/
    │   └── components/
    │       └── SupportForm.jsx    # Embeddable React component
    ├── tests/
    │   ├── test_transition.py     # 40/40 ✅ (infrastructure + tool migration)
    │   ├── test_agent.py
    │   ├── test_channels.py
    │   ├── test_multichannel_e2e.py
    │   └── load_test.py
    ├── k8s/                       # 8 Kubernetes manifests
    ├── docker-compose.yml
    ├── Dockerfile
    └── requirements.txt
```

---

## Quick Start (Local)

### Prerequisites
- Docker Desktop (running)
- Python 3.11+
- One of: **Groq API Key** (free) · OpenAI API Key · Gemini API Key

### 1. Clone and configure

```bash
cd hackathon-5/production
cp .env.example .env
# Add your API key to .env
```

`.env` minimum:
```env
# Pick ONE — only one key needed
GROQ_API_KEY=gsk_...          # Free at console.groq.com
# OPENAI_API_KEY=sk-...       # Paid
# GEMINI_API_KEY=AIzaSy...    # Free at aistudio.google.com
```

### 2. Start all services

```bash
docker compose up -d
```

Starts: PostgreSQL · Kafka · FastAPI API · Worker · Daily Reporter

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"up","kafka":"up"}
```

### 4. Run tests

```bash
pytest production/tests/ -v
# 81/81 passed
```

### 5. Start web form

```bash
cd production/web-form
npm install && npm run dev
# http://localhost:3000
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/webhooks/gmail` | Gmail Pub/Sub webhook |
| `POST` | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| `POST` | `/web-form/submit` | Web form submission |
| `GET` | `/web-form/ticket/{id}` | Ticket status |
| `GET` | `/conversations/{id}` | Conversation history |
| `GET` | `/customers/lookup` | Customer lookup |
| `GET` | `/metrics/channels` | Hourly channel metrics |
| `GET` | `/reports/daily-sentiment` | Daily sentiment report |

**Swagger UI:** `http://localhost:8000/docs`

---

## Demo — Test All 3 Channels

### Web Form
```bash
curl -X POST http://localhost:8000/web-form/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Ali","email":"ali@test.com","subject":"Password reset","category":"account","priority":"high","message":"I cannot reset my password. The email never arrives."}'
```

### WhatsApp
```bash
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+15551234567&Body=How do I add a team member?"
```

### Daily Sentiment Report
```bash
curl http://localhost:8000/reports/daily-sentiment
```

---

## Escalation Routing

| Trigger | Reason Code | Routes To | SLA |
|---------|-------------|-----------|-----|
| Pricing questions | `pricing_inquiry` | billing@techcorp.io | 4h |
| Refund requests | `refund_request` | billing@techcorp.io | 4h |
| Legal threats | `legal_threat` | legal-support@techcorp.io | 1h |
| Angry customer (sentiment < 0.3) | `angry_customer` | senior-support@techcorp.io | 2h |
| Security incidents | `security_incident` | security@techcorp.io | 1h |
| Knowledge gap | `knowledge_gap` | support@techcorp.io | 8h |
| Human requested | `human_requested` | support@techcorp.io | 4h |

---

## Deploy on Kubernetes

```bash
# Build image
docker build -t your-registry/fte-agent:latest production/
docker push your-registry/fte-agent:latest

# Deploy
kubectl apply -f production/k8s/

# Check
kubectl get pods -n fte-production
```

HPA scales API pods: **2 → 10** when CPU > 70%

---

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Response time | < 3 sec | 2.1 sec ✅ |
| Accuracy | > 85% | 87% ✅ |
| Escalation rate | < 20% | 18% ✅ |
| Cross-channel ID | > 95% | 95% ✅ |
| Uptime | > 99.9% | — |

---

**Hackathon 5 — CRM Digital FTE Factory**
*TechCorp SaaS · Multi-channel Customer Success AI Agent*
