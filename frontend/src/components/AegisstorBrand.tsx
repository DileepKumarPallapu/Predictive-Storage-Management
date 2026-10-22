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
      {/* Custom Vector Shield & Multi-Tier Storage Resilience Mark */}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 relative overflow-hidden transition-all duration-200 group-hover:scale-105 shadow-md"
        style={{
          background: 'linear-gradient(135deg, #F97316 0%, #EA580C 45%, #F4B942 85%, #FF6B6B 100%)',
          boxShadow: '0 3px 12px -2px rgba(234, 88, 12, 0.45)',
        }}
      >
        {/* Ambient Sheen Overlay */}
        <div className="absolute inset-0 bg-white/10 opacity-40 pointer-events-none" />

        <svg
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-5.5 h-5.5 text-white drop-shadow-xs"
        >
          {/* Protective Outer Resilience Shield */}
          <path
            d="M14 2.8L5 6.8V12.8C5 18.2 8.8 23.4 14 24.8C19.2 23.4 23 18.2 23 12.8V6.8L14 2.8Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
            strokeOpacity="0.95"
          />
          {/* Multi-Tier Storage Stack Motif (NVMe, SSD, Capacity) */}
          <rect x="8.5" y="8" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="8.5" y="12" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />
          <rect x="8.5" y="16" width="11" height="2.2" rx="0.75" fill="currentColor" fillOpacity="0.95" />

          {/* Active Resilience Telemetry Signal Indicator Dots */}
          <circle cx="17.2" cy="9.1" r="0.7" fill="#FDE047" />
          <circle cx="17.2" cy="13.1" r="0.7" fill="#36B37E" />
          <circle cx="17.2" cy="17.1" r="0.7" fill="#F15BB5" />
        </svg>
      </div>

      {/* Balanced Typographic Wordmark & Non-Overflowing Subtitle */}
      {!collapsed && (
        <div className="flex flex-col min-w-0 justify-center">
          <div className="flex items-center gap-1.5 leading-none">
            <span
              className="font-extrabold tracking-tight text-[16px] text-[var(--text-primary)] font-display"
              style={{ letterSpacing: '-0.02em' }}
            >
              AEGISSTOR
            </span>
            <span className="text-[9px] font-bold font-mono px-1 py-0.2 rounded bg-[var(--color-ember-orange)]/15 text-[var(--color-burnt-orange)] dark:text-[#FB923C] border border-[var(--color-ember-orange)]/25">
              PRO
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
