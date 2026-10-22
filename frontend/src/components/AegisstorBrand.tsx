import React from 'react';

interface AegisstorBrandProps {
  collapsed?: boolean;
  className?: string;
}

export const AegisstorBrand: React.FC<AegisstorBrandProps> = ({ collapsed = false, className = '' }) => {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Custom Geometric Storage Resilience Shield & Stack Icon */}
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-sm relative overflow-hidden transition-transform duration-200 hover:scale-105"
        style={{
          background: 'linear-gradient(135deg, #7778EF 0%, #9B99E9 40%, #F0718F 80%, #E76550 100%)',
          boxShadow: '0 2px 8px -1px rgba(119, 120, 239, 0.35)',
        }}
        title="AEGISSTOR — Storage Resilience Intelligence"
      >
        <svg
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-5 h-5 text-white"
        >
          {/* Outer Protective Shield Geometry */}
          <path
            d="M14 3L5 7V13C5 18.5 8.8 23.6 14 25C19.2 23.6 23 18.5 23 13V7L14 3Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
            strokeOpacity="0.85"
          />
          {/* Layered Tiered Storage Stack Motif */}
          <rect x="9" y="8.5" width="10" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="9" y="12.5" width="10" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="9" y="16.5" width="10" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          {/* Predictive Signal Pulse Indicator */}
          <circle cx="17.2" cy="9.6" r="0.65" fill="#7778EF" />
          <circle cx="17.2" cy="13.6" r="0.65" fill="#2BAF82" />
          <circle cx="17.2" cy="17.6" r="0.65" fill="#E76550" />
        </svg>
      </div>

      {/* Primary Wordmark & Editorial Supporting Label */}
      {!collapsed && (
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-1 leading-none">
            <span className="font-extrabold tracking-tight text-[15px] font-display text-[var(--text-primary)]">
              AEGISSTOR
            </span>
          </div>
          <span className="text-[8.5px] font-mono tracking-widest text-[var(--text-muted)] font-semibold mt-1 uppercase truncate">
            STORAGE RESILIENCE INTELLIGENCE
          </span>
        </div>
      )}
    </div>
  );
};
