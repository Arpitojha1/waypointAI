import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../supabase';
import { clearAuthToken } from '../api';

export interface AuthContextType {
  isAuthenticated: boolean;
  user: any | null;
  setAuth: (user: any | null) => void;
  logout: () => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  const checkLocalAuth = () => {
    try {
      const storedUser = localStorage.getItem('waypoint_user');
      if (storedUser) {
        const parsed = JSON.parse(storedUser);
        setUser(parsed);
        setIsAuthenticated(true);
        return true;
      }
    } catch (e) {
      // ignore JSON parse error
    }
    return false;
  };

  useEffect(() => {
    // 1. Check current session on load
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser(session.user);
        setIsAuthenticated(true);
        try {
          localStorage.setItem('waypoint_user', JSON.stringify(session.user));
        } catch (e) {
          // ignore
        }
      } else {
        // Fallback: check dev mode user in localStorage
        const hasLocal = checkLocalAuth();
        if (!hasLocal) {
          setUser(null);
          setIsAuthenticated(false);
        }
      }
    });

    // 2. Subscribe to Supabase auth state changes live
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setUser(session.user);
        setIsAuthenticated(true);
        try {
          localStorage.setItem('waypoint_user', JSON.stringify(session.user));
        } catch (e) {
          // ignore
        }
      } else if (event === 'SIGNED_OUT') {
        localStorage.removeItem('waypoint_user');
        clearAuthToken();
        setUser(null);
        setIsAuthenticated(false);
      } else {
        const hasLocal = checkLocalAuth();
        if (!hasLocal) {
          setUser(null);
          setIsAuthenticated(false);
        }
      }
    });

    // 3. Listen for cross-tab or custom local auth events
    const handleLocalAuthChange = () => {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session?.user) {
          setUser(session.user);
          setIsAuthenticated(true);
        } else {
          const hasLocal = checkLocalAuth();
          if (!hasLocal) {
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      });
    };

    window.addEventListener('storage', handleLocalAuthChange);
    window.addEventListener('waypoint_auth_change', handleLocalAuthChange);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener('storage', handleLocalAuthChange);
      window.removeEventListener('waypoint_auth_change', handleLocalAuthChange);
    };
  }, []);

  const setAuth = (newUser: any | null) => {
    if (newUser) {
      setUser(newUser);
      setIsAuthenticated(true);
      try {
        localStorage.setItem('waypoint_user', JSON.stringify(newUser));
      } catch (e) {
        // ignore
      }
      window.dispatchEvent(new Event('waypoint_auth_change'));
    } else {
      setUser(null);
      setIsAuthenticated(false);
      localStorage.removeItem('waypoint_user');
      clearAuthToken();
      window.dispatchEvent(new Event('waypoint_auth_change'));
    }
  };

  const signOut = async () => {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      // ignore
    }
    clearAuthToken();
    localStorage.removeItem('waypoint_user');
    setUser(null);
    setIsAuthenticated(false);
    window.dispatchEvent(new Event('waypoint_auth_change'));
  };

  const logout = signOut;

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, setAuth, logout, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
