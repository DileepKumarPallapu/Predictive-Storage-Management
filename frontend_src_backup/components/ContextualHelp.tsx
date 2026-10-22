import React, { useState } from 'react';
import { HelpCircle, Info, Sparkles } from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';

interface Props {
  simpleExplanation: string;
  technicalDetails?: string;
  evidenceSource?: string;
  title?: string;
}

export const ContextualHelp: React.FC<Props> = ({
  simpleExplanation,
  technicalDetails,
  evidenceSource,
  title,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const { isExpert } = usePresentationMode();

  return (
    <div className="relative inline-flex items-center ml-1">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        className="text-[var(--text-muted)] hover:text-[var(--accent-primary)] focus:outline-none transition-colors p-0.5 rounded"
        aria-label="Contextual explanation"
      >
        <HelpCircle size={13} />
      </button>

      {isOpen && (
        <div
          role="tooltip"
          className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-72 glass-modal p-3.5 rounded-xl shadow-glass-modal text-xs animate-in fade-in zoom-in-95 duration-100 pointer-events-none"
        >
          {title && (
            <div className="font-semibold text-[var(--text-primary)] mb-1 flex items-center gap-1.5 border-b border-[var(--border-subtle)] pb-1">
              <Info size={13} className="text-[var(--accent-primary)]" />
              <span>{title}</span>
            </div>
          )}

          <p className="text-[var(--text-secondary)] leading-relaxed">
            {simpleExplanation}
          </p>

          {isExpert && technicalDetails && (
            <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] text-[11px] font-mono text-[var(--accent-secondary)]">
              <span className="font-semibold uppercase tracking-wider block text-[10px] text-[var(--text-muted)]">
                Technical Specification:
              </span>
              {technicalDetails}
            </div>
          )}

          {evidenceSource && (
            <div className="mt-1.5 text-[10px] font-mono text-[var(--text-muted)]">
              Source: <span className="text-[var(--text-secondary)]">{evidenceSource}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
