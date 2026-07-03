import React, { useEffect } from 'react';
import { Sparkles, Info } from 'lucide-react';

interface ToastProps {
  message: string;
  isMemify?: boolean;
  onClose: () => void;
  duration?: number;
}

export const Toast: React.FC<ToastProps> = ({
  message,
  isMemify = false,
  onClose,
  duration = 4000,
}) => {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  return (
    <div className="toast-container">
      <div className={`toast ${isMemify ? 'memify' : ''}`}>
        {isMemify ? (
          <Sparkles size={16} style={{ color: 'var(--color-memify-violet)' }} />
        ) : (
          <Info size={16} style={{ color: 'var(--color-cream-glow)' }} />
        )}
        <span>{message}</span>
      </div>
    </div>
  );
};
