import React, { useState, useEffect, useRef } from 'react';
import { Cpu, Info, X, Key, Check, Globe, Sliders } from 'lucide-react';
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
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setInputKey(settings.byok_key || '');
      setInputModel(settings.byok_model || '');
      setInputEndpoint(settings.byok_endpoint || '');
    }
  }, [isOpen, settings]);

  useEffect(() => {
    if (!isOpen) return;

    // Focus first focusable element when opened
    const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key === 'Tab' && modalRef.current) {
        const focusables = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;
        const firstElement = focusables[0];
        const lastElement = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

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
      <div className="modal-content" ref={modalRef} tabIndex={-1} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Cpu className="text-issue-green" size={24} style={{ color: 'var(--color-issue-green)' }} />
            <h3 className="modal-title">LLM & BYOK Configuration</h3>
            <span title="Configure your OpenRouter model, API key, and endpoint. Default: nvidia/nemotron-3-super-120b-a12b:free." style={{ cursor: 'help', color: 'var(--color-ash-gray)', display: 'inline-flex' }}>
              <Info size={16} />
            </span>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
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
