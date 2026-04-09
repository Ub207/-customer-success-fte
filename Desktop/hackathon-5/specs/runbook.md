# Incident Response Runbook — Customer Success FTE (CRM Digital FTE Factory)

**Service:** Customer Success AI Agent
**Version:** 1.0.0
**Last Updated:** 2026-04-09
**Owner:** Platform Engineering

---

## Table of Contents

1. [Incident Classification](#1-incident-classification)
2. [Service Map](#2-service-map)
3. [Common Incidents and Responses](#3-common-incidents-and-responses)
4. [Runbook Commands Reference](#4-runbook-commands-reference)
5. [Escalation Contacts](#5-escalation-contacts)
6. [Recovery Procedures](#6-recovery-procedures)
7. [Post-Incident Checklist](#7-post-incident-checklist)

---

## 1. Incident Classification

| Severity | Label | Definition | Response Time | Resolution Target |
|----------|-------|------------|---------------|-------------------|
| Critical | **P1** | Complete service outage, data loss, or security breach. All channels down. | 5 minutes | 1 hour |
| High     | **P2** | Partial outage (one or more channels down), severe performance degradation, or >30% escalation rate. | 15 minutes | 4 hours |
| Medium   | **P3** | Non-critical feature broken, high latency without full outage, single customer data issue. | 1 hour | 24 hours |
| Low      | **P4** | Cosmetic issues, minor feature requests, non-impacting warnings. | Next business day | 72 hours |

### Severity Decision Tree

```
Is the API completely unreachable?
  YES → P1 (FTEApiDown alert)
  NO  → Are customers receiving responses?
          NO  → P1 (worker/Kafka down)
          YES → Is latency > 10s?
                  YES → P2 (FTEHighResponseLatency)
                  NO  → Is escalation rate > 30%?
                          YES → P2 (FTEHighEscalationRate)
                          NO  → P3 or P4
```

---

## 2. Service Map

### Architecture Overview

```
Internet
  │
  ├── Gmail Pub/Sub Push ──────────────────────────────────────────┐
  ├── Twilio WhatsApp Webhook ────────────────────────────────────►│
  └── Web Form Browser ─────────────────────────────────────────►│
                                                                   │
                                                          ┌────────▼────────┐
                                                          │  FastAPI (api)   │
                                                          │  :8000           │
                                                          └────────┬────────┘
                                                                   │
                             ┌─────────────────────────────────────┤
                             │                                     │
                    ┌────────▼────────┐                  ┌────────▼────────┐
                    │  Kafka Broker   │                  │  PostgreSQL DB  │
                    │  :9092          │                  │  :5432          │
                    └────────┬────────┘                  └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Worker Pod     │
                    │  (message_      │
                    │  processor)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  OpenAI API     │
                    │  (Agents SDK)   │
                    └─────────────────┘
```

### Service Components

| Component | K8s Resource | Namespace | Port | Health Check |
|-----------|-------------|-----------|------|--------------|
| FastAPI API | `deployment/fte-api` | `fte-production` | 8000 | `GET /health` |
| Kafka Message Worker | `deployment/fte-worker` | `fte-production` | N/A | Pod status |
| PostgreSQL | `statefulset/postgres` | `fte-production` | 5432 | `pg_isready` |
| Kafka Broker | `statefulset/kafka` | `fte-production` | 9092 | `kafka-topics.sh` |
| Daily Report CronJob | `cronjob/fte-daily-reporter` | `fte-production` | N/A | Last job status |
| Metrics Collector | `deployment/fte-metrics-collector` | `fte-production` | N/A | Pod status |

### External Dependencies

| Service | Purpose | Failover |
|---------|---------|---------|
| OpenAI API (`api.openai.com`) | AI agent inference | Return canned response, escalate to human |
| Twilio (`api.twilio.com`) | WhatsApp message delivery | Queue and retry |
| Gmail API / Pub/Sub | Email webhook delivery | Retry via Pub/Sub ack timeout |
| SendGrid (optional) | Outbound email | Fallback SMTP |

---

## 3. Common Incidents and Responses

---

### 3.1 API Pod Down

**Alert:** `FTEApiDown` (P1)
**Symptoms:** `/health` returns 503, Prometheus `up{job="fte-api"} == 0`, customers receive no responses.

**Diagnosis:**

```bash
# Check pod status
kubectl -n fte-production get pods -l app=customer-success-fte,component=api

# View pod events for crash reason
kubectl -n fte-production describe pod -l app=customer-success-fte,component=api

# View recent logs from the failing pod
kubectl -n fte-production logs -l app=customer-success-fte,component=api --tail=100 --previous

# Check if the service endpoint is registered
kubectl -n fte-production get endpoints fte-api
```

**Response Steps:**

1. Check if the pod is in `CrashLoopBackOff` — view logs for Python exceptions.
2. Check if the issue is a failed DB connection at startup (degraded mode message in logs).
3. If OOMKilled, increase memory limits in `deployment-api.yaml` and redeploy.
4. If image pull error, verify the image tag exists in the registry.
5. Force a pod restart:
   ```bash
   kubectl -n fte-production rollout restart deployment/fte-api
   ```
6. Monitor the rollout:
   ```bash
   kubectl -n fte-production rollout status deployment/fte-api
   ```

---

### 3.2 Kafka Consumer Lag / Messages Not Processing

**Alert:** `FTENoMessagesProcessed` (P2)
**Symptoms:** Tickets submitted but no AI responses, Kafka consumer group lag growing, worker pods idle.

**Diagnosis:**

```bash
# Check worker pod health
kubectl -n fte-production get pods -l app=customer-success-fte,component=worker

# View worker logs for consumer errors
kubectl -n fte-production logs -l app=customer-success-fte,component=worker --tail=200

# Check Kafka consumer group lag
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group fte-message-processor --describe

# List all Kafka topics
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check messages in topic (last 10)
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic customer-messages --from-beginning --max-messages 10
```

**Response Steps:**

1. If consumer group shows high lag (>1000 messages), worker is behind — check for errors in logs.
2. If worker is in `CrashLoopBackOff`, review logs for OpenAI API errors or DB connection failures.
3. If OpenAI API is returning rate limit errors (429), the worker will back off automatically — monitor.
4. Restart the worker deployment:
   ```bash
   kubectl -n fte-production rollout restart deployment/fte-worker
   ```
5. If the topic is missing, recreate it:
   ```bash
   kubectl -n fte-production exec -it kafka-0 -- \
     kafka-topics.sh --bootstrap-server localhost:9092 \
     --create --topic customer-messages --partitions 3 --replication-factor 1
   ```

---

### 3.3 Database Connection Failures

**Alert:** Health check returns `"database": false`, API in degraded mode (P2).
**Symptoms:** `/health` returns `{"status": "degraded"}`, DB-dependent endpoints return 500.

**Diagnosis:**

```bash
# Check PostgreSQL pod status
kubectl -n fte-production get pods -l app=postgres

# View PostgreSQL logs
kubectl -n fte-production logs postgres-0 --tail=100

# Check if PostgreSQL is accepting connections
kubectl -n fte-production exec -it postgres-0 -- \
  pg_isready -U fte_user -d fte_production

# Check connection count (connect from a debug pod or API pod)
kubectl -n fte-production exec -it fte-api-<pod-id> -- \
  python -c "import asyncio; from production.database import health_check; print(asyncio.run(health_check()))"

# Check PVC status (disk full?)
kubectl -n fte-production get pvc
kubectl -n fte-production describe pvc postgres-data
```

**Response Steps:**

1. If PostgreSQL pod is down, check PVC health and disk usage.
2. If disk is full, expand the PVC or archive/delete old data.
3. If max connections exceeded, check `max_connections` in PostgreSQL config and connection pool settings in `production/.env`.
4. Restart PostgreSQL (caution — brief downtime):
   ```bash
   kubectl -n fte-production rollout restart statefulset/postgres
   ```
5. If the database schema is corrupted, initiate restore from the latest backup (see [Section 6.3](#63-database-restore)).

---

### 3.4 High Escalation Rate

**Alert:** `FTEHighEscalationRate` — escalations > 30% of tickets (P2).
**Symptoms:** Many tickets marked `escalated`, human agents overwhelmed, OpenAI responses contain errors.

**Diagnosis:**

```bash
# Query escalated tickets from the API metrics endpoint
curl http://fte-api.fte-production.svc:8000/metrics/channels

# Check recent escalation reasons in the DB
kubectl -n fte-production exec -it postgres-0 -- \
  psql -U fte_user -d fte_production -c \
  "SELECT category, COUNT(*) FROM tickets WHERE status='escalated'
   AND created_at >= NOW() - INTERVAL '1 hour' GROUP BY category;"

# Check worker logs for AI response failures
kubectl -n fte-production logs -l app=customer-success-fte,component=worker \
  --tail=500 | grep -i "escalat\|error\|openai"
```

**Common Causes and Fixes:**

| Cause | Fix |
|-------|-----|
| OpenAI API returning errors | Check OpenAI status page; verify `OPENAI_API_KEY` in secrets |
| System prompt too restrictive | Update agent instructions in ConfigMap; redeploy worker |
| Spike of "legal threat" or "sue" tickets | Expected behavior — these auto-escalate by design |
| New ticket type not handled | Update agent tools/instructions to handle the pattern |

**Response Steps:**

1. Check OpenAI API status at `https://status.openai.com`.
2. Verify the API key is valid:
   ```bash
   kubectl -n fte-production get secret fte-secrets -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
   ```
3. If a prompt change is needed, update the ConfigMap and restart the worker.

---

### 3.5 WhatsApp / Twilio Webhook Failures

**Alert:** No WhatsApp tickets being created despite customer messages (P2).
**Symptoms:** Twilio console shows failed delivery, API logs show 4xx on `/webhooks/whatsapp`.

**Diagnosis:**

```bash
# Test the webhook endpoint directly
curl -X POST http://fte-api.fte-production.svc:8000/webhooks/whatsapp \
  -d "From=whatsapp:+1234567890&Body=test+message&MessageSid=SM123"

# View API logs filtered to whatsapp handler
kubectl -n fte-production logs -l app=customer-success-fte,component=api \
  --tail=200 | grep -i whatsapp

# Check Twilio credentials in the secret
kubectl -n fte-production get secret fte-secrets -o yaml | grep -i twilio
```

**Response Steps:**

1. Confirm the Twilio webhook URL points to the correct ingress URL (check `ingress.yaml`).
2. If Twilio signature validation is failing, verify `TWILIO_AUTH_TOKEN` in K8s secrets matches the Twilio console.
3. If the ingress is down, check the ingress controller:
   ```bash
   kubectl -n ingress-nginx get pods
   kubectl -n fte-production get ingress
   ```
4. Test end-to-end by sending a WhatsApp message to the Twilio sandbox number and watching logs in real-time:
   ```bash
   kubectl -n fte-production logs -f -l app=customer-success-fte,component=api
   ```

---

### 3.6 Gmail Webhook Failures

**Alert:** No email tickets being created (P2).
**Symptoms:** Gmail Pub/Sub push subscription shows errors, no email tickets in DB.

**Diagnosis:**

```bash
# Test the Gmail webhook endpoint
curl -X POST http://fte-api.fte-production.svc:8000/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "dGVzdA==", "messageId": "123"}, "subscription": "test"}'

# View API logs for Gmail handler
kubectl -n fte-production logs -l app=customer-success-fte,component=api \
  --tail=200 | grep -i gmail

# Check if Gmail credentials are valid
kubectl -n fte-production get secret fte-secrets -o jsonpath='{.data.GMAIL_CREDENTIALS}' \
  | base64 -d | python -m json.tool | head -5
```

**Response Steps:**

1. Verify the Gmail Pub/Sub push subscription URL is correct in the Google Cloud Console.
2. Check if the service account has the required Gmail API permissions.
3. If the Google OAuth token is expired, rotate credentials:
   - Generate a new service account key in GCP IAM.
   - Update the K8s secret: `kubectl -n fte-production create secret generic fte-secrets --from-file=...`
4. Restart the API pod to reload credentials:
   ```bash
   kubectl -n fte-production rollout restart deployment/fte-api
   ```

---

### 3.7 Agent Responding with Errors

**Alert:** Worker logs show repeated AI response failures (P2/P3).
**Symptoms:** Customers receive error messages, tickets stuck in `processing` state.

**Diagnosis:**

```bash
# Check worker logs for OpenAI errors
kubectl -n fte-production logs -l app=customer-success-fte,component=worker \
  --tail=300 | grep -i "error\|exception\|openai\|rate_limit"

# Check tickets stuck in processing
kubectl -n fte-production exec -it postgres-0 -- \
  psql -U fte_user -d fte_production -c \
  "SELECT id, source_channel, status, created_at
   FROM tickets WHERE status='processing'
   AND created_at < NOW() - INTERVAL '10 minutes'
   ORDER BY created_at ASC LIMIT 20;"

# Manually re-queue a stuck ticket (if supported by the implementation)
# kubectl -n fte-production exec -it fte-worker-<pod-id> -- python -m production.tools.requeue --ticket-id <id>
```

**Response Steps:**

1. If OpenAI is rate-limiting, the exponential backoff in the worker will handle recovery — wait 5-10 minutes.
2. If the model is returning unexpected outputs (hallucination, wrong format), review the system prompt in the ConfigMap.
3. For tickets stuck in `processing`, manually reset them in the DB:
   ```sql
   UPDATE tickets SET status = 'open'
   WHERE status = 'processing'
   AND updated_at < NOW() - INTERVAL '15 minutes';
   ```
4. Restart the worker to pick up the reset tickets:
   ```bash
   kubectl -n fte-production rollout restart deployment/fte-worker
   ```

---

## 4. Runbook Commands Reference

### Health Checks

```bash
# API health
curl -s http://fte-api.fte-production.svc:8000/health | python -m json.tool

# Prometheus metrics
curl -s http://fte-api.fte-production.svc:8000/metrics

# Channel stats (last 24h)
curl -s http://fte-api.fte-production.svc:8000/metrics/channels | python -m json.tool

# PostgreSQL connectivity
kubectl -n fte-production exec -it postgres-0 -- pg_isready -U fte_user

# Kafka broker status
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

### Pod Management

```bash
# List all FTE pods
kubectl -n fte-production get pods -l app=customer-success-fte -o wide

# Tail all component logs simultaneously
kubectl -n fte-production logs -f -l app=customer-success-fte --all-containers --prefix

# Restart a specific component
kubectl -n fte-production rollout restart deployment/fte-api
kubectl -n fte-production rollout restart deployment/fte-worker
kubectl -n fte-production rollout restart deployment/fte-metrics-collector

# Scale up workers for high load
kubectl -n fte-production scale deployment/fte-worker --replicas=5

# Get a shell inside the API pod for debugging
kubectl -n fte-production exec -it \
  $(kubectl -n fte-production get pod -l component=api -o name | head -1) -- /bin/bash
```

### Database Queries

```bash
# Open psql shell
kubectl -n fte-production exec -it postgres-0 -- \
  psql -U fte_user -d fte_production
```

```sql
-- Ticket status summary
SELECT status, source_channel, COUNT(*)
FROM tickets
GROUP BY status, source_channel
ORDER BY status, source_channel;

-- Recent escalations
SELECT id, source_channel, category, created_at
FROM tickets
WHERE status = 'escalated'
ORDER BY created_at DESC
LIMIT 20;

-- Message throughput last hour
SELECT channel, direction, COUNT(*)
FROM messages
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY channel, direction;

-- Average response latency by channel
SELECT channel, AVG(latency_ms)::int as avg_ms, MAX(latency_ms) as max_ms
FROM messages
WHERE latency_ms IS NOT NULL
  AND created_at >= NOW() - INTERVAL '1 hour'
GROUP BY channel;

-- Active DB connections
SELECT state, COUNT(*) FROM pg_stat_activity GROUP BY state;
```

### Kafka Operations

```bash
# List consumer groups
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Describe consumer group lag
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group fte-message-processor --describe

# Reset consumer group offset to earliest (use with caution — reprocesses all messages)
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group fte-message-processor --topic customer-messages \
  --reset-offsets --to-earliest --execute

# Check topic partition count and replication
kubectl -n fte-production exec -it kafka-0 -- \
  kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic customer-messages
```

### Secrets Management

```bash
# View all secrets (keys only, not values)
kubectl -n fte-production get secret fte-secrets -o yaml | grep -E "^  [a-zA-Z]"

# Decode a specific secret value
kubectl -n fte-production get secret fte-secrets \
  -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d && echo

# Update a secret value
kubectl -n fte-production patch secret fte-secrets \
  --type='json' -p='[{"op":"replace","path":"/data/OPENAI_API_KEY","value":"'$(echo -n "sk-new-key" | base64)'"}]'
```

---

## 5. Escalation Contacts

### On-Call Rotation

| Role | Responsibility | Contact Method |
|------|---------------|----------------|
| On-Call Engineer (L1) | First responder for all alerts, P3/P4 resolution | PagerDuty rotation |
| Senior Engineer (L2) | P1/P2 escalation, architecture decisions | PagerDuty escalation after 15 min |
| Engineering Lead | P1 prolonged incidents (>1 hour), customer communication | Phone/SMS |
| CTO | Data breaches, legal threats, >4 hour P1 incidents | Phone |

### External Vendor Contacts

| Vendor | Support Type | Contact |
|--------|-------------|---------|
| OpenAI | API outages, rate limit increases | `https://status.openai.com` / Enterprise support portal |
| Twilio | WhatsApp delivery failures | `https://status.twilio.com` / Support ticket |
| Google Cloud | Pub/Sub, GKE issues | GCP Support portal (must have support plan active) |
| AWS/Cloud Provider | Infrastructure | Cloud provider support portal |

### Incident Communication

- **Internal:** Post to `#incidents` Slack channel immediately upon P1/P2 declaration.
- **Customer-facing:** Update the status page within 15 minutes of P1 declaration.
- **Stakeholder update cadence:** Every 30 minutes during active P1 incident.

---

## 6. Recovery Procedures

### 6.1 Full Service Restart Sequence

Use this sequence to restart all components in the correct order to avoid race conditions:

```bash
# Step 1: Restart PostgreSQL first and wait for readiness
kubectl -n fte-production rollout restart statefulset/postgres
kubectl -n fte-production rollout status statefulset/postgres

# Step 2: Wait for PostgreSQL to accept connections
kubectl -n fte-production exec -it postgres-0 -- pg_isready -U fte_user

# Step 3: Restart Kafka
kubectl -n fte-production rollout restart statefulset/kafka
kubectl -n fte-production rollout status statefulset/kafka

# Step 4: Restart the API
kubectl -n fte-production rollout restart deployment/fte-api
kubectl -n fte-production rollout status deployment/fte-api

# Step 5: Verify API health before starting workers
curl -s http://fte-api.fte-production.svc:8000/health

# Step 6: Restart workers
kubectl -n fte-production rollout restart deployment/fte-worker
kubectl -n fte-production rollout status deployment/fte-worker

# Step 7: Verify end-to-end health
curl -s http://fte-api.fte-production.svc:8000/health | python -m json.tool
curl -s http://fte-api.fte-production.svc:8000/metrics/channels | python -m json.tool
```

### 6.2 Rollback to Previous Version

```bash
# Check rollout history
kubectl -n fte-production rollout history deployment/fte-api
kubectl -n fte-production rollout history deployment/fte-worker

# Rollback to previous version
kubectl -n fte-production rollout undo deployment/fte-api
kubectl -n fte-production rollout undo deployment/fte-worker

# Rollback to a specific revision
kubectl -n fte-production rollout undo deployment/fte-api --to-revision=3

# Verify rollback
kubectl -n fte-production rollout status deployment/fte-api
kubectl -n fte-production get pods -l component=api -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

### 6.3 Database Restore

> **WARNING:** Restoring the database will overwrite current data. Only perform during a P1 incident with Engineering Lead approval.

```bash
# List available backups (adjust path to your backup storage)
kubectl -n fte-production exec -it postgres-0 -- \
  ls -la /var/lib/postgresql/backups/

# Restore from a specific backup file
kubectl -n fte-production exec -it postgres-0 -- \
  pg_restore -U fte_user -d fte_production \
  /var/lib/postgresql/backups/fte_production_2026-04-08.dump

# Alternative: restore from a SQL dump
kubectl -n fte-production exec -it postgres-0 -- \
  psql -U fte_user -d fte_production \
  -f /var/lib/postgresql/backups/fte_production_2026-04-08.sql
```

After restoring:
1. Restart the API to clear connection pool state.
2. Verify ticket counts match expected state.
3. Communicate data recovery timeline to affected customers.

### 6.4 Emergency OpenAI Fallback

If OpenAI API is down, the agent will fail to process messages. To put the system into graceful degradation mode:

```bash
# Update the ConfigMap to enable fallback mode
kubectl -n fte-production edit configmap fte-config

# Add or update: FALLBACK_MODE=true
# This should cause the worker to return a canned "we'll get back to you" response
# and auto-escalate all tickets until FALLBACK_MODE is removed.

# Restart the worker to pick up the config change
kubectl -n fte-production rollout restart deployment/fte-worker
```

---

## 7. Post-Incident Checklist

Complete this checklist after every P1 or P2 incident is resolved.

### Immediate (within 1 hour of resolution)

- [ ] Confirm all services are healthy (`/health` returns `"status": "ok"`)
- [ ] Confirm Kafka consumer lag has returned to zero
- [ ] Confirm escalation rate has returned to normal (<10%)
- [ ] Update the internal `#incidents` Slack channel with resolution summary
- [ ] Update the customer-facing status page to "Resolved"
- [ ] Notify any customers who were directly impacted

### Short-term (within 24 hours)

- [ ] Write an internal incident timeline (what happened, when, who responded)
- [ ] Identify the root cause (not just symptoms)
- [ ] Determine if any data was lost or corrupted; if so, quantify impact
- [ ] Review alert thresholds — did the alert fire at the right time?
- [ ] Review response time — was the on-call SLA met?

### Post-Mortem (within 5 business days)

- [ ] Schedule a blameless post-mortem meeting with all responders
- [ ] Document the post-mortem in the team wiki
- [ ] Create action items with owners and due dates for:
  - [ ] Root cause fix (not workaround)
  - [ ] Monitoring/alerting improvements
  - [ ] Runbook updates (update this document if steps were unclear)
  - [ ] Process improvements
- [ ] Share the post-mortem summary with stakeholders
- [ ] Verify all action items are tracked in the project management system

### Runbook Maintenance

After each incident, update this runbook if:
- A new type of incident was encountered not covered here
- Existing steps were incorrect or unclear
- New commands or tooling were used that should be documented
- Alert thresholds were adjusted

**Runbook review schedule:** Quarterly review by the on-call team.
