import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, Brain, GitBranch, Layers, ShieldCheck } from 'lucide-react';

export const AboutPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '64px', textAlign: 'left' }}>
      <button
        type="button"
        onClick={() => navigate('/dashboard')}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--color-ash-gray)',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          fontFamily: 'var(--font-ui)',
          fontSize: '14px',
          cursor: 'pointer',
          marginBottom: '32px',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} />
        <span>Back to Dashboard</span>
      </button>

      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '100px', background: 'rgba(157, 149, 255, 0.1)', border: '1px solid var(--color-memify-violet)', color: 'var(--color-memify-violet)', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, marginBottom: '16px' }}>
        <Brain size={14} />
        <span>Cognee Hackathon 2026 Submission</span>
      </div>

      <h1 className="text-page-heading" style={{ marginBottom: '16px', color: 'var(--color-cream-glow)' }}>
        About Waypoint AI
      </h1>

      <p className="text-body" style={{ color: 'var(--color-ash-gray)', lineHeight: 1.6, marginBottom: '40px', fontSize: '18px' }}>
        Waypoint is an AI career opportunity agent built to bridge the gap between ambitious engineers and high-impact opportunities. By combining real-time ingestion of jobs, hackathons, and open-source issues with Cognee's dynamic knowledge graph memory, Waypoint generates step-by-step roadmaps tailored to your unique skill gap.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '48px' }}>
        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-card)',
          background: 'var(--color-void-black)',
          border: '1px solid var(--color-olive-stone)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--color-job-blue)' }}>
            <Layers size={22} />
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)' }}>Multi-Source Ingestion</h3>
          </div>
          <p style={{ fontSize: '15px', color: 'var(--color-ash-gray)', lineHeight: 1.5 }}>
            Ingests real-world opportunities from Arbeitnow (jobs), Devpost (hackathons), and GitHub (good first issues) into a unified, clean schema.
          </p>
        </div>

        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-card)',
          background: 'var(--color-void-black)',
          border: '1px solid var(--color-olive-stone)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--color-memify-violet)' }}>
            <Brain size={22} />
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)' }}>Cognee Memory Graph</h3>
          </div>
          <p style={{ fontSize: '15px', color: 'var(--color-ash-gray)', lineHeight: 1.5 }}>
            Uses Cognee's full memory lifecycle (`remember`, `recall`, `improve`/`memify`, `forget`) to continuously adapt milestone order as you complete tasks.
          </p>
        </div>

        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-card)',
          background: 'var(--color-void-black)',
          border: '1px solid var(--color-olive-stone)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: '#0ae448' }}>
            <Sparkles size={22} />
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)' }}>Anthropic Tool-Use Loop</h3>
          </div>
          <p style={{ fontSize: '15px', color: 'var(--color-ash-gray)', lineHeight: 1.5 }}>
            Powered by a hand-written orchestrator and role-scoped system prompts executing direct tool calls without heavy framework bloat.
          </p>
        </div>

        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-card)',
          background: 'var(--color-void-black)',
          border: '1px solid var(--color-olive-stone)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--color-hackathon-orange)' }}>
            <ShieldCheck size={22} />
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)' }}>BYOK & RLS Security</h3>
          </div>
          <p style={{ fontSize: '15px', color: 'var(--color-ash-gray)', lineHeight: 1.5 }}>
            Bring Your Own Key (OpenRouter/Nemotron free tier supported) encrypted in Postgres via pgcrypto, protected by Row-Level Security.
          </p>
        </div>
      </div>

      <div style={{
        padding: '32px',
        borderRadius: 'var(--radius-card)',
        background: 'rgba(255, 252, 225, 0.03)',
        border: '1px solid var(--color-olive-stone)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px',
      }}>
        <div>
          <h4 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-cream-glow)', marginBottom: '6px' }}>
            Explore the Source Code
          </h4>
          <p style={{ fontSize: '14px', color: 'var(--color-ash-gray)' }}>
            Built with FastAPI, SQLAlchemy Async, Cognee, React 19, and Vite.
          </p>
        </div>
        <a
          href="https://github.com"
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
          }}
        >
          <GitBranch size={18} />
          <span>GitHub Repository</span>
        </a>
      </div>
    </div>
  );
};
