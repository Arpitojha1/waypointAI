import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Cpu } from 'lucide-react';
import { StaggeredMenu } from './StaggeredMenu';
import { useAuth } from '../context/AuthContext';

interface NavProps {
  activeTab?: 'opportunities' | 'profile';
  onSelectTab?: (tab: 'opportunities' | 'profile') => void;
  onOpenBYOK: () => void;
  byokActive: boolean;
  byokModel?: string;
  profileSeeded?: boolean;
}

export const Nav: React.FC<NavProps> = ({
  onOpenBYOK,
  byokActive,
  byokModel,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, signOut, logout } = useAuth();

  const formatModelDisplay = (model?: string) => {
    if (!model || !model.trim()) return 'nemotron-3-super (free)';
    let name = model.trim();
    if (name.includes('/')) {
      name = name.split('/').pop() || name;
    }
    if (name.endsWith(':free')) {
      name = `${name.replace(':free', '')} (free)`;
    }
    return name;
  };

  const handleBrandClick = () => {
    if (location.pathname === '/') {
      navigate('/dashboard');
    } else {
      navigate('/');
    }
  };

  return (
    <header className="nav-bar">
      <div
        className="nav-brand"
        onClick={handleBrandClick}
        role="button"
        tabIndex={0}
        style={{ cursor: 'pointer' }}
      >
        <div className="nav-brand-logo">W</div>
        <span>Waypoint</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-16)' }}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {location.pathname !== '/profile' && (
              <button
                type="button"
                className="byok-status font-ui"
                style={{ borderColor: 'var(--color-job-blue)', color: 'var(--color-job-blue)', fontWeight: 600 }}
                onClick={() => navigate('/profile')}
              >
                <span>Profile</span>
              </button>
            )}
            <button
              type="button"
              className="byok-status font-ui"
              style={{ borderColor: 'var(--color-memify-violet)', color: 'var(--color-cream-glow)', fontWeight: 600 }}
              onClick={() => {
                if (signOut) signOut();
                else logout();
                navigate('/');
              }}
            >
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {location.pathname !== '/login' && (
              <button
                type="button"
                className="byok-status font-ui"
                style={{ borderColor: 'var(--color-memify-violet)', color: 'var(--color-cream-glow)', fontWeight: 600 }}
                onClick={() => navigate('/login')}
              >
                <span>Log In</span>
              </button>
            )}
            {location.pathname !== '/signup' && (
              <button
                type="button"
                className="byok-status font-ui"
                style={{ borderColor: 'var(--color-job-blue)', color: 'var(--color-job-blue)', fontWeight: 600 }}
                onClick={() => navigate('/signup')}
              >
                <span>Sign Up</span>
              </button>
            )}
          </div>
        )}

        <button
          type="button"
          className="byok-status"
          onClick={onOpenBYOK}
          title="Open OpenRouter / LLM Configuration"
        >
          <span className={`status-dot ${byokActive ? 'active' : 'default'}`} />
          <Cpu size={14} style={{ opacity: 0.8 }} />
          <span>LLM: {formatModelDisplay(byokModel)}</span>
        </button>

        <StaggeredMenu />
      </div>
    </header>
  );
};
