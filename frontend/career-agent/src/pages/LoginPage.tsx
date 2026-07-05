import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { signInWithPassword } from '../supabase';
import { fetchMyProfile } from '../api';
import { useAuth } from '../context/AuthContext';
import './LoginPage.css';

export interface LoginPageProps {
  onComplete?: () => void;
  onToast?: (msg: string, isMemify?: boolean) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onComplete, onToast }) => {
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');

    if (!email.trim() || !email.includes('@')) {
      setLoginError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setLoginError('Please enter your password.');
      return;
    }

    setLoading(true);
    try {
      const res = await signInWithPassword(email.trim(), password);
      if (res.error) {
        const errLower = res.error.toLowerCase();
        if (errLower.includes('invalid login credentials') || errLower.includes('invalid credentials')) {
          setLoginError('Incorrect email or password.');
        } else if (errLower.includes('email not confirmed')) {
          setLoginError('Please confirm your email before logging in.');
        } else {
          setLoginError(res.error);
        }
        setLoading(false);
        return;
      }

      if (res.user) {
        setAuth(res.user);
      }

      // Check existing profile state separately from authentication
      let profile = null;
      try {
        profile = await fetchMyProfile();
      } catch (err: any) {
        // Thrown error indicates backend failure / network issue / 401, distinct from 404 (no profile found)
        setLoginError(`Signed in, but failed to verify your profile status: ${err.message || 'Server error'}. Please try again.`);
        setLoading(false);
        return;
      }

      if (onComplete) {
        onComplete();
      }

      if (profile) {
        if (onToast) onToast('Welcome back! Logged in successfully.');
        navigate('/dashboard');
      } else {
        if (onToast) onToast('Signed in! Please complete your onboarding profile.');
        navigate('/signup');
      }
    } catch (err: any) {
      setLoginError(err.message || 'An unexpected error occurred during login.');
      setLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">Welcome Back</h1>
          <p className="login-subtitle">
            Enter your credentials to access your career dashboard and neural roadmaps.
          </p>
        </div>

        {loginError && (
          <div className="login-error-banner" role="alert">
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '1px' }} />
            <span>{loginError}</span>
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="login-form-group">
            <label className="login-label" htmlFor="login-email">
              Email Address
            </label>
            <div className="login-input-wrapper">
              <Mail className="login-input-icon" size={18} />
              <input
                id="login-email"
                type="email"
                className="login-input"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
                autoComplete="email"
                autoFocus
              />
            </div>
          </div>

          <div className="login-form-group">
            <label className="login-label" htmlFor="login-password">
              Password
            </label>
            <div className="login-input-wrapper">
              <Lock className="login-input-icon" size={18} />
              <input
                id="login-password"
                type="password"
                className="login-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
                autoComplete="current-password"
              />
            </div>
          </div>

          <button
            type="submit"
            className="login-submit-btn"
            disabled={loading}
          >
            <span>{loading ? 'Signing In...' : 'Log In'}</span>
            {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        <div className="login-footer">
          <span>Don't have an account?</span>
          <Link to="/signup" className="login-link">
            Sign Up
          </Link>
        </div>
      </div>
    </div>
  );
};
