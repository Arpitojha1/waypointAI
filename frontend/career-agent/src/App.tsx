import { useState, useEffect, useCallback, useRef } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import type { Opportunity, OpportunityType, Roadmap, UserProfile } from './types';
import type { BYOKSettings } from './api';
import { Nav } from './components/Nav';
import { Footer } from './components/Footer';
import { BYOKModal } from './components/BYOKModal';
import { Toast } from './components/Toast';
import { OpportunityList } from './pages/OpportunityList';
import { RoadmapView } from './pages/RoadmapView';
import { LandingPage } from './pages/LandingPage';
import { ProfilePage } from './pages/ProfilePage';
import { AboutPage } from './pages/AboutPage';
import { SignupPage } from './pages/SignupPage';
import { LoginPage } from './pages/LoginPage';
import { fetchOpportunities, createRoadmap, fetchRoadmapByOpportunity, fetchMyProfile, getAuthToken, fetchBYOKSettings, saveBYOKSettings } from './api';
import { useAuth } from './context/AuthContext';
import './index.css';

function AppContent() {
  const { setAuth, isAuthenticated } = useAuth();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<OpportunityType | 'all'>('all');
  const fetchingOppsRef = useRef<boolean>(false);
  
  const [selectedRoadmap, setSelectedRoadmap] = useState<Roadmap | null>(null);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const [byokOpen, setByokOpen] = useState<boolean>(false);
  const [byokSettings, setByokSettings] = useState<BYOKSettings>({});
  
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [toastMsg, setToastMsg] = useState<string>('');
  const [toastIsMemify, setToastIsMemify] = useState<boolean>(false);

  const navigate = useNavigate();
  const location = useLocation();

  const triggerToast = useCallback((msg: string, isMemify = false) => {
    setToastMsg(msg);
    setToastIsMemify(isMemify);
  }, []);

  const loadOpportunities = useCallback(async () => {
    if (fetchingOppsRef.current) return;
    fetchingOppsRef.current = true;
    setLoading(true);
    setError('');
    try {
      await getAuthToken();
      const opps = await fetchOpportunities(typeFilter === 'all' ? undefined : typeFilter);
      
      // Client-side deduplication
      const seenIds = new Set<string>();
      const seenKeys = new Set<string>();
      const uniqueOpps: Opportunity[] = [];
      for (const opp of opps) {
        if (seenIds.has(opp.id)) continue;
        const key = `${opp.type}|${(opp.url || '').toLowerCase().trim()}|${opp.title.toLowerCase().trim()}`;
        if (seenKeys.has(key)) continue;
        seenIds.add(opp.id);
        seenKeys.add(key);
        uniqueOpps.push(opp);
      }
      
      setOpportunities(uniqueOpps);
    } catch (err: any) {
      setError(err.message || 'Failed to load career opportunities');
      triggerToast(`Error loading opportunities: ${err.message}`, false);
    } finally {
      setLoading(false);
      fetchingOppsRef.current = false;
    }
  }, [typeFilter, triggerToast]);

  const loadProfile = useCallback(async () => {
    try {
      const p = await fetchMyProfile();
      setProfile(p);
      if (p) {
        setAuth(p);
      }
    } catch (err) {
      console.warn('Could not load profile:', err);
    }
  }, [setAuth]);

  const loadBYOK = useCallback(async () => {
    try {
      const settings = await fetchBYOKSettings();
      setByokSettings(settings);
    } catch (err) {
      console.warn('Could not load BYOK settings:', err);
    }
  }, []);

  useEffect(() => {
    loadOpportunities();
  }, [loadOpportunities]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile, location.pathname]); // Re-check profile when route changes (e.g. returning from ProfilePage)

  useEffect(() => {
    loadBYOK();
  }, [loadBYOK]);

  const handleSelectOpportunity = async (opp: Opportunity) => {
    setGeneratingId(opp.id);
    try {
      // Phase 1: Check for existing roadmap first (instant DB read)
      const existing = await fetchRoadmapByOpportunity(opp.id);
      if (existing) {
        setSelectedRoadmap(existing);
        setSelectedOpportunity(opp);
        triggerToast(`Loaded existing roadmap: '${existing.title}'`, false);
        return;
      }

      // No existing roadmap — generate a new one
      const modelName = byokSettings.byok_model || 'nvidia/nemotron-3-super-120b-a12b:free';
      triggerToast(`Orchestrating career roadmap with ${modelName}...`, false);
      const roadmap = await createRoadmap(opp.id, true);
      setSelectedRoadmap(roadmap);
      setSelectedOpportunity(opp);
      triggerToast(`Roadmap '${roadmap.title}' generated successfully!`, false);
    } catch (err: any) {
      triggerToast(`Generation failed: ${err.message}`, false);
      alert(`Could not generate roadmap: ${err.message}`);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleSaveBYOKSettings = async (settings: BYOKSettings) => {
    const updated = await saveBYOKSettings(settings);
    setByokSettings(updated);
    triggerToast('BYOK configuration saved to Postgres.', false);
  };

  const isLandingPage = location.pathname === '/';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {isLandingPage ? (
        <LandingPage onGetStarted={() => navigate(profile ? '/dashboard' : '/signup')} />
      ) : (
        <div className="container" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Nav
            onOpenBYOK={() => setByokOpen(true)}
            byokActive={Boolean(byokSettings.byok_key || byokSettings.byok_model || byokSettings.byok_endpoint)}
            byokModel={byokSettings.byok_model}
            profileSeeded={Boolean(profile)}
          />

          <main style={{ flexGrow: 1 }}>
            <Routes>
              <Route
                path="/dashboard"
                element={
                  selectedRoadmap ? (
                    <RoadmapView
                      roadmap={selectedRoadmap}
                      opportunity={selectedOpportunity}
                      onBack={() => {
                        setSelectedRoadmap(null);
                        setSelectedOpportunity(null);
                      }}
                      onUpdateRoadmap={(updated) => setSelectedRoadmap(updated)}
                      onToast={triggerToast}
                    />
                  ) : (
                    <OpportunityList
                      opportunities={opportunities}
                      loading={loading}
                      error={error}
                      activeFilter={typeFilter}
                      onFilterChange={(f) => setTypeFilter(f)}
                      onSelectOpportunity={handleSelectOpportunity}
                      generatingId={generatingId}
                      onRefresh={loadOpportunities}
                    />
                  )
                }
              />
              <Route
                path="/profile"
                element={<ProfilePage onBack={() => navigate('/dashboard')} />}
              />
              <Route
                path="/signup"
                element={<SignupPage onComplete={loadProfile} onToast={triggerToast} />}
              />
              <Route
                path="/login"
                element={
                  isAuthenticated && profile ? (
                    <Navigate to="/dashboard" replace />
                  ) : (
                    <LoginPage onComplete={loadProfile} onToast={triggerToast} />
                  )
                }
              />
              <Route path="/about" element={<AboutPage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>

          <Footer />
        </div>
      )}

      <BYOKModal
        isOpen={byokOpen}
        onClose={() => setByokOpen(false)}
        settings={byokSettings}
        onSaveSettings={handleSaveBYOKSettings}
      />

      <Toast
        message={toastMsg}
        isMemify={toastIsMemify}
        onClose={() => setToastMsg('')}
      />
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
