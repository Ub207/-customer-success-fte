-- Migration: 001_initial
-- Description: Initial schema for Customer Success FTE system
-- Created: 2026-03-27
-- Author: CRM Digital FTE Factory

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgvector;

-- ---------------------------------------------------------------------------
-- customers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email        VARCHAR(255) UNIQUE,
    phone        VARCHAR(50),
    name         VARCHAR(255),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata     JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers (phone);

-- ---------------------------------------------------------------------------
-- customer_identifiers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id      UUID NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    identifier_type  VARCHAR(50) NOT NULL,
    identifier_value VARCHAR(255) NOT NULL,
    verified         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_customer ON customer_identifiers (customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_identifiers_value ON customer_identifiers (identifier_value);

-- ---------------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id      UUID NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    initial_channel  VARCHAR(50) NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    status           VARCHAR(50) NOT NULL DEFAULT 'active',
    sentiment_score  FLOAT,
    resolution_type  VARCHAR(100),
    escalated_to     VARCHAR(255),
    metadata         JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations (customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations (initial_channel);

-- ---------------------------------------------------------------------------
-- messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id    UUID NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    channel            VARCHAR(50) NOT NULL,
    direction          VARCHAR(20) NOT NULL,
    role               VARCHAR(20) NOT NULL,
    content            TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tokens_used        INTEGER,
    latency_ms         INTEGER,
    tool_calls         JSONB,
    channel_message_id VARCHAR(255),
    delivery_status    VARCHAR(50) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_channel_msg_id ON messages (channel_message_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at DESC);

-- ---------------------------------------------------------------------------
-- tickets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id  UUID REFERENCES conversations (id) ON DELETE SET NULL,
    customer_id      UUID NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    source_channel   VARCHAR(50) NOT NULL,
    category         VARCHAR(100) NOT NULL DEFAULT 'general',
    priority         VARCHAR(20) NOT NULL DEFAULT 'medium',
    status           VARCHAR(50) NOT NULL DEFAULT 'open',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at      TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets (source_channel);

-- ---------------------------------------------------------------------------
-- knowledge_base
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title      VARCHAR(500) NOT NULL,
    content    TEXT NOT NULL,
    category   VARCHAR(100),
    embedding  VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
    ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- channel_configs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS channel_configs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel             VARCHAR(50) UNIQUE NOT NULL,
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    config              JSONB NOT NULL DEFAULT '{}'::JSONB,
    response_template   TEXT,
    max_response_length INTEGER NOT NULL DEFAULT 1600,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO channel_configs (channel, enabled, max_response_length, config)
VALUES
    ('email',     TRUE, 3500,  '{"sla_hours": 8,  "format": "html_allowed"}'::JSONB),
    ('whatsapp',  TRUE, 1600,  '{"preferred_length": 300, "emoji_allowed": true}'::JSONB),
    ('web_form',  TRUE, 2100,  '{"sla_hours": 4,  "attachments_allowed": true}'::JSONB)
ON CONFLICT (channel) DO NOTHING;

-- ---------------------------------------------------------------------------
-- agent_metrics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_metrics (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name  VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    channel      VARCHAR(50),
    dimensions   JSONB NOT NULL DEFAULT '{}'::JSONB,
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_name ON agent_metrics (metric_name, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_channel ON agent_metrics (channel, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_recorded ON agent_metrics (recorded_at DESC);

COMMIT;
