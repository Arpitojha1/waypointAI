-- Waypoint Database Seed Script
-- Sample data for sanity-checking the database schema and RLS setup.
-- Can be executed via: psql $DATABASE_URL -f sql/seed.sql

BEGIN;

-- 1. Sample User Profile (using a fixed UUID representing an authenticated user)
INSERT INTO user_profiles (id, user_id, display_name, skills, experience_summary, projects, preferences)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    '00000000-0000-0000-0000-000000000001',
    'Jane Coder',
    '["Python", "FastAPI", "React", "PostgreSQL", "TypeScript"]'::jsonb,
    '2 years of full-stack web development experience building scalable APIs and interactive frontends.',
    '[{"name": "TaskFlow", "description": "Async task management dashboard"}]'::jsonb,
    '{"theme": "dark", "notifications": true}'::jsonb
) ON CONFLICT DO NOTHING;

-- 2. Sample Opportunities (one of each type: issue, job, hackathon)
INSERT INTO opportunities (id, type, title, description, url, source, metadata, repo_owner, repo_name, issue_number, company, location, deadline, is_active)
VALUES 
(
    '22222222-2222-2222-2222-222222222201',
    'issue',
    'Add async database session support to FastAPI boilerplate',
    'We need help converting our synchronous SQLAlchemy setup to use asyncpg and async sessions.',
    'https://github.com/example/fastapi-repo/issues/42',
    'github',
    '{"labels": ["good first issue", "help wanted", "python"]}'::jsonb,
    'example',
    'fastapi-repo',
    42,
    NULL,
    NULL,
    NULL,
    true
),
(
    '22222222-2222-2222-2222-222222222202',
    'job',
    'Senior Backend Engineer (Python/FastAPI)',
    'Looking for a strong backend developer skilled in Python, async programming, and cloud infrastructure.',
    'https://www.arbeitnow.com/jobs/companies/example-corp/senior-backend-engineer',
    'arbeitnow',
    '{"remote": true, "tags": ["Python", "FastAPI", "PostgreSQL"]}'::jsonb,
    NULL,
    NULL,
    NULL,
    'Example Corp',
    'Berlin, Germany / Remote',
    NULL,
    true
),
(
    '22222222-2222-2222-2222-222222222203',
    'hackathon',
    'Cognee AI Memory Hackathon 2026',
    'Build innovative autonomous agent workflows powered by Cognee memory graphs.',
    'https://cognee-2026.devpost.com/',
    'devpost',
    '{"prize_pool": "$50,000", "topics": ["AI", "Memory", "Agents"]}'::jsonb,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '2026-07-05 23:59:00+00',
    true
) ON CONFLICT DO NOTHING;

-- 3. Sample Roadmap linked to the GitHub Issue Opportunity
INSERT INTO roadmaps (id, user_id, opportunity_id, title, summary, version)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '00000000-0000-0000-0000-000000000001',
    '22222222-2222-2222-2222-222222222201',
    'Roadmap: Contribute to fastapi-repo #42',
    'Step-by-step preparation and contribution guide tailored to Jane Coder skills.',
    1
) ON CONFLICT DO NOTHING;

-- 4. Sample Steps for the Roadmap
INSERT INTO steps (id, roadmap_id, user_id, title, description, order_index, status, resource_links, is_memified)
VALUES 
(
    '44444444-4444-4444-4444-444444444401',
    '33333333-3333-3333-3333-333333333333',
    '00000000-0000-0000-0000-000000000001',
    'Fork and clone repository locally',
    'Fork https://github.com/example/fastapi-repo to your personal account and clone it.',
    0,
    'done',
    '[{"title": "GitHub Forking Guide", "url": "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo"}]'::jsonb,
    false
),
(
    '44444444-4444-4444-4444-444444444402',
    '33333333-3333-3333-3333-333333333333',
    '00000000-0000-0000-0000-000000000001',
    'Set up local async PostgreSQL test database',
    'Spin up a local docker container or postgres instance to test async SQLAlchemy connections.',
    1,
    'pending',
    '[{"title": "AsyncSQLAlchemy Docs", "url": "https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html"}]'::jsonb,
    true
) ON CONFLICT DO NOTHING;

COMMIT;
