BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial_schema

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE opportunity_type AS ENUM ('job', 'hackathon', 'issue');

CREATE TYPE step_status AS ENUM ('pending', 'done', 'rejected', 'skipped');

CREATE TABLE user_profiles (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    display_name VARCHAR(255), 
    skills JSONB DEFAULT '[]'::jsonb, 
    experience_summary TEXT, 
    projects JSONB DEFAULT '[]'::jsonb, 
    preferences JSONB DEFAULT '{}'::jsonb, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_user_profiles_user_id ON user_profiles (user_id);

CREATE TYPE opportunity_type AS ENUM ('job', 'hackathon', 'issue');

CREATE TABLE opportunities (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    type opportunity_type NOT NULL, 
    title VARCHAR(500) NOT NULL, 
    description TEXT, 
    url VARCHAR(2048), 
    source VARCHAR(100), 
    metadata JSONB DEFAULT '{}'::jsonb, 
    repo_owner VARCHAR(255), 
    repo_name VARCHAR(255), 
    issue_number INTEGER, 
    company VARCHAR(500), 
    location VARCHAR(500), 
    deadline TIMESTAMP WITH TIME ZONE, 
    is_active BOOLEAN DEFAULT true, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_opportunities_type ON opportunities (type);

CREATE INDEX ix_opportunities_is_active ON opportunities (is_active);

CREATE TABLE roadmaps (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    opportunity_id UUID NOT NULL, 
    title VARCHAR(500) NOT NULL, 
    summary TEXT, 
    version INTEGER DEFAULT 1, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE INDEX ix_roadmaps_user_id ON roadmaps (user_id);

CREATE TYPE step_status AS ENUM ('pending', 'done', 'rejected', 'skipped');

CREATE TABLE steps (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    roadmap_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(500) NOT NULL, 
    description TEXT, 
    order_index INTEGER DEFAULT 0 NOT NULL, 
    status step_status DEFAULT 'pending', 
    resource_links JSONB DEFAULT '[]'::jsonb, 
    is_memified BOOLEAN DEFAULT false, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(roadmap_id) REFERENCES roadmaps (id) ON DELETE CASCADE
);

CREATE INDEX ix_steps_user_id ON steps (user_id);

CREATE INDEX ix_steps_roadmap_id ON steps (roadmap_id);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_profiles_select ON user_profiles
            FOR SELECT USING (user_id = auth.uid());

CREATE POLICY user_profiles_insert ON user_profiles
            FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY user_profiles_update ON user_profiles
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid());

CREATE POLICY user_profiles_delete ON user_profiles
            FOR DELETE USING (user_id = auth.uid());

ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY;

CREATE POLICY roadmaps_select ON roadmaps
            FOR SELECT USING (user_id = auth.uid());

CREATE POLICY roadmaps_insert ON roadmaps
            FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY roadmaps_update ON roadmaps
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid());

CREATE POLICY roadmaps_delete ON roadmaps
            FOR DELETE USING (user_id = auth.uid());

ALTER TABLE steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY steps_select ON steps
            FOR SELECT USING (user_id = auth.uid());

CREATE POLICY steps_insert ON steps
            FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY steps_update ON steps
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid());

CREATE POLICY steps_delete ON steps
            FOR DELETE USING (user_id = auth.uid());

INSERT INTO alembic_version (version_num) VALUES ('001_initial_schema') RETURNING alembic_version.version_num;

COMMIT;

