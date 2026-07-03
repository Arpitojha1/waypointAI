import React from 'react';
import type { Opportunity, OpportunityType } from '../types';
import { OpportunityCard } from '../components/OpportunityCard';
import { Sparkles, Briefcase, Trophy, GitPullRequest, Layers, RefreshCw } from 'lucide-react';

interface OpportunityListProps {
  opportunities: Opportunity[];
  loading: boolean;
  error: string;
  activeFilter: OpportunityType | 'all';
  onFilterChange: (filter: OpportunityType | 'all') => void;
  onSelectOpportunity: (opportunity: Opportunity) => void;
  generatingId: string | null;
  onRefresh: () => void;
}

export const OpportunityList: React.FC<OpportunityListProps> = ({
  opportunities,
  loading,
  error,
  activeFilter,
  onFilterChange,
  onSelectOpportunity,
  generatingId,
  onRefresh,
}) => {
  return (
    <div>
      <div style={{ marginBottom: '40px', textAlign: 'left' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '100px', background: 'rgba(10, 228, 72, 0.1)', border: '1px solid #0ae448', color: '#0ae448', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, marginBottom: '16px' }}>
          <Sparkles size={14} />
          <span>Powered by Cognee Memory & Nemotron Free</span>
        </div>
        <h1 className="text-page-heading" style={{ marginBottom: '12px' }}>
          Targeted Career Opportunities
        </h1>
        <p className="text-body" style={{ color: 'var(--color-ash-gray)', maxWidth: '720px' }}>
          Select any opportunity below to orchestrate a personalized, multi-step career roadmap. Waypoint analyzes the skill gap against your Cognee knowledge graph and generates actionable milestones.
        </p>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <button
            type="button"
            className={`filter-btn ${activeFilter === 'all' ? 'active-all' : ''}`}
            onClick={() => onFilterChange('all')}
          >
            <Layers size={15} />
            <span>All Opportunities</span>
            <span style={{ opacity: 0.6 }}>({opportunities.length})</span>
          </button>

          <button
            type="button"
            className={`filter-btn ${activeFilter === 'job' ? 'active-job' : ''}`}
            onClick={() => onFilterChange('job')}
          >
            <span className="filter-dot job" />
            <Briefcase size={15} />
            <span>Jobs</span>
          </button>

          <button
            type="button"
            className={`filter-btn ${activeFilter === 'hackathon' ? 'active-hackathon' : ''}`}
            onClick={() => onFilterChange('hackathon')}
          >
            <span className="filter-dot hackathon" />
            <Trophy size={15} />
            <span>Hackathons</span>
          </button>

          <button
            type="button"
            className={`filter-btn ${activeFilter === 'issue' ? 'active-issue' : ''}`}
            onClick={() => onFilterChange('issue')}
          >
            <span className="filter-dot issue" />
            <GitPullRequest size={15} />
            <span>GitHub Issues</span>
          </button>
        </div>

        <button
          type="button"
          className="btn-secondary"
          style={{ padding: '8px 16px', borderRadius: '100px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', cursor: 'pointer' }}
          onClick={onRefresh}
          disabled={loading}
          title="Refresh opportunities from Postgres"
        >
          <RefreshCw size={14} className={loading ? 'spinner' : ''} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="hairline-divider" style={{ marginTop: '16px', marginBottom: '32px' }} />

      {error && (
        <div style={{ padding: '16px', borderRadius: '8px', background: 'rgba(255, 92, 92, 0.1)', border: '1px solid var(--color-reject-red)', color: 'var(--color-reject-red)', marginBottom: '32px', textAlign: 'left' }}>
          <strong>Error loading opportunities:</strong> {error}
        </div>
      )}

      {loading && opportunities.length === 0 ? (
        <div style={{ padding: '64px', textAlign: 'center', color: 'var(--color-ash-gray)' }}>
          <div className="spinner" style={{ margin: '0 auto 16px', width: '32px', height: '32px' }} />
          <p className="font-mono">Loading real opportunities from database...</p>
        </div>
      ) : opportunities.length === 0 ? (
        <div className="empty-state">
          <p style={{ marginBottom: '12px' }}>No opportunities found matching this filter.</p>
          <button type="button" className="btn btn-secondary" onClick={() => onFilterChange('all')}>
            Show All
          </button>
        </div>
      ) : (
        <div className="opportunity-grid">
          {opportunities.map((opp) => (
            <OpportunityCard
              key={opp.id}
              opportunity={opp}
              onSelect={onSelectOpportunity}
              isGenerating={generatingId === opp.id}
            />
          ))}
        </div>
      )}
    </div>
  );
};
