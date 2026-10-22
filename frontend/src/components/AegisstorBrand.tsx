import React from 'react';

interface AegisstorBrandProps {
  collapsed?: boolean;
  className?: string;
}

export const AegisstorBrand: React.FC<AegisstorBrandProps> = ({ collapsed = false, className = '' }) => {
  return (
    <div
      className={`flex items-center gap-3 select-none transition-all duration-200 ${className}`}
      title="AEGISSTOR — Storage Resilience Intelligence Platform"
    >
      {/* Custom Vector Geometric Shield & Multi-Tier Storage Resilience Mark */}
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 relative overflow-hidden transition-all duration-200 group-hover:scale-105 shadow-sm"
        style={{
          background: 'linear-gradient(135deg, #7778EF 0%, #9B99E9 40%, #F0718F 80%, #E76550 100%)',
          boxShadow: '0 2px 8px -1px rgba(119, 120, 239, 0.35)',
        }}
      >
        <svg
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-5 h-5 text-white drop-shadow-xs"
        >
          {/* Protective Outer Resilience Shield Geometry */}
          <path
            d="M14 2.8L5 6.8V12.8C5 18.2 8.8 23.4 14 24.8C19.2 23.4 23 18.2 23 12.8V6.8L14 2.8Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
            strokeOpacity="0.95"
          />
          {/* Multi-Tier Storage Stack Motif */}
          <rect x="8.5" y="8" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="8.5" y="12" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="8.5" y="16" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />

          {/* Active Resilience Telemetry Signal Indicator Dots */}
          <circle cx="17.2" cy="9.1" r="0.7" fill="#7778EF" />
          <circle cx="17.2" cy="13.1" r="0.7" fill="#2BAF82" />
          <circle cx="17.2" cy="17.1" r="0.7" fill="#E76550" />
        </svg>
      </div>

      {/* Balanced Typographic Wordmark & Non-Overflowing Subtitle */}
      {!collapsed && (
        <div className="flex flex-col min-w-0 justify-center">
          <div className="flex items-center gap-1 leading-none">
            <span
              className="font-extrabold tracking-tight text-[15.5px] text-[var(--text-primary)] font-display"
              style={{ letterSpacing: '-0.02em' }}
            >
              AEGISSTOR
            </span>
          </div>
          <span
            className="text-[8px] font-sans font-semibold tracking-wider text-[var(--text-muted)] mt-1 uppercase whitespace-nowrap overflow-hidden text-ellipsis max-w-[145px] sm:max-w-none"
            style={{ letterSpacing: '0.07em' }}
            title="STORAGE RESILIENCE INTELLIGENCE"
          >
            Storage Resilience Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
