import React, { useState } from 'react';
import type { Step, StepStatus } from '../types';
import { Check, X, SkipForward, ExternalLink, Sparkles, Pencil, Brain } from 'lucide-react';
import { submitStepEdit } from '../api';

interface StepItemProps {
  step: Step;
  onFeedback: (stepId: string, status: StepStatus) => void;
  onEditSave?: (stepId: string, newDescription: string, message: string, isMemify: boolean) => void;
  isUpdating?: boolean;
}

export const StepItem: React.FC<StepItemProps> = ({
  step,
  onFeedback,
  onEditSave,
  isUpdating = false,
}) => {
  const { id, title, description, status, resource_links, cognee_memified } = step;

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(description);
  const [isSaving, setIsSaving] = useState(false);

  const handleCheckboxClick = () => {
    if (isUpdating) return;
    if (status === 'done') {
      onFeedback(id, 'pending');
    } else {
      onFeedback(id, 'done');
    }
  };

  const handleEdit = () => {
    setEditText(description);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditText(description);
  };

  const handleSaveEdit = async (action: 'accept' | 'improve') => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      const res = await submitStepEdit(id, editText, action);
      setIsEditing(false);
      if (onEditSave) {
        onEditSave(id, editText, res.message, action === 'improve');
      }
    } catch (err: any) {
      console.error('Step edit failed:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const renderCheckboxContent = () => {
    if (status === 'done') return <Check size={16} strokeWidth={3} />;
    if (status === 'rejected') return <X size={16} strokeWidth={3} />;
    if (status === 'skipped') return <SkipForward size={14} />;
    return null;
  };

  return (
    <div
      className={`step-item status-${status} ${cognee_memified ? 'memify-pulse' : ''}`}
      style={{ opacity: isUpdating ? 0.7 : 1 }}
    >
      <button
        type="button"
        className="step-checkbox"
        onClick={handleCheckboxClick}
        disabled={isUpdating}
        title={status === 'done' ? 'Mark pending' : 'Mark done'}
      >
        {renderCheckboxContent()}
      </button>

      <div className="step-content">
        <div className="step-title-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h4 className="step-title">{title}</h4>
            {cognee_memified && (
              <span className="memify-badge" title="Adapted by Cognee memory based on feedback">
                <Sparkles size={11} />
                adapted
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="text-meta-mono" style={{ opacity: 0.6 }}>
              Step #{step.order_index}
            </span>
            {!isEditing && (
              <button
                type="button"
                onClick={handleEdit}
                disabled={isUpdating}
                title="Edit step description"
                style={{
                  background: 'transparent',
                  border: '1px solid var(--color-olive-stone)',
                  borderRadius: '6px',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  color: 'var(--color-ash-gray)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                }}
              >
                <Pencil size={12} />
              </button>
            )}
          </div>
        </div>

        {isEditing ? (
          <div className="step-edit-area">
            <textarea
              className="step-edit-textarea"
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={4}
              disabled={isSaving}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--color-olive-stone)',
                background: 'rgba(255, 252, 225, 0.03)',
                color: 'var(--color-cream-glow)',
                fontFamily: 'var(--font-ui)',
                fontSize: '14px',
                lineHeight: '1.6',
                resize: 'vertical',
                outline: 'none',
              }}
            />
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button
                type="button"
                className="step-action-btn done"
                onClick={() => handleSaveEdit('accept')}
                disabled={isSaving}
                title="Save edit as-is (no memory write)"
              >
                <Check size={14} />
                <span>Accept</span>
              </button>
              <button
                type="button"
                className="step-action-btn"
                onClick={() => handleSaveEdit('improve')}
                disabled={isSaving}
                title="Save edit and feed diff to Cognee improve/memify"
                style={{ borderColor: 'var(--color-memify-violet)', color: 'var(--color-memify-violet)' }}
              >
                <Brain size={14} />
                <span>Improve</span>
              </button>
              <button
                type="button"
                className="step-action-btn"
                onClick={handleCancelEdit}
                disabled={isSaving}
                style={{ opacity: 0.6 }}
              >
                <X size={14} />
                <span>Cancel</span>
              </button>
            </div>
          </div>
        ) : (
          <p className="step-desc">{description}</p>
        )}

        {resource_links && resource_links.length > 0 && (
          <div className="step-resources">
            {resource_links.map((link, idx) => (
              <a
                key={idx}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="resource-pill"
              >
                <span>{link.title}</span>
                <ExternalLink size={12} style={{ opacity: 0.7 }} />
              </a>
            ))}
          </div>
        )}

        <div className="step-actions">
          <button
            type="button"
            className={`step-action-btn done ${status === 'done' ? 'active' : ''}`}
            onClick={() => onFeedback(id, status === 'done' ? 'pending' : 'done')}
            disabled={isUpdating}
          >
            <Check size={14} />
            <span>{status === 'done' ? 'Completed' : 'Done'}</span>
          </button>

          <button
            type="button"
            className={`step-action-btn reject ${status === 'rejected' ? 'active' : ''}`}
            onClick={() => onFeedback(id, status === 'rejected' ? 'pending' : 'rejected')}
            disabled={isUpdating}
            title="Reject step & trigger Cognee improve (negative feedback)"
          >
            <X size={14} />
            <span>{status === 'rejected' ? 'Rejected' : 'Reject & Improve'}</span>
          </button>

          <button
            type="button"
            className={`step-action-btn skip ${status === 'skipped' ? 'active' : ''}`}
            onClick={() => onFeedback(id, status === 'skipped' ? 'pending' : 'skipped')}
            disabled={isUpdating}
            title="Skip step & trigger Cognee forget"
          >
            <SkipForward size={14} />
            <span>{status === 'skipped' ? 'Skipped' : 'Skip / Forget'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
