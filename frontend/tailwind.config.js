/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ember: {
          bgPrimary: 'var(--bg-primary)',
          bgSecondary: 'var(--bg-secondary)',
          bgTertiary: 'var(--bg-tertiary)',
          surfacePrimary: 'var(--surface-primary)',
          surfaceSecondary: 'var(--surface-secondary)',
          surfaceElevated: 'var(--surface-elevated)',
          textPrimary: 'var(--text-primary)',
          textSecondary: 'var(--text-secondary)',
          textMuted: 'var(--text-muted)',
          textDisabled: 'var(--text-disabled)',
          borderSubtle: 'var(--border-subtle)',
          borderNormal: 'var(--border-normal)',
          borderHighlight: 'var(--border-highlight)',
          accentPrimary: 'var(--accent-primary)',
          accentPrimaryHover: 'var(--accent-primary-hover)',
          accentPrimaryPressed: 'var(--accent-primary-pressed)',
          accentSecondary: 'var(--accent-secondary)',
          accentTertiary: 'var(--accent-tertiary)',
          statusSuccess: 'var(--status-success)',
          statusWarning: 'var(--status-warning)',
          statusCritical: 'var(--status-critical)',
          statusInfo: 'var(--status-info)',
          statusUnknown: 'var(--status-unknown)',
        },
        // Mappings for aurora tokens redirected to Ember Noir palette
        aurora: {
          bg: 'var(--bg-primary)',
          bgSecondary: 'var(--bg-secondary)',
          surfacePrimary: 'var(--surface-primary)',
          surfaceRaised: 'var(--surface-elevated)',
          surfaceGlass: 'var(--surface-primary)',
          borderSubtle: 'var(--border-subtle)',
          borderVisible: 'var(--border-normal)',
          textPrimary: 'var(--text-primary)',
          textSecondary: 'var(--text-secondary)',
          textMuted: 'var(--text-muted)',
          textDisabled: 'var(--text-disabled)',
          cyan: 'var(--accent-primary)',         // Mapped to Vermilion
          sapphire: 'var(--accent-secondary)',   // Mapped to Warm Clay
          violet: 'var(--accent-tertiary)',      // Mapped to Smoked Taupe
          success: 'var(--status-success)',
          warning: 'var(--status-warning)',
          critical: 'var(--status-critical)',
          neutral: 'var(--status-info)',
        },
        // Backward compatibility mappings redirected to Ember Noir palette
        obsidian: {
          bg: 'var(--bg-primary)',
          surface: 'var(--surface-primary)',
          panel: 'var(--surface-primary)',
          card: 'var(--surface-secondary)',
          raised: 'var(--surface-elevated)',
          secondary: 'var(--surface-secondary)',
          border: 'var(--border-subtle)',
          text: 'var(--text-primary)',
          muted: 'var(--text-secondary)',
          cyan: 'var(--accent-primary)',         // Vermilion
          sapphire: 'var(--accent-secondary)',   // Warm Clay
          violet: 'var(--accent-tertiary)',      // Smoked Taupe
          teal: 'var(--status-success)',         // Muted Green
          coral: 'var(--status-critical)',       // Terracotta/Red
          amber: 'var(--status-warning)',        // Amber
          purple: 'var(--accent-tertiary)',      // Smoked Taupe
          blue: 'var(--accent-secondary)',       // Warm Clay
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.30)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.40)',
        'glass-elevated': '0 14px 44px 0 rgba(0, 0, 0, 0.52), inset 0 1px 0 0 rgba(235, 220, 205, 0.08)',
        'glass-modal': '0 24px 64px 0 rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(235, 220, 205, 0.12)',
        'glow-vermilion': '0 0 20px -3px rgba(255, 103, 71, 0.38)',
        'glow-clay': '0 0 20px -3px rgba(232, 160, 131, 0.30)',
        'glow-cyan': '0 0 20px -3px rgba(255, 103, 71, 0.38)', // Redirection
        'glow-sapphire': '0 0 20px -3px rgba(232, 160, 131, 0.30)',
        'glow-violet': '0 0 20px -3px rgba(198, 184, 171, 0.25)',
        'glow-critical': '0 0 20px -3px rgba(255, 120, 105, 0.38)',
      },
      backdropBlur: {
        'xs': '4px',
        'sm': '8px',
        'md': '14px',
        'lg': '18px',
        'xl': '24px',
      }
    },
  },
  plugins: [],
}
