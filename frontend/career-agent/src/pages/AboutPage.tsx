import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, Brain, GitBranch, Layers, ShieldCheck, ArrowRight } from 'lucide-react';

export const AboutPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="about-container">
      <button
        type="button"
        onClick={() => navigate('/dashboard')}
        className="about-back-btn"
      >
        <ArrowLeft size={16} />
        <span>Back to Dashboard</span>
      </button>

      <div className="about-header">
        <div className="about-badge">
          <Brain size={14} />
          <span>Cognee Hackathon 2026 Submission</span>
        </div>

        <h1 className="text-page-heading" style={{ marginBottom: '16px', color: 'var(--color-cream-glow)' }}>
          About Waypoint AI
        </h1>

        <p className="text-body" style={{ color: 'var(--color-ash-gray)', lineHeight: 1.6, fontSize: '18px', maxWidth: '800px' }}>
          Waypoint is an AI career opportunity agent built to bridge the gap between ambitious engineers and high-impact opportunities. By combining real-time ingestion of jobs, hackathons, and open-source issues with Cognee's dynamic knowledge graph memory, Waypoint generates step-by-step roadmaps tailored to your unique skill gap.
        </p>
      </div>

      <div className="about-bento-grid">
        {/* Hero Bento Card (Spans across top) */}
        <div className="bento-card hero-span">
          <div className="bento-card-header" style={{ color: 'var(--color-memify-violet)' }}>
            <Brain size={26} />
            <h3 className="bento-card-title">Cognee Memory Graph & Adaptive Intelligence</h3>
          </div>
          <p className="bento-card-desc" style={{ maxWidth: '780px' }}>
            Unlike static generators that forget your context, Waypoint leverages Cognee's full graph memory lifecycle to continuously steer and adapt milestone order as you interact with steps.
          </p>

          <div className="bento-memory-flow">
            <span style={{ color: 'var(--color-ash-gray)' }}>Lifecycle:</span>
            <span className="bento-step-pill">1. remember(profile)</span>
            <ArrowRight size={14} className="bento-arrow" />
            <span className="bento-step-pill">2. recall(context)</span>
            <ArrowRight size={14} className="bento-arrow" />
            <span className="bento-step-pill" style={{ background: 'var(--color-memify-violet)', color: 'var(--color-void-black)' }}>3. improve / memify(feedback)</span>
            <ArrowRight size={14} className="bento-arrow" />
            <span className="bento-step-pill">4. forget(skipped)</span>
          </div>
        </div>

        {/* Secondary Card 1 */}
        <div className="bento-card">
          <div className="bento-card-header" style={{ color: 'var(--color-job-blue)' }}>
            <Layers size={22} />
            <h3 className="bento-card-title">Multi-Source Ingestion</h3>
          </div>
          <p className="bento-card-desc">
            Ingests real-world opportunities from Arbeitnow (jobs), Devpost (hackathons), and GitHub (good first issues) into a unified, clean schema ready for AI orchestration.
          </p>
        </div>

        {/* Secondary Card 2 */}
        <div className="bento-card">
          <div className="bento-card-header" style={{ color: '#0ae448' }}>
            <Sparkles size={22} />
            <h3 className="bento-card-title">Anthropic Tool-Use Loop</h3>
          </div>
          <p className="bento-card-desc">
            Powered by a lightweight, hand-written orchestrator and role-scoped system prompts executing direct tool calls without heavy framework abstraction bloat.
          </p>
        </div>

        {/* Secondary Card 3 */}
        <div className="bento-card" style={{ gridColumn: '1 / -1' }}>
          <div className="bento-card-header" style={{ color: 'var(--color-hackathon-orange)' }}>
            <ShieldCheck size={22} />
            <h3 className="bento-card-title">BYOK & RLS Postgres Security</h3>
          </div>
          <p className="bento-card-desc">
            Bring Your Own Key (OpenRouter/Nemotron free tier supported) encrypted in Postgres via pgcrypto, protected by strict Supabase Row-Level Security policies.
          </p>
        </div>
      </div>

      <div className="about-source-bar">
        <div>
          <h4 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)', marginBottom: '6px' }}>
            Explore the Source Code
          </h4>
          <p style={{ fontSize: '14px', color: 'var(--color-ash-gray)' }}>
            Built with FastAPI, SQLAlchemy Async, Cognee, React 19, and Vite 8.
          </p>
        </div>
        <a
          href="https://github.com/Arpitojha1/waypointAI"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: '100px',
            background: 'var(--color-cream-glow)',
            color: 'var(--color-void-black)',
            fontWeight: 600,
            fontSize: '14px',
            textDecoration: 'none',
            transition: 'opacity 0.2s ease',
          }}
        >
          <GitBranch size={18} />
          <span>GitHub Repository</span>
        </a>
      </div>
    </div>
  );
};

