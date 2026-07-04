import React, { useState } from 'react';
import type { Roadmap, StepStatus, Opportunity } from '../types';
import { StepItem } from '../components/StepItem';
import { submitStepFeedback } from '../api';
import { ArrowLeft, Sparkles, Info, CheckCircle2, AlertCircle, Brain } from 'lucide-react';


interface RoadmapViewProps {
  roadmap: Roadmap;
  opportunity: Opportunity | null;
  onBack: () => void;
  onUpdateRoadmap: (updatedRoadmap: Roadmap) => void;
  onToast: (msg: string, isMemify?: boolean) => void;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({
  roadmap,
  opportunity,
  onBack,
  onUpdateRoadmap,
  onToast,
}) => {
  const [updatingStepId, setUpdatingStepId] = useState<string | null>(null);
  const [error, setError] = useState<string>('');

  const handleStepFeedback = async (stepId: string, status: StepStatus) => {
    setUpdatingStepId(stepId);
    setError('');
    try {
      const res = await submitStepFeedback(stepId, status);
      
      const updatedSteps = roadmap.steps.map((s) => {
        if (s.id === stepId) {
          const isMemified = res.message.toLowerCase().includes('cognee') || status === 'rejected' || status === 'skipped';
          return {
            ...s,
            status,
            cognee_memified: isMemified || s.cognee_memified,
          };
        }
        return s;
      });

      const updatedRoadmap = {
        ...roadmap,
        steps: updatedSteps,
      };
      onUpdateRoadmap(updatedRoadmap);

      const isMemifyMsg = res.message.toLowerCase().includes('cognee') || res.message.toLowerCase().includes('adapt') || res.message.toLowerCase().includes('forget');
      onToast(res.message || `Step marked as ${status}`, isMemifyMsg);
    } catch (err: any) {
      setError(err.message || 'Failed to update step feedback');
      onToast(`Error: ${err.message}`, false);
    } finally {
      setUpdatingStepId(null);
    }
  };

  const handleStepEdit = (stepId: string, newDescription: string, message: string, isMemify: boolean) => {
    const updatedSteps = roadmap.steps.map((s) => {
      if (s.id === stepId) {
        return { ...s, description: newDescription };
      }
      return s;
    });
    onUpdateRoadmap({ ...roadmap, steps: updatedSteps });
    onToast(message, isMemify);
  };

  const sortedSteps = [...roadmap.steps].sort((a, b) => a.order_index - b.order_index);
  const completedCount = sortedSteps.filter((s) => s.status === 'done').length;
  const progressPercent = sortedSteps.length > 0 ? Math.round((completedCount / sortedSteps.length) * 100) : 0;

  return (
    <div className="roadmap-container">
      <div className="roadmap-header-consolidated">
        <button
          type="button"
          onClick={onBack}
          className="about-back-btn"
          style={{ marginBottom: '0' }}
        >
          <ArrowLeft size={16} />
          <span>Back to Opportunities</span>
        </button>

        <div className="roadmap-header-top">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' }}>
              {opportunity && (
                <span className={`type-badge ${opportunity.type}`}>
                  {opportunity.type}
                </span>
              )}
              <span className="text-meta-mono" style={{ color: 'var(--color-ash-gray)' }}>
                Roadmap ID: {roadmap.id.slice(0, 8)}...
              </span>
            </div>
            <h1 className="roadmap-title" style={{ margin: 0 }}>{roadmap.title}</h1>
          </div>

          <div className="roadmap-progress-card">
            <CheckCircle2 size={24} style={{ color: progressPercent === 100 ? 'var(--color-issue-green)' : 'var(--color-ash-gray)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--color-cream-glow)' }}>
                {completedCount} of {sortedSteps.length} Steps Done
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '2px' }}>
                Reject/Skip triggers Cognee graph adaptation
              </div>
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '20px',
              fontWeight: 600,
              color: progressPercent === 100 ? 'var(--color-issue-green)' : 'var(--color-cream-glow)',
              marginLeft: 'auto',
            }}>
              {progressPercent}%
            </div>
          </div>
        </div>

        {roadmap.summary && (
          <div className="roadmap-strategy-panel">
            <div className="roadmap-strategy-main">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'var(--color-cream-glow)', fontWeight: 600, fontSize: '15px' }}>
                <Sparkles size={16} style={{ color: 'var(--color-job-blue)' }} />
                <span>Roadmap Strategy</span>
                <span title="Generated by Cognee knowledge graph analysis of your profile against target requirements" style={{ cursor: 'help', color: 'var(--color-ash-gray)', display: 'inline-flex' }}>
                  <Info size={14} />
                </span>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--color-ash-gray)', lineHeight: 1.6, margin: 0 }}>
                {roadmap.summary}
              </p>
            </div>

            <div className="roadmap-strategy-aside">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--color-memify-violet)' }}>
                <Brain size={15} style={{ flexShrink: 0 }} />
                <span>Cognee Memory Active</span>
              </div>
              <div>
                Demo Feature: Rejecting or skipping any step below feeds diffs back to Cognee to dynamically adapt remaining milestones.
              </div>
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '12px', borderRadius: '6px', background: 'rgba(255, 92, 92, 0.1)', border: '1px solid var(--color-reject-red)', color: 'var(--color-reject-red)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      <div className="step-list">
        {sortedSteps.map((step) => (
          <StepItem
            key={step.id}
            step={step}
            onFeedback={handleStepFeedback}
            onEditSave={handleStepEdit}
            isUpdating={updatingStepId === step.id}
          />
        ))}
      </div>
    </div>
  );
};
