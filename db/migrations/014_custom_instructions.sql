-- Migration: Custom Instructions for AI Tuning
-- Allows storing user-defined prompt instructions without exposing baseline safety rules

CREATE TABLE IF NOT EXISTS custom_instructions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    instructions TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Create index for active lookup
CREATE INDEX idx_custom_instructions_active ON custom_instructions(is_active);

-- Create history table for rollback capability
CREATE TABLE IF NOT EXISTS custom_instructions_history (
    id SERIAL PRIMARY KEY,
    instruction_id INTEGER REFERENCES custom_instructions(id) ON DELETE CASCADE,
    instructions TEXT NOT NULL,
    version INTEGER NOT NULL,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for history lookup
CREATE INDEX idx_custom_instructions_history_instruction_id ON custom_instructions_history(instruction_id);

-- Insert default empty instruction set
INSERT INTO custom_instructions (name, instructions, description, is_active)
VALUES (
    'default',
    '',
    'Default empty instruction set - add your custom guidance here',
    true
)
ON CONFLICT (name) DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_custom_instructions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.version = OLD.version + 1;
    
    -- Archive old version to history
    INSERT INTO custom_instructions_history (instruction_id, instructions, version, changed_at)
    VALUES (OLD.id, OLD.instructions, OLD.version, CURRENT_TIMESTAMP);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_custom_instructions_timestamp
BEFORE UPDATE ON custom_instructions
FOR EACH ROW
EXECUTE FUNCTION update_custom_instructions_timestamp();

COMMENT ON TABLE custom_instructions IS 'User-editable prompt instructions that layer on top of baseline safety rules';
COMMENT ON COLUMN custom_instructions.instructions IS 'Custom RAG instructions - merged with baseline at runtime';
COMMENT ON COLUMN custom_instructions.is_active IS 'Only one instruction set can be active at a time';
COMMENT ON TABLE custom_instructions_history IS 'Version history for rollback capability';
