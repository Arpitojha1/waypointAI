import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { UserProfile } from '../types';
import { fetchMyProfile, seedProfile } from '../api';
import {
  User,
  Mail,
  Sparkles,
  Brain,
  Check,
  RotateCcw,
  ArrowLeft,
  Briefcase,
  Zap,
  AlertCircle,
  Terminal,
  Shield,
} from 'lucide-react';
import './ProfilePage.css';

export interface ProfilePageProps {
  onBack?: () => void;
}

const GLITCH_CHARS = '010101#@$%&*?!/<>{}[];:A-Z01X#$@%&?!*^~<>+=';

interface ScrambleTextProps {
  text: string;
  trigger: boolean;
  className?: string;
  speed?: number;
}

const ScrambleText: React.FC<ScrambleTextProps> = ({
  text,
  trigger,
  className = '',
  speed = 28,
}) => {
  const [display, setDisplay] = useState(text);
  const [isScrambling, setIsScrambling] = useState(false);

  useEffect(() => {
    if (!text) return;
    setIsScrambling(true);
    let frame = 0;
    const totalFrames = 15;
    const interval = setInterval(() => {
      frame++;
      const progress = frame / totalFrames;

      const scrambled = text
        .split('')
        .map((char, index) => {
          if (char === ' ') return ' ';
          if (progress > index / text.length) {
            return char;
          }
          return GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)];
        })
        .join('');

      setDisplay(scrambled);

      if (frame >= totalFrames) {
        clearInterval(interval);
        setDisplay(text);
        setIsScrambling(false);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, trigger, speed]);

  return (
    <span className={`${className} ${isScrambling ? 'font-mono' : ''}`} style={{ color: isScrambling ? 'var(--color-memify-violet)' : undefined }}>
      {display}
    </span>
  );
};

export const ProfilePage: React.FC<ProfilePageProps> = ({ onBack }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [name, setName] = useState('Alex Engineer');
  const [skillsStr, setSkillsStr] = useState('React, TypeScript, Tailwind CSS, FastAPI, Python, PostgreSQL');
  const [summary, setSummary] = useState(
    'Full-stack developer with 3 years of experience building modern React web apps and Python backends. Looking to transition into senior frontend roles specializing in animations and design systems.'
  );

  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isGlitching, setIsGlitching] = useState(false);

  const cardContainerRef = useRef<HTMLDivElement>(null);

  const loadProfile = useCallback(async () => {
    setFetching(true);
    try {
      const p = await fetchMyProfile();
      if (p) {
        setProfile(p);
        if (p.display_name) setName(p.display_name);
        if (p.skills && p.skills.length > 0) {
          setSkillsStr(p.skills.join(', '));
        }
        if (p.experience_summary) {
          setSummary(p.experience_summary);
        }
      }
    } catch (err) {
      console.warn('Could not load profile on standalone page:', err);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const triggerFlip = useCallback((flipToBack: boolean) => {
    setIsFlipped(flipToBack);
    setIsGlitching(true);
    setTimeout(() => setIsGlitching(false), 450);

    if (cardContainerRef.current) {
      cardContainerRef.current.style.setProperty('--tilt-x', '0deg');
      cardContainerRef.current.style.setProperty('--tilt-y', '0deg');
    }
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (isFlipped) return; // Disable tilt on back face!
      if (!cardContainerRef.current) return;
      const rect = cardContainerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -11;
      const rotateY = ((x - centerX) / centerX) * 11;

      cardContainerRef.current.style.setProperty('--tilt-x', `${rotateX.toFixed(2)}deg`);
      cardContainerRef.current.style.setProperty('--tilt-y', `${rotateY.toFixed(2)}deg`);
    },
    [isFlipped]
  );

  const handleMouseLeave = useCallback(() => {
    if (!cardContainerRef.current) return;
    cardContainerRef.current.style.setProperty('--tilt-x', '0deg');
    cardContainerRef.current.style.setProperty('--tilt-y', '0deg');
  }, []);

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else if (window.history && window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = '/';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const skills = skillsStr
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const updated = await seedProfile({
        display_name: name.trim(),
        skills,
        experience_summary: summary.trim(),
      });

      setProfile(updated);
      setSaved(true);

      setTimeout(() => {
        setSaved(false);
        triggerFlip(false);
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to seed profile into Cognee');
    } finally {
      setLoading(false);
    }
  };

  const emailDisplay = profile?.preferences?.email || 'alex@waypoint.ai';
  const displayedSkills =
    profile?.skills && profile.skills.length > 0
      ? profile.skills
      : skillsStr
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
  const initials = (profile?.display_name || name || 'A E')
    .split(' ')
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'AE';

  return (
    <div className="profile-page-container font-ui">
      <nav className="profile-page-nav">
        <button type="button" onClick={handleBack} className="profile-back-btn">
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </button>

        <div className="profile-status-pill">
          <span className={`status-dot ${profile ? '' : 'violet'}`} />
          <span>
            <ScrambleText
              text={profile ? 'COGNEE MEMORY SYNCED' : 'MEMORY CORE READY'}
              trigger={isFlipped || fetching}
            />
          </span>
        </div>
      </nav>

      <header className="profile-page-header">
        <h1 className="profile-page-title">Career Profile & Memory Core</h1>
        <p className="profile-page-subtitle">
          Your centralized identity in Waypoint AI. Hover to inspect your 3D neural card, and click to edit your skills and Cognee memory vector.
        </p>
      </header>

      <div className="profile-card-scene">
        <div
          ref={cardContainerRef}
          className={`profile-card-container ${isFlipped ? 'flipped' : ''}`}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <div className={`profile-card-3d ${isGlitching ? 'glitch-effect' : ''}`}>
            {/* ── Section 1: Front Face (Identity Card) ── */}
            <div
              className="card-face card-front"
              onClick={() => !isFlipped && triggerFlip(true)}
              onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ' ') && !isFlipped) {
                  e.preventDefault();
                  triggerFlip(true);
                }
              }}
              role="button"
              tabIndex={0}
              aria-label="Click to flip and edit profile"
              aria-expanded={isFlipped}
            >
              <div className="card-front-header">
                <div className="card-id-tag">
                  <Shield size={14} style={{ color: 'var(--color-memify-violet)' }} />
                  <span>ID #WP-AI-8942</span>
                </div>
                <div className="decryption-badge">
                  <Sparkles size={13} />
                  <span>
                    <ScrambleText
                      text={profile ? 'COGNEE VECTOR ACTIVE' : 'UNINITIALIZED'}
                      trigger={isFlipped}
                    />
                  </span>
                </div>
              </div>

              <div className="card-hero-section">
                <div className="profile-avatar-wrapper">
                  <div className="profile-avatar">{initials}</div>
                  <div className="avatar-ring" />
                </div>
                <h2 className="profile-name">
                  <ScrambleText text={profile?.display_name || name} trigger={isFlipped} />
                </h2>
                <div className="profile-email">
                  <Mail size={14} />
                  <span>
                    <ScrambleText text={emailDisplay} trigger={isFlipped} />
                  </span>
                </div>
              </div>

              <div>
                <div className="card-section-label">
                  <Terminal size={14} />
                  <span>
                    <ScrambleText text="Neural Skill Matrix" trigger={isFlipped} />
                  </span>
                </div>
                <div className="skills-showcase">
                  {displayedSkills.map((skill, idx) => (
                    <span key={idx} className="skill-tag-pill">
                      <ScrambleText text={skill} trigger={isFlipped} />
                    </span>
                  ))}
                </div>

                <div className="card-section-label">
                  <Briefcase size={14} />
                  <span>
                    <ScrambleText text="Experience Summary & Career Goals" trigger={isFlipped} />
                  </span>
                </div>
                <div className="summary-showcase">
                  <ScrambleText
                    text={profile?.experience_summary || summary}
                    trigger={isFlipped}
                  />
                </div>
              </div>

              <div className="card-flip-bar">
                <div className="flip-bar-left">
                  <RotateCcw size={16} />
                  <span>Click anywhere to flip & edit profile</span>
                </div>
                <span className="flip-bar-arrow">→</span>
              </div>
            </div>

            {/* ── Section 2: Back Face (Expanded Editable Form) ── */}
            <div className="card-face card-back" onClick={(e) => e.stopPropagation()}>
              <div className="card-back-header">
                <div className="card-back-title">
                  <User size={22} style={{ color: 'var(--color-job-blue)' }} />
                  <span>Edit Profile & Memory</span>
                </div>
                <button
                  type="button"
                  className="btn-flip-back"
                  onClick={() => triggerFlip(false)}
                >
                  <RotateCcw size={14} />
                  <span>← Flip Back to Card</span>
                </button>
              </div>

              <div className="cognee-info-box">
                <Brain size={20} style={{ color: 'var(--color-memify-violet)', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div className="cognee-title">Cognee Knowledge Graph</div>
                  <div className="cognee-desc">
                    Seeding your profile injects your skills and background into Cognee memory. When generating roadmaps, the orchestrator recalls this context to tailor milestones to your exact skill gap.
                  </div>
                </div>
              </div>

              {error && (
                <div className="error-banner">
                  <AlertCircle size={18} style={{ flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div className="form-group">
                    <label className="form-label-with-icon">
                      <User size={15} style={{ color: 'var(--color-job-blue)' }} />
                      <span>Display Name</span>
                    </label>
                    <input
                      type="text"
                      className="form-input font-ui"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Alex Engineer"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label-with-icon">
                      <Zap size={15} style={{ color: 'var(--color-memify-violet)' }} />
                      <span>Skills (comma-separated)</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="React, TypeScript, Tailwind CSS, Python..."
                      value={skillsStr}
                      onChange={(e) => setSkillsStr(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label-with-icon">
                      <Briefcase size={15} style={{ color: 'var(--color-issue-green)' }} />
                      <span>Experience Summary & Career Goals</span>
                    </label>
                    <textarea
                      className="form-textarea font-ui"
                      rows={4}
                      value={summary}
                      onChange={(e) => setSummary(e.target.value)}
                      placeholder="Describe your background and target career milestones..."
                      required
                    />
                  </div>
                </div>

                <div className="form-actions-bar">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => triggerFlip(false)}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn" disabled={loading}>
                    {loading ? (
                      <>
                        <div className="spinner" />
                        <span>Seeding Memory...</span>
                      </>
                    ) : saved ? (
                      <>
                        <Check size={16} />
                        <span>Seeded!</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={16} />
                        <span>Seed Profile in Cognee</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
