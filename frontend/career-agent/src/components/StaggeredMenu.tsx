import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, Sun, Moon, ArrowRight, Sparkles } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import './StaggeredMenu.css';

interface StaggeredMenuProps {
  onOpenBYOK?: () => void;
  byokActive?: boolean;
}

export const StaggeredMenu: React.FC<StaggeredMenuProps> = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated, signOut, logout } = useAuth();
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

  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    // Focus first focusable element inside panel when opened
    const focusableElements = panelRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        return;
      }
      if (e.key === 'Tab' && panelRef.current) {
        const focusables = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;
        const firstElement = focusables[0];
        const lastElement = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const menuItems = isAuthenticated
    ? [
        { label: 'Home', path: '/' },
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Profile', path: '/profile' },
        { label: 'About', path: '/about' },
        { label: 'Sign Out', path: '#signout' },
      ]
    : [
        { label: 'Home', path: '/' },
        { label: 'Log In', path: '/login' },
        { label: 'Sign Up', path: '/signup' },
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'About', path: '/about' },
      ];

  const handleNavigate = (path: string) => {
    setIsOpen(false);
    if (path === '#signout' || path === '#logout') {
      if (signOut) signOut();
      else logout();
      navigate('/');
      return;
    }
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
      <div className={`staggered-menu-panel ${isOpen ? 'open' : ''}`} ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true">
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
