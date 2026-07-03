import React, { useState, useEffect } from 'react';
import { Cpu, ShieldCheck, X, Key, Check, Globe, Sliders } from 'lucide-react';
import type { BYOKSettings } from '../api';

interface BYOKModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: BYOKSettings;
  onSaveSettings: (settings: BYOKSettings) => Promise<void> | void;
}

export const BYOKModal: React.FC<BYOKModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSaveSettings,
}) => {
  const [inputKey, setInputKey] = useState(settings.byok_key || '');
  const [inputModel, setInputModel] = useState(settings.byok_model || '');
  const [inputEndpoint, setInputEndpoint] = useState(settings.byok_endpoint || '');
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setInputKey(settings.byok_key || '');
      setInputModel(settings.byok_model || '');
      setInputEndpoint(settings.byok_endpoint || '');
    }
  }, [isOpen, settings]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSaveSettings({
        byok_key: inputKey.trim(),
        byok_model: inputModel.trim(),
        byok_endpoint: inputEndpoint.trim(),
      });
      setSaved(true);
      setTimeout(() => {
        setSaved(false);
        setSaving(false);
        onClose();
      }, 1000);
    } catch (err) {
      setSaving(false);
      console.error('Failed to save BYOK settings:', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Cpu className="text-issue-green" size={24} style={{ color: 'var(--color-issue-green)' }} />
            <h3 className="modal-title">LLM & BYOK Configuration</h3>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div style={{
          padding: '16px',
          borderRadius: '8px',
          background: 'rgba(10, 228, 72, 0.08)',
          border: '1px solid rgba(10, 228, 72, 0.3)',
          marginBottom: '24px',
          fontSize: '14px',
          color: 'var(--color-cream-glow)',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start',
        }}>
          <ShieldCheck size={20} style={{ color: 'var(--color-issue-green)', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>Model & API Configuration</div>
            <div style={{ fontSize: '13px', opacity: 0.85, lineHeight: 1.4 }}>
              Configure your OpenRouter model, API key, and endpoint. By default, Waypoint uses <strong>nvidia/nemotron-3-super-120b-a12b:free</strong> to prevent budget errors.
            </div>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <div className="form-group">
            <label className="form-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Key size={14} />
                Custom OpenRouter API Key (Optional BYOK)
              </span>
            </label>
            <input
              type="password"
              className="form-input"
              placeholder="sk-or-v1-..."
              value={inputKey}
              onChange={(e) => setInputKey(e.target.value)}
            />
            <div className="form-helper">
              Leave blank to use server default. If provided, key is securely encrypted in Postgres via pgcrypto.
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '16px' }}>
            <label className="form-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Sliders size={14} />
                Model ID (Free text field)
              </span>
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="nvidia/nemotron-3-super-120b-a12b:free"
              value={inputModel}
              onChange={(e) => setInputModel(e.target.value)}
            />
            <div className="form-helper">
              e.g. nvidia/nemotron-3-super-120b-a12b:free or any valid OpenRouter model ID. Leave blank for default.
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '16px' }}>
            <label className="form-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Globe size={14} />
                Base Endpoint URL
              </span>
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="https://openrouter.ai/api/v1"
              value={inputEndpoint}
              onChange={(e) => setInputEndpoint(e.target.value)}
            />
            <div className="form-helper">
              Default is https://openrouter.ai/api/v1.
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saved ? (
                <>
                  <Check size={16} />
                  <span>Saved!</span>
                </>
              ) : saving ? (
                <span>Saving...</span>
              ) : (
                <span>Save Settings</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
