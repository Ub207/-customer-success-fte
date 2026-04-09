# CRM Digital FTE Factory

> **Build Your First 24/7 AI Employee** — A production-grade Customer Success AI Agent that autonomously handles support queries across Email, WhatsApp, and Web Form.

---

## Overview

**CRM Digital FTE** replaces a routine customer support role with a fully autonomous AI agent. It receives messages from three channels, processes them through an AI agent with tool use, stores everything in PostgreSQL, and responds — all without human intervention.

Built on the **Agent Maturity Model**: from a Claude Desktop MCP prototype (Stage 1) to a full production system with FastAPI, Kafka, and Kubernetes (Stage 2).

---

## Business Case

| Metric | Human FTE | AI Digital FTE |
|--------|-----------|----------------|
| Annual Cost | ~$75,000/year | <$1,000/year |
| Availability | 8 hrs/day, 5 days/week | 24/7/365 |
| Response Time | Minutes to hours | < 3 seconds |
| Consistency | Varies | 100% consistent |
| Channels | 1–2 | Email + WhatsApp + Web |
| Scalability | Hire more staff | Auto-scale via Kubernetes HPA |

**Result:** 80%+ of routine tickets resolved automatically. Human agents handle only complex, high-value cases.

---

## Architecture

```
Customer Message
      │
      ├── Gmail (Pub/Sub) ──────────┐
      ├── WhatsApp (Twilio) ────────┤
      └── Web Form (Next.js) ───────┤
                                    ▼
                             FastAPI (port 8000)
                                    │
                              Kafka Topic
                                    │
                            Message Processor
                            (Kafka Consumer)
                                    │
                      ┌─────────────▼─────────────┐
                      │    AI Agent (OpenAI SDK)   │
                      │                           │
                      │  1. create_ticket         │
                      │  2. get_customer_history  │
                      │  3. search_knowledge_base │
                      │  4. escalate_to_human     │
                      │  5. send_response         │
                      └─────────────┬─────────────┘
                                    │
                             PostgreSQL + pgvector
                             (Neon / local Docker)
```

---

## Agent Maturity Model

```
Stage 1 — Incubation              Stage 2 — Production
──────────────────────            ─────────────────────────────
MCP Prototype                     Custom Agent (OpenAI Agents SDK)
src/mcp_server.py                 production/agent/

• In-memory storage       →       • PostgreSQL + pgvector
• 5 tools tested          →       • Same 5 tools (production hardened)
• Prompt iterations x5    →       • v5 system prompt (final)
• Claude Desktop          →       • FastAPI + Kafka + Kubernetes
• Single process          →       • Multi-service architecture
```

---

## Features

- **3 Channels** — Gmail (Google Cloud Pub/Sub), WhatsApp (Twilio), Web Form (Next.js)
- **Cross-channel memory** — same customer on email + WhatsApp = unified conversation history
- **5 Agent Tools** — `create_ticket`, `get_customer_history`, `search_knowledge_base`, `escalate_to_human`, `send_response`
- **Smart Escalation** — auto-routes to billing, legal, security, or senior support with SLA enforcement
- **Semantic KB Search** — pgvector embeddings for knowledge base lookup
- **Embeddable Web Form** — drop `<SupportForm apiUrl="..." />` into any React app
- **Daily Sentiment Report** — `GET /reports/daily-sentiment` with hourly trend data
- **Kubernetes Ready** — HPA auto-scales 2 → 10 pods when CPU > 70%
- **Structured Logging** — structlog JSON logs for all services

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | OpenAI Agents SDK (GPT-4o / Groq / Gemini) |
| API | FastAPI — async Python 3.11 |
| Database | PostgreSQL 15 + pgvector |
| Message Queue | Apache Kafka (aiokafka) / Redpanda Cloud |
| Email | Gmail API + Google Cloud Pub/Sub |
| WhatsApp | Twilio Messaging API |
| Web Form | Next.js 14 + React + Tailwind CSS |
| Deployment | Docker + Kubernetes (HPA) |
| Logging | structlog (structured JSON) |
| Testing | pytest (81 tests) + Locust (load testing) |

---

## Project Structure

```
hackathon-5/
│
├── context/                          # Agent knowledge files
│   ├── brand-voice.md                # Tone and communication style
│   ├── company-profile.md            # Company info the agent knows
│   ├── product-docs.md               # Product knowledge base
│   ├── escalation-rules.md           # When to escalate to humans
│   └── sample-tickets.json           # Example tickets for reference
│
├── src/                              # Stage 1 — Incubation prototype
│   ├── mcp_server.py                 # MCP server (Claude Desktop)
│   └── skills_manifest.py            # Agent skills definition
│
├── specs/                            # Design and planning docs
│   ├── customer-success-fte-spec.md
│   ├── discovery-log.md
│   └── transition-checklist.md
│
└── production/                       # Stage 2 — Full production system
    │
    ├── agent/                        # AI Agent core
    │   ├── customer_success_agent.py # Agent runner (OpenAI Agents SDK)
    │   ├── tools.py                  # 5 @function_tool definitions
    │   ├── prompts.py                # System prompt v5 (final)
    │   └── formatters.py             # Channel-specific response formatting
    │
    ├── api/
    │   └── main.py                   # FastAPI app — 9 REST endpoints
    │
    ├── channels/                     # Inbound message handlers
    │   ├── gmail_handler.py          # Gmail Pub/Sub webhook
    │   ├── whatsapp_handler.py       # Twilio webhook handler
    │   └── web_form_handler.py       # Web form submission handler
    │
    ├── workers/                      # Background Kafka consumers
    │   ├── message_processor.py      # Core worker: Kafka → Agent → DB
    │   ├── response_delivery.py      # Sends replies back to customer
    │   ├── ticket_lifecycle.py       # Manages ticket status transitions
    │   ├── metrics_collector.py      # Collects stats every 5 minutes
    │   └── daily_report.py           # Generates daily sentiment report
    │
    ├── database/
    │   ├── schema.sql                # 8 PostgreSQL tables + pgvector
    │   ├── queries.py                # All DB queries
    │   └── migrations/               # Schema migration files
    │
    ├── web-form/                     # Next.js frontend
    │   ├── pages/
    │   │   ├── index.js              # Dashboard home
    │   │   ├── webform.js            # Customer support form
    │   │   ├── whatsapp.js           # WhatsApp dashboard
    │   │   ├── gmail.js              # Gmail dashboard
    │   │   └── api/support/submit.js # API route → FastAPI proxy
    │   └── components/
    │       ├── SupportForm.jsx       # Embeddable React widget
    │       ├── WebFormDashboard.jsx
    │       ├── WhatsAppDashboard.jsx
    │       └── GmailDashboard.jsx
    │
    ├── k8s/                          # Kubernetes manifests
    │   ├── deployment-api.yaml
    │   ├── deployment-worker.yaml
    │   ├── hpa.yaml                  # Auto-scale: 2 → 10 pods at 70% CPU
    │   ├── cronjob-daily-reporter.yaml
    │   ├── ingress.yaml
    │   └── secrets.yaml
    │
    ├── tests/
    │   ├── test_agent.py             # 13 agent unit tests
    │   ├── test_channels.py          # 10 channel handler tests
    │   ├── test_multichannel_e2e.py  # 18 end-to-end flow tests
    │   ├── test_transition.py        # 40 Stage 1→2 migration tests
    │   └── load_test.py              # Locust: 100 concurrent users
    │
    ├── kafka_client.py               # Kafka producer/consumer (SASL/SSL support)
    ├── logging_config.py             # Structured JSON logging
    ├── docker-compose.yml            # Local dev: PostgreSQL + Kafka + API + Worker
    ├── Dockerfile
    └── requirements.txt
```

---

## Quick Start (Local — No Docker Required)

The project is pre-configured to use **Neon** (cloud PostgreSQL) and **Redpanda Cloud** (managed Kafka), so you can run without Docker.

### Prerequisites

- Python 3.11+
- Node.js 18+ (for web form)
- One API key: **Gemini** (free) · Groq (free) · OpenAI (paid)

### 1. Clone

```bash
git clone https://github.com/Ub207/-customer-success-fte.git
cd customer-success-fte
```

### 2. Configure environment

```bash
cp production/.env.example production/.env
# Edit production/.env and add your API key
```

Minimum `.env`:
```env
# Pick ONE
GEMINI_API_KEY=AIzaSy...        # Free — aistudio.google.com
# GROQ_API_KEY=gsk_...          # Free — console.groq.com
# OPENAI_API_KEY=sk-...         # Paid

# Cloud services (pre-filled if using Neon + Redpanda)
DATABASE_URL=postgresql://...
KAFKA_BOOTSTRAP_SERVERS=...
KAFKA_SASL_USERNAME=...
KAFKA_SASL_PASSWORD=...
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
```

### 3. Install Python dependencies

```bash
cd production
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate        # Mac/Linux
pip install -r requirements.txt
```

### 4. Start the API

```bash
# From project root
source production/venv/Scripts/activate
uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","database":true}
```

### 6. Start the web form

```bash
cd production/web-form
npm install
npm run dev
# http://localhost:3000
```

---

## Quick Start (Docker)

### Prerequisites
- Docker Desktop running
- One API key (Gemini / Groq / OpenAI)

```bash
cd production
cp .env.example .env
# Add API key to .env

docker compose up -d
# Starts: PostgreSQL · Kafka · FastAPI · Worker · Daily Reporter

curl http://localhost:8000/health
```

---

## API Reference

Base URL: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe — Kubernetes health check |
| `POST` | `/webhooks/gmail` | Gmail Pub/Sub push webhook |
| `POST` | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| `POST` | `/web-form/submit` | Customer web form submission |
| `GET` | `/web-form/ticket/{id}` | Ticket status lookup |
| `GET` | `/conversations/{id}` | Full conversation with all messages |
| `GET` | `/customers/lookup` | Customer lookup by email or phone |
| `GET` | `/metrics/channels` | Per-channel stats (last 24 hours) |
| `GET` | `/reports/daily-sentiment` | Daily sentiment + performance report |

---

## Demo — Test All 3 Channels

### Web Form
```bash
curl -X POST http://localhost:8000/web-form/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ali",
    "email": "ali@example.com",
    "subject": "Cannot reset password",
    "category": "account",
    "priority": "high",
    "message": "I cannot reset my password. The reset email never arrives."
  }'
```

### WhatsApp
```bash
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+15551234567&Body=How do I add a team member to my project?"
```

### Daily Report
```bash
curl "http://localhost:8000/reports/daily-sentiment?report_date=2026-04-08"
```

---

## Agent Tools

The AI agent has exactly 5 tools and must call them in order:

| # | Tool | Purpose |
|---|------|---------|
| 1 | `create_ticket` | Log the interaction first — always |
| 2 | `get_customer_history` | Retrieve prior interactions across all channels |
| 3 | `search_knowledge_base` | Semantic search on product docs |
| 4 | `escalate_to_human` | Route to specialist team with SLA |
| 5 | `send_response` | Deliver reply — must always be last |

---

## Escalation Routing

| Trigger | Reason Code | Routes To | SLA |
|---------|-------------|-----------|-----|
| "lawyer", "sue", "legal", "court" | `legal_threat` | legal-support@techcorp.io | 1 hour |
| Suspected account compromise | `security_incident` | security@techcorp.io | 1 hour |
| Profanity, aggression, threats to cancel | `angry_customer` | senior-support@techcorp.io | 2 hours |
| Pricing or plan cost questions | `pricing_inquiry` | billing@techcorp.io | 4 hours |
| Refund requests | `refund_request` | billing@techcorp.io | 4 hours |
| "I want to speak to a human" | `human_requested` | support@techcorp.io | 4 hours |
| 2 failed KB searches | `knowledge_gap` | support@techcorp.io | 8 hours |

---

## Test Results

```
Total: 81/81 passing (100%)
```

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_transition.py` | 40 | 40/40 passing |
| `test_agent.py` | 13 | 13/13 passing |
| `test_channels.py` | 10 | 10/10 passing |
| `test_multichannel_e2e.py` | 18 | 18/18 passing |
| `load_test.py` | — | Locust — 100 concurrent users |

### Run tests

```bash
# From project root
source production/venv/Scripts/activate
pytest production/tests/ -v
```

---

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Response time | < 3 sec | 2.1 sec |
| Accuracy | > 85% | 87% |
| Escalation rate | < 20% | 18% |
| Cross-channel ID match | > 95% | 95% |

---

## Deploy on Kubernetes

```bash
# Build and push image
docker build -t your-registry/fte-agent:latest production/
docker push your-registry/fte-agent:latest

# Apply all manifests
kubectl apply -f production/k8s/

# Check status
kubectl get pods -n fte-production
kubectl get hpa -n fte-production
```

HPA auto-scales API pods: **2 → 10** when CPU > 70%.

---

## Embed the Web Form

Drop the support form into any React app:

```jsx
import { SupportForm } from './components/SupportForm'

export default function ContactPage() {
  return <SupportForm apiUrl="https://your-api.com" />
}
```

---

## Development

### Run the background worker

```bash
source production/venv/Scripts/activate
python -m production.workers.message_processor
```

### Seed the knowledge base

```bash
python scripts/seed_knowledge_base.py
```

### Load test (Locust)

```bash
pip install locust
locust -f production/tests/load_test.py --host=http://localhost:8000
# Open http://localhost:8089 — set 100 users, 10 spawn rate
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | One of three | Google Gemini API key (free) |
| `GROQ_API_KEY` | One of three | Groq API key (free) |
| `OPENAI_API_KEY` | One of three | OpenAI API key (paid) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | Yes | Kafka broker address |
| `KAFKA_SASL_USERNAME` | If using Redpanda/cloud Kafka | SASL username |
| `KAFKA_SASL_PASSWORD` | If using Redpanda/cloud Kafka | SASL password |
| `KAFKA_SECURITY_PROTOCOL` | If using Redpanda/cloud Kafka | `SASL_SSL` |
| `KAFKA_SASL_MECHANISM` | If using Redpanda/cloud Kafka | `SCRAM-SHA-256` |
| `TWILIO_ACCOUNT_SID` | WhatsApp only | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | WhatsApp only | Twilio auth token |
| `GMAIL_USER_EMAIL` | Gmail only | Gmail address |

---

**Hackathon 5 — CRM Digital FTE Factory**
*TechCorp SaaS · Multi-channel Customer Success AI Agent · Built with OpenAI Agents SDK + FastAPI + Kafka + PostgreSQL*
