import { useState, useEffect, useCallback, useRef } from 'react';
import type { Opportunity, OpportunityType, Roadmap, UserProfile } from './types';
import type { BYOKSettings } from './api';
import { Nav } from './components/Nav';
import { BYOKModal } from './components/BYOKModal';
import { ProfileModal } from './components/ProfileModal';
import { Toast } from './components/Toast';
import { OpportunityList } from './pages/OpportunityList';
import { RoadmapView } from './pages/RoadmapView';
import { fetchOpportunities, createRoadmap, fetchRoadmapByOpportunity, fetchMyProfile, seedProfile, getAuthToken, fetchBYOKSettings, saveBYOKSettings } from './api';
import './index.css';

export function App() {
  const [activeTab, setActiveTab] = useState<'opportunities' | 'profile'>('opportunities');
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
  
  const [profileOpen, setProfileOpen] = useState<boolean>(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [toastMsg, setToastMsg] = useState<string>('');
  const [toastIsMemify, setToastIsMemify] = useState<boolean>(false);

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
    } catch (err) {
      console.warn('Could not load profile:', err);
    }
  }, []);

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
  }, [loadProfile]);

  useEffect(() => {
    loadBYOK();
  }, [loadBYOK]);

  const handleSelectTab = (tab: 'opportunities' | 'profile') => {
    if (tab === 'profile') {
      setProfileOpen(true);
    } else {
      setActiveTab('opportunities');
      setSelectedRoadmap(null);
      setSelectedOpportunity(null);
    }
  };

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

  const handleSaveProfile = async (data: {
    display_name: string;
    skills: string[];
    experience_summary: string;
  }) => {
    const p = await seedProfile(data);
    setProfile(p);
    triggerToast('Career profile and Cognee memory seeded successfully!', true);
  };

  return (
    <div className="container">
      <Nav
        activeTab={selectedRoadmap ? 'opportunities' : activeTab}
        onSelectTab={handleSelectTab}
        onOpenBYOK={() => setByokOpen(true)}
        byokActive={Boolean(byokSettings.byok_key || byokSettings.byok_model || byokSettings.byok_endpoint)}
        profileSeeded={Boolean(profile)}
      />

      <main>
        {selectedRoadmap ? (
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
        )}
      </main>

      <BYOKModal
        isOpen={byokOpen}
        onClose={() => setByokOpen(false)}
        settings={byokSettings}
        onSaveSettings={handleSaveBYOKSettings}
      />

      <ProfileModal
        isOpen={profileOpen}
        onClose={() => setProfileOpen(false)}
        profile={profile}
        onSaveProfile={handleSaveProfile}
      />

      <Toast
        message={toastMsg}
        isMemify={toastIsMemify}
        onClose={() => setToastMsg('')}
      />
    </div>
  );
}

export default App;
