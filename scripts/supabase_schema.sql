-- Supabase schema for Andrei AI Agent System memory
-- Run in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    agent VARCHAR(50) DEFAULT 'system',
    category VARCHAR(50) DEFAULT 'general',
    metadata JSONB DEFAULT '{}',
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_agent ON agent_memories(agent);
CREATE INDEX IF NOT EXISTS idx_agent_memories_category ON agent_memories(category);
CREATE INDEX IF NOT EXISTS idx_agent_memories_created ON agent_memories(created_at DESC);

-- Optional: vector similarity search function
CREATE OR REPLACE FUNCTION match_memories(
    query_embedding vector(384),
    match_count INT DEFAULT 10,
    filter_agent TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    agent VARCHAR,
    category VARCHAR,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.agent,
        m.category,
        m.metadata,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM agent_memories m
    WHERE (filter_agent IS NULL OR m.agent = filter_agent)
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Row Level Security (enable if using anon key)
ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON agent_memories
    FOR ALL
    USING (true)
    WITH CHECK (true);