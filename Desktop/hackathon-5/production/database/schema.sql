-- ================================================================
-- CRM Digital FTE Factory — Hackathon 5
-- PostgreSQL Schema
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector for semantic search

-- ----------------------------------------------------------------
-- 1. customers
--    One record per unique customer, unified across all channels.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE,
    phone       VARCHAR(50)  UNIQUE,
    name        VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    metadata    JSONB        NOT NULL DEFAULT '{}'
);

-- ----------------------------------------------------------------
-- 2. customer_identifiers
--    Maps channel-specific IDs (email, phone, WhatsApp number)
--    back to a single customers row. Enables cross-channel memory.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type   VARCHAR(50) NOT NULL,   -- 'email' | 'phone' | 'whatsapp'
    identifier_value  VARCHAR(255) NOT NULL,
    verified          BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (identifier_type, identifier_value)
);

-- ----------------------------------------------------------------
-- 3. conversations
--    One conversation thread per customer interaction session.
--    Tracks the channel it started on, sentiment, and outcome.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID         NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel  VARCHAR(50)  NOT NULL,   -- 'email' | 'whatsapp' | 'web_form'
    status           VARCHAR(50)  NOT NULL DEFAULT 'active',  -- active | resolved | escalated
    sentiment_score  DECIMAL(3,2),            -- 0.00 (negative) → 1.00 (positive)
    resolution_type  VARCHAR(50),             -- 'auto_resolved' | 'escalated' | 'abandoned'
    escalated_to     VARCHAR(255),            -- email address of human agent
    started_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    metadata         JSONB        NOT NULL DEFAULT '{}'
);

-- ----------------------------------------------------------------
-- 4. messages
--    Every inbound and outbound message in a conversation.
--    Stores token usage, latency, and tool calls for analytics.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    channel            VARCHAR(50) NOT NULL,   -- 'email' | 'whatsapp' | 'web_form'
    direction          VARCHAR(20) NOT NULL,   -- 'inbound' | 'outbound'
    role               VARCHAR(20) NOT NULL,   -- 'customer' | 'agent' | 'system'
    content            TEXT        NOT NULL,
    tokens_used        INTEGER,
    latency_ms         INTEGER,
    tool_calls         JSONB       NOT NULL DEFAULT '[]',
    channel_message_id VARCHAR(255),           -- Gmail message ID, Twilio SID, etc.
    delivery_status    VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending|sent|delivered|failed
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 5. tickets
--    Support ticket created for every inbound customer issue.
--    Linked to a conversation and a customer.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    customer_id      UUID        NOT NULL REFERENCES customers(id),
    source_channel   VARCHAR(50) NOT NULL,   -- channel the ticket came from
    category         VARCHAR(100),           -- 'billing' | 'technical' | 'account' | etc.
    priority         VARCHAR(20) NOT NULL DEFAULT 'medium',  -- low|medium|high|urgent
    status           VARCHAR(50) NOT NULL DEFAULT 'open',    -- open|in_progress|resolved|escalated
    resolution_notes TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------
-- 6. knowledge_base
--    Articles the agent searches to answer customer questions.
--    Uses pgvector for semantic (embedding-based) similarity search.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(500) NOT NULL,
    content     TEXT         NOT NULL,
    category    VARCHAR(100),
    embedding   VECTOR(1536),              -- OpenAI text-embedding-3-small dimension
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 7. channel_configs
--    Per-channel runtime configuration: enabled flag, templates,
--    response length limits, and any channel-specific settings.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS channel_configs (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(50) NOT NULL UNIQUE,  -- 'email' | 'whatsapp' | 'web_form'
    enabled             BOOLEAN     NOT NULL DEFAULT TRUE,
    config              JSONB       NOT NULL DEFAULT '{}',  -- credentials, webhook URLs, etc.
    response_template   TEXT,                               -- optional response wrapper
    max_response_length INTEGER,                            -- hard char/word limit per channel
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------
-- 8. agent_metrics
--    Time-series performance data: response latency, token usage,
--    escalation rate, sentiment scores — one row per data point.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_metrics (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name   VARCHAR(100) NOT NULL,   -- 'response_latency_ms' | 'tokens_used' | etc.
    metric_value  DECIMAL(10,4) NOT NULL,
    channel       VARCHAR(50),             -- nullable: some metrics are cross-channel
    dimensions    JSONB        NOT NULL DEFAULT '{}',  -- arbitrary key/value tags
    recorded_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ================================================================
-- INDEXES
-- ================================================================

-- customers
CREATE INDEX IF NOT EXISTS idx_customers_email
    ON customers (email);

CREATE INDEX IF NOT EXISTS idx_customers_phone
    ON customers (phone);

-- customer_identifiers
CREATE INDEX IF NOT EXISTS idx_customer_identifiers_customer
    ON customer_identifiers (customer_id);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_value
    ON customer_identifiers (identifier_value);

-- conversations
CREATE INDEX IF NOT EXISTS idx_conversations_customer
    ON conversations (customer_id);

CREATE INDEX IF NOT EXISTS idx_conversations_status
    ON conversations (status);

CREATE INDEX IF NOT EXISTS idx_conversations_channel
    ON conversations (initial_channel);

-- messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_channel
    ON messages (channel);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages (created_at);

-- tickets
CREATE INDEX IF NOT EXISTS idx_tickets_customer
    ON tickets (customer_id);

CREATE INDEX IF NOT EXISTS idx_tickets_conversation
    ON tickets (conversation_id);

CREATE INDEX IF NOT EXISTS idx_tickets_status
    ON tickets (status);

CREATE INDEX IF NOT EXISTS idx_tickets_channel
    ON tickets (source_channel);

CREATE INDEX IF NOT EXISTS idx_tickets_created_at
    ON tickets (created_at);

-- knowledge_base — IVFFlat index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
    ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- agent_metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_name
    ON agent_metrics (metric_name);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_recorded_at
    ON agent_metrics (recorded_at);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_channel
    ON agent_metrics (channel);
