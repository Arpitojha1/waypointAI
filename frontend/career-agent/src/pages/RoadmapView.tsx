import React, { useState } from 'react';
import type { Roadmap, StepStatus, Opportunity } from '../types';
import { StepItem } from '../components/StepItem';
import { submitStepFeedback } from '../api';
import { ArrowLeft, Sparkles, Brain, CheckCircle2, AlertCircle } from 'lucide-react';

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
      <div className="roadmap-header">
        <button
          type="button"
          onClick={onBack}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--color-ash-gray)',
            fontFamily: 'var(--font-ui)',
            fontSize: '14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            marginBottom: '24px',
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Opportunities</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
          {opportunity && (
            <span className={`type-badge ${opportunity.type}`}>
              {opportunity.type}
            </span>
          )}
          <span className="text-meta-mono" style={{ color: 'var(--color-ash-gray)' }}>
            Roadmap ID: {roadmap.id.slice(0, 8)}...
          </span>
        </div>

        <h1 className="roadmap-title">{roadmap.title}</h1>

        {roadmap.summary && (
          <div className="roadmap-summary">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'var(--color-cream-glow)', fontWeight: 600 }}>
              <Sparkles size={16} style={{ color: 'var(--color-job-blue)' }} />
              <span>Orchestrator Strategy Summary</span>
            </div>
            <p>{roadmap.summary}</p>
          </div>
        )}

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          background: 'rgba(255, 252, 225, 0.03)',
          border: '1px solid var(--color-olive-stone)',
          borderRadius: '8px',
          marginBottom: '32px',
          flexWrap: 'wrap',
          gap: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <CheckCircle2 size={20} style={{ color: progressPercent === 100 ? 'var(--color-issue-green)' : 'var(--color-ash-gray)' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '15px' }}>Progress: {completedCount} of {sortedSteps.length} Steps Done</div>
              <div style={{ fontSize: '13px', color: 'var(--color-ash-gray)' }}>
                Mark steps done to build skills, or Reject/Skip to adapt Cognee memory.
              </div>
            </div>
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '18px',
            fontWeight: 600,
            color: progressPercent === 100 ? 'var(--color-issue-green)' : 'var(--color-cream-glow)',
          }}>
            {progressPercent}%
          </div>
        </div>

        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          background: 'rgba(157, 149, 255, 0.05)',
          border: '1px dashed var(--color-memify-violet)',
          color: 'var(--color-memify-violet)',
          fontSize: '13px',
          fontFamily: 'var(--font-mono)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '32px',
        }}>
          <Brain size={16} style={{ flexShrink: 0 }} />
          <span>
            Demo Feature: Rejecting or skipping any step automatically triggers Cognee memory feedback and adapts future step generation!
          </span>
        </div>

        {error && (
          <div style={{ padding: '12px', borderRadius: '6px', background: 'rgba(255, 92, 92, 0.1)', border: '1px solid var(--color-reject-red)', color: 'var(--color-reject-red)', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
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
