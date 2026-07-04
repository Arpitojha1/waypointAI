import React from 'react';
import { Check } from 'lucide-react';
import './Stepper.css';

export interface StepDefinition {
  id: string;
  title: string;
  subtitle?: string;
}

export interface StepperProps {
  steps: StepDefinition[];
  currentStep: number; // 1-indexed (1 to steps.length)
  children: React.ReactNode;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  children,
  className = '',
}) => {
  const totalSteps = steps.length;
  // Calculate line fill percentage (e.g. step 1 -> 0%, step 2 of 4 -> 33.3%, step 4 of 4 -> 100%)
  const lineProgress = totalSteps > 1 ? ((currentStep - 1) / (totalSteps - 1)) * 100 : 0;

  return (
    <div className={`stepper-container ${className}`}>
      {/* ── Progress Pill Badge ── */}
      <div className="stepper-header">
        <div className="stepper-progress-pill font-mono">
          <span className="progress-dot" />
          <span>
            STEP {currentStep} OF {totalSteps} — {steps[currentStep - 1]?.title.toUpperCase()}
          </span>
        </div>

        {/* ── Step Indicators Track ── */}
        <div className="stepper-track">
          {/* Connecting Line Track */}
          <div className="stepper-line-container">
            <div className="stepper-line-fill" style={{ width: `${lineProgress}%` }} />
          </div>

          {/* Step Circles & Labels */}
          {steps.map((step, index) => {
            const stepNum = index + 1;
            const isCompleted = stepNum < currentStep;
            const isActive = stepNum === currentStep;
            const statusClass = isCompleted ? 'completed' : isActive ? 'active' : 'pending';

            return (
              <div key={step.id} className={`stepper-step-item ${statusClass}`}>
                <div
                  className="stepper-circle"
                  aria-label={`Step ${stepNum}: ${step.title}`}
                  aria-current={isActive ? 'step' : undefined}
                >
                  {isCompleted ? <Check size={18} strokeWidth={2.5} /> : stepNum}
                </div>
                <span className="stepper-label">{step.title}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Step Content Box ── */}
      <div className="stepper-content-box font-ui">
        <div key={currentStep} className="stepper-step-transition">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Stepper;
