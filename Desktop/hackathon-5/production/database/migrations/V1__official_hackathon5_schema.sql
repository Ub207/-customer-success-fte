-- =============================================
-- Migration: V1__official_hackathon5_schema
-- Description: Official Hackathon 5 schema — replaces 001_initial with
--              fully-compliant column names, types, and structure.
-- Created: 2026-03-28
-- =============================================

BEGIN;

-- -------------------------------------------------------
-- Drop old tables (in dependency order) if they exist
-- -------------------------------------------------------
DROP TABLE IF EXISTS agent_metrics       CASCADE;
DROP TABLE IF EXISTS channel_configs     CASCADE;
DROP TABLE IF EXISTS knowledge_base      CASCADE;
DROP TABLE IF EXISTS tickets             CASCADE;
DROP TABLE IF EXISTS messages            CASCADE;
DROP TABLE IF EXISTS conversations       CASCADE;
DROP TABLE IF EXISTS customer_identifiers CASCADE;
DROP TABLE IF EXISTS customers           CASCADE;

-- -------------------------------------------------------
-- Extensions
-- -------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector

-- -------------------------------------------------------
-- 1. customers
-- -------------------------------------------------------
CREATE TABLE customers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE,
    phone         VARCHAR(50),
    name          VARCHAR(255),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    metadata      JSONB DEFAULT '{}'
);

-- -------------------------------------------------------
-- 2. customer_identifiers  (cross-channel matching)
-- -------------------------------------------------------
CREATE TABLE customer_identifiers (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type   VARCHAR(50) NOT NULL,   -- 'email', 'phone', 'whatsapp'
    identifier_value  VARCHAR(255) NOT NULL,
    verified          BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

-- -------------------------------------------------------
-- 3. conversations
-- -------------------------------------------------------
CREATE TABLE conversations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel   VARCHAR(50) NOT NULL,
    started_at        TIMESTAMPTZ DEFAULT NOW(),
    ended_at          TIMESTAMPTZ,
    status            VARCHAR(50) DEFAULT 'active',
    sentiment_score   DECIMAL(3,2),
    resolution_type   VARCHAR(50),
    escalated_to      VARCHAR(255),
    metadata          JSONB DEFAULT '{}'
);

-- -------------------------------------------------------
-- 4. messages
-- -------------------------------------------------------
CREATE TABLE messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID REFERENCES conversations(id) ON DELETE CASCADE,
    channel             VARCHAR(50) NOT NULL,           -- email, whatsapp, web_form
    direction           VARCHAR(20) NOT NULL,           -- inbound, outbound
    role                VARCHAR(20) NOT NULL,           -- customer, agent, system
    content             TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    tokens_used         INTEGER,
    latency_ms          INTEGER,
    tool_calls          JSONB DEFAULT '[]',
    channel_message_id  VARCHAR(255),
    delivery_status     VARCHAR(50) DEFAULT 'pending'
);

-- -------------------------------------------------------
-- 5. tickets
-- -------------------------------------------------------
CREATE TABLE tickets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id   UUID REFERENCES conversations(id),
    customer_id       UUID REFERENCES customers(id),
    source_channel    VARCHAR(50) NOT NULL,
    category          VARCHAR(100),
    priority          VARCHAR(20) DEFAULT 'medium',
    status            VARCHAR(50) DEFAULT 'open',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    resolved_at       TIMESTAMPTZ,
    resolution_notes  TEXT
);

-- -------------------------------------------------------
-- 6. knowledge_base  (pgvector semantic search)
-- -------------------------------------------------------
CREATE TABLE knowledge_base (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(500) NOT NULL,
    content     TEXT NOT NULL,
    category    VARCHAR(100),
    embedding   VECTOR(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

-- -------------------------------------------------------
-- 7. channel_configs
-- -------------------------------------------------------
CREATE TABLE channel_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(50) UNIQUE NOT NULL,
    enabled             BOOLEAN DEFAULT TRUE,
    config              JSONB NOT NULL,
    response_template   TEXT,
    max_response_length INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO channel_configs (channel, enabled, max_response_length, config) VALUES
    ('email',    TRUE, 3500, '{"sla_hours": 8,  "format": "html_allowed"}'::JSONB),
    ('whatsapp', TRUE, 1600, '{"preferred_length": 300, "emoji_allowed": true}'::JSONB),
    ('web_form', TRUE, 2100, '{"sla_hours": 4,  "attachments_allowed": true}'::JSONB)
ON CONFLICT (channel) DO NOTHING;

-- -------------------------------------------------------
-- 8. agent_metrics
-- -------------------------------------------------------
CREATE TABLE agent_metrics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name   VARCHAR(100) NOT NULL,
    metric_value  DECIMAL(10,4) NOT NULL,
    channel       VARCHAR(50),
    dimensions    JSONB DEFAULT '{}',
    recorded_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ====================== INDEXES ======================
CREATE INDEX idx_customers_email            ON customers(email);
CREATE INDEX idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX idx_conversations_customer     ON conversations(customer_id);
CREATE INDEX idx_messages_conversation      ON messages(conversation_id);
CREATE INDEX idx_messages_channel           ON messages(channel);
CREATE INDEX idx_tickets_status             ON tickets(status);
CREATE INDEX idx_tickets_channel            ON tickets(source_channel);
CREATE INDEX idx_agent_metrics_name         ON agent_metrics(metric_name, recorded_at DESC);
CREATE INDEX idx_agent_metrics_channel      ON agent_metrics(channel, recorded_at DESC);

-- pgvector semantic search index
CREATE INDEX idx_knowledge_embedding
    ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMIT;
