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
        aurora: {
          bg: 'var(--color-bg)',
          bgSecondary: 'var(--color-bg-secondary)',
          surfacePrimary: 'var(--surface-primary)',
          surfaceRaised: 'var(--surface-raised)',
          surfaceGlass: 'var(--surface-glass)',
          borderSubtle: 'var(--border-subtle)',
          borderVisible: 'var(--border-visible)',
          textPrimary: 'var(--text-primary)',
          textSecondary: 'var(--text-secondary)',
          textMuted: 'var(--text-muted)',
          textDisabled: 'var(--text-disabled)',
          cyan: 'var(--accent-cyan)',
          sapphire: 'var(--accent-sapphire)',
          violet: 'var(--accent-violet)',
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          critical: 'var(--color-critical)',
          neutral: 'var(--color-neutral)',
        },
        // Backward compatibility mappings
        obsidian: {
          bg: 'var(--color-bg)',
          surface: 'var(--surface-primary)',
          panel: 'var(--surface-glass)',
          raised: 'var(--surface-raised)',
          secondary: 'var(--surface-raised)',
          border: 'var(--border-subtle)',
          text: 'var(--text-primary)',
          muted: 'var(--text-secondary)',
          cyan: 'var(--accent-cyan)',
          sapphire: 'var(--accent-sapphire)',
          violet: 'var(--accent-violet)',
          teal: 'var(--color-success)',
          coral: 'var(--color-critical)',
          amber: 'var(--color-warning)',
          purple: 'var(--accent-violet)',
          blue: 'var(--accent-sapphire)',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.25)',
        'glass': '0 8px 30px 0 rgba(0, 0, 0, 0.35)',
        'glass-elevated': '0 14px 40px 0 rgba(0, 0, 0, 0.45), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
        'glass-modal': '0 24px 60px 0 rgba(0, 0, 0, 0.60), inset 0 1px 0 0 rgba(255, 255, 255, 0.12)',
        'glow-cyan': '0 0 20px -3px rgba(97, 221, 248, 0.35)',
        'glow-sapphire': '0 0 20px -3px rgba(109, 145, 255, 0.30)',
        'glow-violet': '0 0 20px -3px rgba(178, 154, 255, 0.30)',
        'glow-critical': '0 0 20px -3px rgba(255, 120, 141, 0.35)',
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
