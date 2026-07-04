import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mail,
  Lock,
  User,
  AtSign,
  Zap,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { Stepper, type StepDefinition } from '../components/Stepper';
import { signUpWithSupabase } from '../supabase';
import { seedProfile } from '../api';
import { useAuth } from '../context/AuthContext';
import './SignupPage.css';

export interface SignupPageProps {
  onComplete?: () => void;
  onToast?: (msg: string, isMemify?: boolean) => void;
}

const STEPS: StepDefinition[] = [
  { id: 'auth', title: 'Account', subtitle: 'Email & Password' },
  { id: 'identity', title: 'Identity', subtitle: 'Name & Username' },
  { id: 'skills', title: 'Skills', subtitle: 'Neural Skill Matrix' },
  { id: 'summary', title: 'Summary', subtitle: 'Career Goals' },
];

const QUICK_SKILLS = [
  'React',
  'TypeScript',
  'Python',
  'FastAPI',
  'Tailwind CSS',
  'PostgreSQL',
  'Next.js',
  'Docker',
  'GraphQL',
  'AWS',
];

export const SignupPage: React.FC<SignupPageProps> = ({ onComplete, onToast }) => {
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  // Stepper State
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Step 1: Email & Password
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [step1Loading, setStep1Loading] = useState<boolean>(false);
  const [step1Error, setStep1Error] = useState<string>('');
  const [accountCreated, setAccountCreated] = useState<boolean>(false);

  // Step 2: Name & Username
  const [fullName, setFullName] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [step2Error, setStep2Error] = useState<string>('');

  // Step 3: Skills (reusing exact ProfilePage comma-separated text input & tag pattern)
  const [skillsStr, setSkillsStr] = useState<string>('React, TypeScript, Tailwind CSS, Python');
  const [step3Error, setStep3Error] = useState<string>('');

  // Step 4: Career Summary (reusing exact ProfilePage textarea pattern)
  const [summary, setSummary] = useState<string>(
    'Full-stack developer building modern web applications and AI backends. Looking to expand into advanced agentic workflows and system architecture.'
  );
  const [step4Loading, setStep4Loading] = useState<boolean>(false);
  const [step4Error, setStep4Error] = useState<string>('');

  // ── Step 1 Handler: Create Supabase Auth Account ──
  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep1Error('');

    if (!email.trim() || !email.includes('@')) {
      setStep1Error('Please enter a valid email address.');
      return;
    }
    if (password.length < 6) {
      setStep1Error('Password must be at least 6 characters long.');
      return;
    }

    setStep1Loading(true);
    try {
      const res = await signUpWithSupabase(email.trim(), password);
      if (res.error) {
        setStep1Error(res.error);
        return;
      }
      // Account created successfully
      setAccountCreated(true);
      if (res.user) {
        setAuth(res.user);
      } else {
        setAuth({ id: 'dev-user-001', email: email.trim() });
      }
      if (onToast) onToast(`Supabase Auth account created for ${email}`, false);
      setCurrentStep(2);
    } catch (err: any) {
      setStep1Error(err.message || 'An unexpected error occurred during signup.');
    } finally {
      setStep1Loading(false);
    }
  };

  // ── Step 2 Handler: Validate Name & Username ──
  const handleStep2Next = (e: React.FormEvent) => {
    e.preventDefault();
    setStep2Error('');

    if (!fullName.trim()) {
      setStep2Error('Please enter your full display name.');
      return;
    }
    const cleanUser = username.trim();
    if (!cleanUser) {
      setStep2Error('Please choose a username.');
      return;
    }
    if (cleanUser.length < 3) {
      setStep2Error('Username must be at least 3 characters long.');
      return;
    }
    // Validate format client-side (no spaces, alphanumeric/dashes/underscores)
    const validUsernameRegex = /^[a-zA-Z0-9_-]+$/;
    if (!validUsernameRegex.test(cleanUser)) {
      setStep2Error('Username cannot contain spaces or special symbols (letters, numbers, hyphens, and underscores only).');
      return;
    }

    setCurrentStep(3);
  };

  // ── Step 3 Handler: Validate Skills ──
  const handleStep3Next = (e: React.FormEvent) => {
    e.preventDefault();
    setStep3Error('');

    const parsedSkills = skillsStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    if (parsedSkills.length === 0) {
      setStep3Error('Please add at least one technical skill.');
      return;
    }

    setCurrentStep(4);
  };

  const handleQuickAddSkill = (skill: string) => {
    const current = skillsStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (!current.includes(skill)) {
      const updated = [...current, skill].join(', ');
      setSkillsStr(updated);
      setStep3Error('');
    }
  };

  // ── Step 4 Handler: ONE Final Call to Existing seedProfile Endpoint ──
  const handleStep4Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep4Error('');

    if (!summary.trim() || summary.trim().length < 10) {
      setStep4Error('Please provide a brief career summary (at least 10 characters).');
      return;
    }

    setStep4Loading(true);
    try {
      const parsedSkills = skillsStr
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      await seedProfile({
        display_name: fullName.trim(),
        skills: parsedSkills,
        experience_summary: summary.trim(),
        preferences: {
          username: username.trim(),
          email: email.trim(),
        },
      });

      if (onToast) {
        onToast('Cognee memory vector seeded! Redirecting to dashboard...', true);
      }
      setAuth({
        id: 'dev-user-001',
        email: email.trim(),
        display_name: fullName.trim(),
        username: username.trim(),
      });
      if (onComplete) onComplete();
      navigate('/dashboard');
    } catch (err: any) {
      setStep4Error(err.message || 'Failed to submit profile update.');
    } finally {
      setStep4Loading(false);
    }
  };

  return (
    <div className="signup-page-container font-ui">
      <header className="signup-page-header">
        <h1 className="signup-page-title">Initialize Your Waypoint Identity</h1>
        <p className="signup-page-subtitle">
          Create your Supabase Auth account and configure your neural skill matrix for Cognee AI roadmap generation.
        </p>
      </header>

      <Stepper steps={STEPS} currentStep={currentStep}>
        {/* ── STEP 1: EMAIL & PASSWORD ── */}
        {currentStep === 1 && (
          <form onSubmit={handleStep1Submit} className="step-form-wrapper">
            <div>
              <div className="step-form-title">
                <ShieldCheck size={22} style={{ color: 'var(--color-job-blue)' }} />
                <span>Create Supabase Auth Account</span>
              </div>
              <p className="step-form-description">
                Your credentials are authenticated securely via Supabase. We never store plain text passwords.
              </p>
            </div>

            {step1Error && (
              <div className="step-error-banner" role="alert">
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{step1Error}</span>
              </div>
            )}

            {accountCreated ? (
              <div className="locked-account-box">
                <div className="locked-account-info">
                  <CheckCircle2 size={24} style={{ color: 'var(--color-issue-green)' }} />
                  <div>
                    <div style={{ color: 'var(--color-cream-glow)', fontWeight: 600, fontSize: '16px' }}>
                      {email}
                    </div>
                    <div style={{ color: 'var(--color-ash-gray)', fontSize: '13px', marginTop: '2px' }}>
                      Supabase Auth account created and active.
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="locked-badge">Verified & Locked</span>
                </div>
              </div>
            ) : (
              <>
                <div className="step-form-group">
                  <label htmlFor="signup-email" className="step-label">
                    <Mail size={15} style={{ color: 'var(--color-job-blue)' }} />
                    <span>Email Address</span>
                  </label>
                  <input
                    id="signup-email"
                    type="email"
                    className="step-input font-ui"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex@waypoint.ai"
                    required
                    disabled={step1Loading}
                  />
                </div>

                <div className="step-form-group">
                  <label htmlFor="signup-password" className="step-label">
                    <Lock size={15} style={{ color: 'var(--color-memify-violet)' }} />
                    <span>Password (min. 6 characters)</span>
                  </label>
                  <input
                    id="signup-password"
                    type="password"
                    className="step-input font-ui"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    minLength={6}
                    disabled={step1Loading}
                  />
                </div>
              </>
            )}

            <div className="step-actions-bar" style={{ justifyContent: 'flex-end' }}>
              {accountCreated ? (
                <button
                  type="button"
                  className="btn-step-next"
                  onClick={() => setCurrentStep(2)}
                >
                  <span>Next: Identity Setup</span>
                  <ArrowRight size={16} />
                </button>
              ) : (
                <button type="submit" className="btn-step-submit" disabled={step1Loading}>
                  {step1Loading ? (
                    <>
                      <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                      <span>Creating Account...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Account & Continue</span>
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              )}
            </div>
          </form>
        )}

        {/* ── STEP 2: NAME & USERNAME ── */}
        {currentStep === 2 && (
          <form onSubmit={handleStep2Next} className="step-form-wrapper">
            <div>
              <div className="step-form-title">
                <User size={22} style={{ color: 'var(--color-job-blue)' }} />
                <span>Personal Identity</span>
              </div>
              <p className="step-form-description">
                Collects your full display name and handle. Your username format is validated client-side and saved during profile completion.
              </p>
            </div>

            {step2Error && (
              <div className="step-error-banner" role="alert">
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{step2Error}</span>
              </div>
            )}

            <div className="step-form-group">
              <label htmlFor="signup-fullname" className="step-label">
                <User size={15} style={{ color: 'var(--color-job-blue)' }} />
                <span>Full Display Name</span>
              </label>
              <input
                id="signup-fullname"
                type="text"
                className="step-input font-ui"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alex Engineer"
                required
              />
            </div>

            <div className="step-form-group">
              <label htmlFor="signup-username" className="step-label">
                <AtSign size={15} style={{ color: 'var(--color-memify-violet)' }} />
                <span>Username (no spaces, min. 3 chars)</span>
              </label>
              <input
                id="signup-username"
                type="text"
                className="step-input font-mono"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="alex_engineer"
                required
              />
            </div>

            <div className="step-actions-bar">
              <button
                type="button"
                className="btn-step-back"
                onClick={() => setCurrentStep(1)}
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button type="submit" className="btn-step-next">
                <span>Next: Skills Matrix</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        )}

        {/* ── STEP 3: SKILLS MATRIX (Reusing exact existing skills component pattern) ── */}
        {currentStep === 3 && (
          <form onSubmit={handleStep3Next} className="step-form-wrapper">
            <div>
              <div className="step-form-title">
                <Zap size={22} style={{ color: 'var(--color-memify-violet)' }} />
                <span>Neural Skill Matrix</span>
              </div>
              <p className="step-form-description">
                Input your technical stack as comma-separated tags. Reusing the exact multi-select / tag pattern from your Profile configuration.
              </p>
            </div>

            {step3Error && (
              <div className="step-error-banner" role="alert">
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{step3Error}</span>
              </div>
            )}

            <div className="step-form-group">
              <label htmlFor="signup-skills" className="step-label">
                <Zap size={15} style={{ color: 'var(--color-memify-violet)' }} />
                <span>Skills (comma-separated)</span>
              </label>
              <input
                id="signup-skills"
                type="text"
                className="step-input"
                value={skillsStr}
                onChange={(e) => setSkillsStr(e.target.value)}
                placeholder="React, TypeScript, Tailwind CSS, Python..."
                required
              />
            </div>

            {/* Reusing exact skill tag display pattern */}
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginBottom: '6px', fontWeight: 500 }}>
                Active Tag Preview:
              </div>
              <div className="signup-skills-showcase">
                {skillsStr
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean)
                  .map((skill, idx) => (
                    <span key={idx} className="skill-tag-pill font-mono" style={{ background: 'color-mix(in srgb, var(--color-memify-violet) 18%, transparent)', color: 'var(--color-cream-glow)', border: '1px solid color-mix(in srgb, var(--color-memify-violet) 40%, transparent)', padding: '4px 12px', borderRadius: '100px', fontSize: '13px' }}>
                      {skill}
                    </span>
                  ))}
                {skillsStr.split(',').map((s) => s.trim()).filter(Boolean).length === 0 && (
                  <span style={{ fontSize: '13px', color: 'var(--color-ash-gray)', fontStyle: 'italic' }}>
                    No skills entered yet...
                  </span>
                )}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginBottom: '8px', fontWeight: 500 }}>
                Quick-Add Suggestions:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {QUICK_SKILLS.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    className="quick-skill-pill"
                    onClick={() => handleQuickAddSkill(skill)}
                  >
                    + {skill}
                  </button>
                ))}
              </div>
            </div>

            <div className="step-actions-bar">
              <button
                type="button"
                className="btn-step-back"
                onClick={() => setCurrentStep(2)}
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button type="submit" className="btn-step-next">
                <span>Next: Career Summary</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        )}

        {/* ── STEP 4: CAREER SUMMARY (Reusing exact existing summary textarea pattern) ── */}
        {currentStep === 4 && (
          <form onSubmit={handleStep4Submit} className="step-form-wrapper">
            <div>
              <div className="step-form-title">
                <Briefcase size={22} style={{ color: 'var(--color-issue-green)' }} />
                <span>Experience Summary & Career Goals</span>
              </div>
              <p className="step-form-description">
                Provide context on your engineering background and career targets. This seeds your Cognee memory vector for intelligent roadmap generation.
              </p>
            </div>

            {step4Error && (
              <div className="step-error-banner" role="alert">
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{step4Error}</span>
              </div>
            )}

            <div className="step-form-group">
              <label htmlFor="signup-summary" className="step-label">
                <Briefcase size={15} style={{ color: 'var(--color-issue-green)' }} />
                <span>Experience Summary & Goals</span>
              </label>
              <textarea
                id="signup-summary"
                className="step-textarea font-ui"
                rows={5}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Describe your background and target career milestones..."
                required
                disabled={step4Loading}
              />
            </div>

            <div className="step-info-banner">
              <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Single Atomic Submission:</strong> Clicking "Complete & Launch Dashboard" submits all accumulated profile data (Name, Username, Skills, and Summary) in one API request to the existing <code>/api/profile/seed</code> endpoint.
              </div>
            </div>

            <div className="step-actions-bar">
              <button
                type="button"
                className="btn-step-back"
                onClick={() => setCurrentStep(3)}
                disabled={step4Loading}
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button type="submit" className="btn-step-submit" disabled={step4Loading}>
                {step4Loading ? (
                  <>
                    <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                    <span>Seeding Cognee Memory...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Complete & Launch Dashboard</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </Stepper>
    </div>
  );
};

export default SignupPage;
