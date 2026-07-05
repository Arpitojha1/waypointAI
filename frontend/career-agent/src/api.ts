import type { Opportunity, OpportunityType, Roadmap, Step, StepStatus, UserProfile } from './types';
import { supabase } from './supabase';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

let authToken: string | null = localStorage.getItem('waypoint_token');

export function clearAuthToken(): void {
  authToken = null;
  localStorage.removeItem('waypoint_token');
}

export async function getAuthToken(): Promise<string> {
  try {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.access_token) {
      authToken = data.session.access_token;
      localStorage.setItem('waypoint_token', authToken);
      return authToken;
    }
  } catch (err) {
    console.warn('Could not check active Supabase session:', err);
  }

  if (authToken) return authToken;

  try {
    const res = await fetch(`${API_BASE_URL}/api/profile/token`);
    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      if (authToken) {
        localStorage.setItem('waypoint_token', authToken);
      }
      return authToken || '';
    }
  } catch (err) {
    console.warn('Could not fetch dev token from /api/profile/token:', err);
  }
  return '';
}

async function getHeaders(requireAuth = false): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (requireAuth) {
    const token = await getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  return headers;
}

export async function fetchOpportunities(typeFilter?: OpportunityType): Promise<Opportunity[]> {
  const url = typeFilter
    ? `${API_BASE_URL}/api/opportunities?type=${typeFilter}`
    : `${API_BASE_URL}/api/opportunities`;
  const res = await fetch(url, { headers: await getHeaders(false) });
  if (!res.ok) {
    throw new Error(`Failed to fetch opportunities: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchOpportunity(id: string): Promise<Opportunity> {
  const res = await fetch(`${API_BASE_URL}/api/opportunities/${id}`, { headers: await getHeaders(false) });
  if (!res.ok) {
    throw new Error(`Failed to fetch opportunity: ${res.statusText}`);
  }
  return res.json();
}

export async function createRoadmap(opportunityId: string, rememberInCognee = true, forceRegenerate = false): Promise<Roadmap> {
  const res = await fetch(`${API_BASE_URL}/api/roadmaps`, {
    method: 'POST',
    headers: await getHeaders(true),
    body: JSON.stringify({
      opportunity_id: opportunityId,
      remember_in_cognee: rememberInCognee,
      force_regenerate: forceRegenerate,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to generate roadmap: ${errorText || res.statusText}`);
  }
  return res.json();
}

export async function fetchRoadmap(id: string): Promise<Roadmap> {
  const res = await fetch(`${API_BASE_URL}/api/roadmaps/${id}`, { headers: await getHeaders(true) });
  if (!res.ok) {
    throw new Error(`Failed to load roadmap: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRoadmapByOpportunity(opportunityId: string): Promise<Roadmap | null> {
  const res = await fetch(`${API_BASE_URL}/api/roadmaps/by-opportunity/${opportunityId}`, {
    headers: await getHeaders(true),
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to check existing roadmap: ${res.statusText}`);
  }
  return res.json();
}

export async function submitStepFeedback(
  stepId: string,
  status: StepStatus,
  notes?: string
): Promise<{ step: Step; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/steps/${stepId}/feedback`, {
    method: 'POST',
    headers: await getHeaders(true),
    body: JSON.stringify({ status, notes }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to submit feedback: ${errorText || res.statusText}`);
  }
  return res.json();
}

export async function submitStepEdit(
  stepId: string,
  description: string,
  action: 'accept' | 'improve'
): Promise<{ id: string; description: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/steps/${stepId}/edit`, {
    method: 'POST',
    headers: await getHeaders(true),
    body: JSON.stringify({ description, action }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to save step edit: ${errorText || res.statusText}`);
  }
  return res.json();
}

export async function fetchMyProfile(): Promise<UserProfile | null> {
  const res = await fetch(`${API_BASE_URL}/api/profile/me`, { headers: await getHeaders(true) });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to load profile: ${res.statusText}`);
  }
  return res.json();
}

export async function seedProfile(payload: {
  display_name: string;
  skills: string[];
  experience_summary: string;
  preferences?: Record<string, any>;
}): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/api/profile/seed`, {
    method: 'POST',
    headers: await getHeaders(true),
    body: JSON.stringify({
      ...payload,
      remember_in_cognee: true,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to seed profile: ${errorText || res.statusText}`);
  }
  return res.json();
}

export interface BYOKSettings {
  byok_key?: string;
  byok_model?: string;
  byok_endpoint?: string;
}

export async function fetchBYOKSettings(): Promise<BYOKSettings> {
  const res = await fetch(`${API_BASE_URL}/api/profile/byok`, { headers: await getHeaders(true) });
  if (!res.ok) {
    return {};
  }
  return res.json();
}

export async function saveBYOKSettings(payload: BYOKSettings): Promise<BYOKSettings> {
  const res = await fetch(`${API_BASE_URL}/api/profile/byok`, {
    method: 'POST',
    headers: await getHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to save BYOK settings: ${errorText || res.statusText}`);
  }
  return res.json();
}