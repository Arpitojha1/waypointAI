import React from 'react';
import type { Opportunity } from '../types';
import { Building2, Calendar, GitPullRequest, ExternalLink, ArrowRight, Sparkles } from 'lucide-react';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onSelect: (opportunity: Opportunity) => void;
  isGenerating?: boolean;
}

export const OpportunityCard: React.FC<OpportunityCardProps> = ({
  opportunity,
  onSelect,
  isGenerating = false,
}) => {
  const { type, title, description, company, location, repo_owner, repo_name, issue_number, url, source } = opportunity;

  const renderMeta = () => {
    if (type === 'job') {
      return (
        <span className="meta-item">
          <Building2 size={14} />
          {company || source || 'Company'} {location ? `· ${location}` : ''}
        </span>
      );
    }
    if (type === 'issue') {
      return (
        <span className="meta-item">
          <GitPullRequest size={14} />
          {repo_owner && repo_name ? `${repo_owner}/${repo_name} #${issue_number || ''}` : source || 'GitHub Issue'}
        </span>
      );
    }
    return (
      <span className="meta-item">
        <Calendar size={14} />
        {source || 'Devpost Hackathon'}
      </span>
    );
  };

  return (
    <div
      className={`opportunity-card type-${type}`}
      onClick={() => !isGenerating && onSelect(opportunity)}
      role="button"
      tabIndex={0}
    >
      <div>
        <div className="card-header">
          <span className={`type-badge ${type}`}>
            {type}
          </span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ color: 'var(--color-ash-gray)', transition: 'color 0.2s' }}
              title="Open original posting"
            >
              <ExternalLink size={15} />
            </a>
          )}
        </div>

        <h3 className="card-title">{title}</h3>
        {description && <p className="card-desc">{description}</p>}
      </div>

      <div className="card-footer">
        <div className="card-meta">
          {renderMeta()}
        </div>

        <button
          type="button"
          disabled={isGenerating}
          style={{
            background: 'transparent',
            border: 'none',
            color: type === 'job' ? 'var(--color-job-blue)' : type === 'hackathon' ? 'var(--color-hackathon-orange)' : '#abff84',
            fontFamily: 'var(--font-ui)',
            fontWeight: 600,
            fontSize: '14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            cursor: isGenerating ? 'wait' : 'pointer',
          }}
        >
          {isGenerating ? (
            <>
              <div className="spinner" style={{ width: '14px', height: '14px' }} />
              <span>Orchestrating...</span>
            </>
          ) : (
            <>
              <Sparkles size={14} />
              <span>Roadmap</span>
              <ArrowRight size={14} />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
