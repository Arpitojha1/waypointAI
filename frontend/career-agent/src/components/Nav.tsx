import React from 'react';
import { Cpu, User } from 'lucide-react';

interface NavProps {
  activeTab: 'opportunities' | 'profile';
  onSelectTab: (tab: 'opportunities' | 'profile') => void;
  onOpenBYOK: () => void;
  byokActive: boolean;
  profileSeeded: boolean;
}

export const Nav: React.FC<NavProps> = ({
  activeTab,
  onSelectTab,
  onOpenBYOK,
  byokActive,
  profileSeeded,
}) => {
  return (
    <header className="nav-bar">
      <div
        className="nav-brand"
        onClick={() => onSelectTab('opportunities')}
        role="button"
        tabIndex={0}
      >
        <div className="nav-brand-logo">W</div>
        <span>Waypoint</span>
      </div>

      <nav className="nav-pills">
        <button
          type="button"
          className={`nav-pill ${activeTab === 'opportunities' ? 'active' : ''}`}
          onClick={() => onSelectTab('opportunities')}
        >
          Opportunities
        </button>
        <button
          type="button"
          className={`nav-pill ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => onSelectTab('profile')}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <User size={15} />
            My Profile
            {!profileSeeded && (
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: 'var(--color-hackathon-orange)',
                  display: 'inline-block',
                }}
                title="Profile unseeded"
              />
            )}
          </span>
        </button>
      </nav>

      <button
        type="button"
        className="byok-status"
        onClick={onOpenBYOK}
        title="Open OpenRouter / LLM Configuration"
      >
        <span className={`status-dot ${byokActive ? 'active' : 'default'}`} />
        <Cpu size={14} style={{ opacity: 0.8 }} />
        <span>LLM: nemotron-3-super (free)</span>
      </button>
    </header>
  );
};
