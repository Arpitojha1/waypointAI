import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, Sun, Moon, ArrowRight, Sparkles } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import './StaggeredMenu.css';

interface StaggeredMenuProps {
  onOpenBYOK?: () => void;
  byokActive?: boolean;
}

export const StaggeredMenu: React.FC<StaggeredMenuProps> = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  // Close menu on route change
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  // Prevent background scrolling when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const menuItems = [
    { label: 'Home', path: '/' },
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'My Profile', path: '/profile' },
    { label: 'About', path: '/about' },
  ];

  const handleNavigate = (path: string) => {
    setIsOpen(false);
    navigate(path);
  };

  return (
    <div className="staggered-menu-wrapper">
      {/* Theme Toggle Button in Header */}
      <button
        type="button"
        className="theme-toggle-btn"
        onClick={toggleTheme}
        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      {/* Hamburger Menu Trigger */}
      <button
        type="button"
        className={`staggered-menu-trigger ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(true)}
        aria-expanded={isOpen}
      >
        <Menu size={16} />
        <span>Menu</span>
      </button>

      {/* Backdrop Overlay */}
      <div
        className={`staggered-menu-overlay ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(false)}
      />

      {/* Slide-In Panel */}
      <div className={`staggered-menu-panel ${isOpen ? 'open' : ''}`} role="dialog" aria-modal="true">
        <div>
          <div className="menu-panel-header">
            <div className="menu-panel-brand">
              <span
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
              </span>
              <span>Waypoint AI</span>
            </div>
            <button
              type="button"
              className="menu-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close menu"
            >
              <X size={20} />
            </button>
          </div>

          <ul className="menu-items-list">
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path || 
                (item.path === '/dashboard' && location.pathname.startsWith('/dashboard'));
              return (
                <li key={item.path} className="menu-item">
                  <a
                    href={item.path}
                    className={`menu-link ${isActive ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault();
                      handleNavigate(item.path);
                    }}
                  >
                    <span>{item.label}</span>
                    <ArrowRight size={20} style={{ opacity: isActive ? 1 : 0.4 }} />
                  </a>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="menu-panel-footer">
          <div className="menu-theme-row">
            <span style={{ fontWeight: 600 }}>Color Theme</span>
            <button
              type="button"
              onClick={toggleTheme}
              style={{
                background: 'var(--color-void-black)',
                color: 'var(--color-cream-glow)',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '100px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontFamily: 'var(--font-ui)',
                fontSize: '13px',
                fontWeight: 600,
              }}
            >
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
            <Sparkles size={14} style={{ color: '#00bae2' }} />
            <span>Built for Cognee Hackathon 2026</span>
          </div>
        </div>
      </div>
    </div>
  );
};
