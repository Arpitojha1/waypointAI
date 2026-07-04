import { createClient } from '@supabase/supabase-js';
import { getAuthToken } from './api';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://your-project.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'your-supabase-anon-key';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export interface SignUpResult {
  user: any;
  session: any;
  error: string | null;
}

export async function signUpWithSupabase(email: string, password: string): Promise<SignUpResult> {
  // Check if running in dev mode without a real Supabase URL configured
  if (!import.meta.env.VITE_SUPABASE_URL || supabaseUrl.includes('your-project')) {
    console.warn('Running in Dev Mode without live VITE_SUPABASE_URL. Using dev token fallback.');
    try {
      const token = await getAuthToken();
      if (token) {
        localStorage.setItem('waypoint_token', token);
        return {
          user: { id: 'dev-user-001', email },
          session: { access_token: token },
          error: null,
        };
      }
    } catch (e) {
      // ignore and let supabase call proceed
    }
  }

  try {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    });

    if (error) {
      return { user: null, session: null, error: error.message };
    }

    if (data.session?.access_token) {
      localStorage.setItem('waypoint_token', data.session.access_token);
    } else if (!data.session && data.user) {
      // If email confirmation required or session not returned directly, fallback to dev token so local API calls work
      try {
        const token = await getAuthToken();
        if (token) {
          localStorage.setItem('waypoint_token', token);
        }
      } catch (e) {
        // ignore
      }
    }

    return { user: data.user, session: data.session, error: null };
  } catch (err: any) {
    return { user: null, session: null, error: err.message || 'Network error during signup' };
  }
}
