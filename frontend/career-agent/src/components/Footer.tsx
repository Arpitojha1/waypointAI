import React from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Heart, Sparkles } from 'lucide-react';
import { ScrambledText } from './ScrambledText';
import './Footer.css';

export const Footer: React.FC = () => {
  const navigate = useNavigate();

  return (
    <footer className="app-footer">
      <div className="container">
        <div className="footer-content">
          <div className="footer-brand-section">
            <div
              className="footer-brand-title"
              onClick={() => navigate('/')}
              role="button"
              tabIndex={0}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '100px',
                  background: 'var(--gradient-issue-green)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#0e100f',
                  fontWeight: 700,
                  fontSize: '13px',
                }}
              >
                W
              </div>
              <ScrambledText text="WAYPOINT AI" style={{ fontWeight: 800, letterSpacing: '-0.02em' }} />
            </div>
            <p className="footer-brand-desc">
              An autonomous career opportunity agent that ingests real-world listings and adapts step-by-step roadmaps using Cognee's dynamic knowledge graph memory.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#0ae448', fontSize: '13px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              <Sparkles size={14} />
              <span>Cognee Hackathon 2026 Submission</span>
            </div>
          </div>

          <div className="footer-links-section">
            <div className="footer-links-col">
              <span className="footer-col-title">Navigation</span>
              <a href="/" className="footer-link" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
                Home
              </a>
              <a href="/dashboard" className="footer-link" onClick={(e) => { e.preventDefault(); navigate('/dashboard'); }}>
                Dashboard
              </a>
              <a href="/profile" className="footer-link" onClick={(e) => { e.preventDefault(); navigate('/profile'); }}>
                My Profile
              </a>
              <a href="/about" className="footer-link" onClick={(e) => { e.preventDefault(); navigate('/about'); }}>
                About Waypoint
              </a>
            </div>

            <div className="footer-links-col">
              <span className="footer-col-title">Opportunity Sources</span>
              <a href="https://www.arbeitnow.com" target="_blank" rel="noopener noreferrer" className="footer-link">
                Arbeitnow (Jobs)
              </a>
              <a href="https://devpost.com" target="_blank" rel="noopener noreferrer" className="footer-link">
                Devpost (Hackathons)
              </a>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="footer-link">
                GitHub (Good First Issues)
              </a>
            </div>

            <div className="footer-links-col">
              <span className="footer-col-title">Technology</span>
              <a href="https://github.com/cognee-ai/cognee" target="_blank" rel="noopener noreferrer" className="footer-link">
                Cognee Memory SDK
              </a>
              <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer" className="footer-link">
                OpenRouter / Nemotron Free
              </a>
              <a href="https://supabase.com" target="_blank" rel="noopener noreferrer" className="footer-link">
                Supabase & Postgres
              </a>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <div>
            © 2026 Waypoint AI. All rights reserved.
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              Built with <Heart size={13} style={{ color: 'var(--color-reject-red)' }} /> for Cognee
            </span>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--color-cream-glow)', display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
            >
              <GitBranch size={15} />
              <span>Source</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};
