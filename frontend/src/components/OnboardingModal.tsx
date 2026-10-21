import React, { useState } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Database,
  Sliders,
  ShieldCheck,
  BarChart3,
  Sparkles,
  Layers,
  Compass,
  CheckCircle2
} from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  currentMode: string;
  onSelectMode: (mode: string) => void;
}

export const OnboardingModal: React.FC<Props> = ({
  isOpen,
  onClose,
  currentMode,
  onSelectMode,
}) => {
  const [step, setStep] = useState(1);
  const totalSteps = 6;

  if (!isOpen) return null;

  const nextStep = () => {
    if (step < totalSteps) setStep(step + 1);
    else onClose();
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="glass-modal max-w-xl w-full rounded-2xl overflow-hidden shadow-glass-modal animate-in fade-in zoom-in-95 duration-150 border border-[var(--border-normal)]">
        {/* Header with Step Progress */}
        <div className="px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-secondary)] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)]">
              <Sparkles size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Welcome to AEGISSTOR
              </h3>
              <p className="text-[11px] text-[var(--text-muted)] font-mono">
                Step {step} of {totalSteps} — Platform Orientation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Dots */}
            <div className="flex gap-1.5">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full transition-all ${
                    i + 1 === step
                      ? 'w-6 bg-[var(--accent-primary)] shadow-[0_0_8px_var(--accent-primary)]'
                      : i + 1 < step
                      ? 'bg-[var(--accent-primary)]/50'
                      : 'bg-[var(--border-normal)]'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={onClose}
              className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-lg transition-colors"
              title="Skip Tour"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Body Content per Step */}
        <div className="p-6 min-h-[280px] flex flex-col justify-between">
          {step === 1 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)] shadow-inner">
                <Database size={24} />
              </div>
              <h4 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Predictive Storage Capacity & Performance Management
              </h4>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                AEGISSTOR is an enterprise intelligence platform that helps storage teams anticipate capacity exhaustion, quantify uncertainty, and safely test corrective actions before physical storage runs out.
              </p>
              <div className="p-3.5 glass-panel rounded-xl text-xs text-[var(--text-secondary)] space-y-1">
                <div className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                  <CheckCircle2 size={14} className="text-[var(--status-success)]" /> Core Promise:
                </div>
                <div>We tell you when disks will fill up and what actions you can take, with zero guesswork and zero physical danger to your hardware.</div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--accent-secondary)]/20 border border-[var(--accent-secondary)]/40 flex items-center justify-center text-[var(--accent-secondary)]">
                <Sliders size={24} />
              </div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                Select Your Operating Mode
              </h4>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Choose how you would like to explore AEGISSTOR today. You can toggle this anytime in the top bar.
              </p>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => onSelectMode('demo')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    currentMode === 'demo'
                      ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/15 shadow-[0_0_12px_rgba(255,103,71,0.2)]'
                      : 'glass-panel hover:border-[var(--border-normal)]'
                  }`}
                >
                  <div className="font-bold text-xs text-[var(--text-primary)] flex items-center justify-between">
                    <span>Demo Mode</span>
                    {currentMode === 'demo' && <CheckCircle2 size={14} className="text-[var(--accent-primary)]" />}
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1.5">
                    Preloaded with realistic enterprise NVMe, SAS, and Cold tier storage pools with synthetic telemetry.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => onSelectMode('read_only')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    currentMode === 'read_only'
                      ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/15 shadow-[0_0_12px_rgba(255,103,71,0.2)]'
                      : 'glass-panel hover:border-[var(--border-normal)]'
                  }`}
                >
                  <div className="font-bold text-xs text-[var(--text-primary)] flex items-center justify-between">
                    <span>Read-Only Live</span>
                    {currentMode === 'read_only' && <CheckCircle2 size={14} className="text-[var(--accent-primary)]" />}
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1.5">
                    Connects to verified local host telemetry collector in passive monitoring mode.
                  </p>
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--status-warning)]/20 border border-[var(--status-warning)]/40 flex items-center justify-center text-[var(--status-warning)]">
                <ShieldCheck size={24} />
              </div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                Real Telemetry vs. Synthetic Data
              </h4>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                AEGISSTOR enforces complete transparency regarding data provenance.
              </p>

              <div className="space-y-2 text-xs">
                <div className="p-3 glass-panel rounded-xl flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-[var(--accent-primary)] mt-1.5 shrink-0" />
                  <div>
                    <span className="font-semibold text-[var(--text-primary)]">Synthetic Demo Data:</span>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                      Clearly labeled with badges across all charts. Generates typical enterprise diurnal cycles, burst writes, and queue spikes.
                    </p>
                  </div>
                </div>

                <div className="p-3 glass-panel rounded-xl flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-[var(--status-success)] mt-1.5 shrink-0" />
                  <div>
                    <span className="font-semibold text-[var(--text-primary)]">Zero Hardware Fabrication Rule:</span>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                      We never fabricate hardware readings. If real device telemetry drops out, the system marks intervals as missing rather than drawing deceptive fake lines.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--accent-tertiary)]/20 border border-[var(--accent-tertiary)]/40 flex items-center justify-center text-[var(--accent-tertiary)]">
                <BarChart3 size={24} />
              </div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                Understanding Forecasts & Expected Ranges
              </h4>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Storage forecasts are not single guesses—they represent calibrated probability intervals.
              </p>

              <div className="p-3.5 glass-panel rounded-xl space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between text-[var(--text-secondary)]">
                  <span>Median Estimate (q50):</span>
                  <span className="text-[var(--accent-primary)] font-bold">Most probable future trend</span>
                </div>
                <div className="flex items-center justify-between text-[var(--text-secondary)]">
                  <span>Expected Range (80% CI):</span>
                  <span className="text-[var(--accent-secondary)] font-bold">Safe operational boundary</span>
                </div>
                <div className="flex items-center justify-between text-[var(--text-secondary)]">
                  <span>Hard SLA Limit:</span>
                  <span className="text-[var(--status-critical)] font-bold">Immutable safety ceiling</span>
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--status-success)]/20 border border-[var(--status-success)]/40 flex items-center justify-center text-[var(--status-success)]">
                <Layers size={24} />
              </div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                The Safe Digital Twin Simulator
              </h4>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Before approving remediation actions—such as migrating cold data to archive or expanding LUNs—you can test them in our software Digital Twin.
              </p>

              <div className="p-3.5 glass-panel rounded-xl text-xs space-y-2">
                <div className="font-semibold text-[var(--status-success)] flex items-center gap-1.5">
                  <ShieldCheck size={15} /> Safety Guarantee:
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                  The Digital Twin is completely virtual. Simulations never alter physical disks, repartition arrays, or execute destructive host mutations.
                </p>
              </div>
            </div>
          )}

          {step === 6 && (
            <div className="space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-xl bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)]/40 flex items-center justify-center text-[var(--accent-primary)]">
                <Compass size={24} />
              </div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                Navigation & Presentation Modes
              </h4>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                The platform is grouped into 7 clear sections: <strong>Overview</strong>, <strong>Monitor</strong>, <strong>Predict</strong>, <strong>Simulate</strong>, <strong>Respond</strong>, <strong>Research</strong>, and <strong>Administration</strong>.
              </p>

              <div className="p-3.5 glass-panel rounded-xl text-xs space-y-1.5">
                <div className="font-semibold text-[var(--text-primary)]">
                  Guided Mode vs. Expert Mode
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                  By default, you are in <strong>Guided Mode</strong> with plain-language explanations. Switch to <strong>Expert Mode</strong> anytime using the toggle in the top bar to inspect raw machine-learning parameters.
                </p>
              </div>
            </div>
          )}

          {/* Footer Controls */}
          <div className="pt-4 border-t border-[var(--border-subtle)] flex items-center justify-between">
            <button
              onClick={onClose}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors px-2 py-1 font-medium"
            >
              Skip Tour
            </button>

            <div className="flex items-center gap-2">
              {step > 1 && (
                <button
                  onClick={prevStep}
                  className="btn-ember-secondary px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1"
                >
                  <ArrowLeft size={13} /> Back
                </button>
              )}

              <button
                onClick={nextStep}
                className="btn-ember-primary px-4 py-1.5 rounded-lg text-xs flex items-center gap-1 font-semibold"
              >
                {step === totalSteps ? 'Get Started' : 'Next'} <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
