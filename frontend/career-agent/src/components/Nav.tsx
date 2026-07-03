import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Cpu } from 'lucide-react';
import { StaggeredMenu } from './StaggeredMenu';

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
