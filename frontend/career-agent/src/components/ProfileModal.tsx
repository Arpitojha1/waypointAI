import React, { useState } from 'react';
import type { UserProfile } from '../types';
import { User, X, Sparkles, Check, Info } from 'lucide-react';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile | null;
  onSaveProfile: (data: {
    display_name: string;
    skills: string[];
    experience_summary: string;
  }) => Promise<void>;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  profile,
  onSaveProfile,
}) => {
  const [name, setName] = useState(profile?.display_name || 'Alex Engineer');
  const [skillsStr, setSkillsStr] = useState(profile?.skills?.join(', ') || 'React, TypeScript, Tailwind CSS, FastAPI, Python, PostgreSQL');
  const [summary, setSummary] = useState(
    profile?.experience_summary || 'Full-stack developer with 3 years of experience building modern React web apps and Python backends. Looking to transition into senior frontend roles specializing in animations and design systems.'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const skills = skillsStr
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      await onSaveProfile({
        display_name: name.trim(),
        skills,
        experience_summary: summary.trim(),
      });
      setSaved(true);
      setTimeout(() => {
        setSaved(false);
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || 'Failed to seed profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <User size={24} style={{ color: 'var(--color-job-blue)' }} />
            <h3 className="modal-title">My Career Profile & Memory</h3>
            <span title="Seeding your profile injects skills and background into Cognee memory for roadmap generation." style={{ cursor: 'help', color: 'var(--color-ash-gray)', display: 'inline-flex' }}>
              <Info size={16} />
            </span>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div style={{ padding: '12px', borderRadius: '6px', background: 'rgba(255, 92, 92, 0.1)', border: '1px solid var(--color-reject-red)', color: 'var(--color-reject-red)', marginBottom: '16px', fontSize: '14px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Display Name</label>
            <input
              type="text"
              className="form-input font-ui"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Skills (comma-separated)</label>
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
            <label className="form-label">Experience Summary & Career Goals</label>
            <textarea
              className="form-textarea font-ui"
              rows={4}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
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
  );
};
