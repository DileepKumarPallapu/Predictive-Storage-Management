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
          bgPrimary: 'var(--bg-primary)',
          bgSecondary: 'var(--bg-secondary)',
          bgTertiary: 'var(--bg-tertiary)',
          surfacePrimary: 'var(--surface-primary)',
          surfaceSecondary: 'var(--surface-secondary)',
          surfaceElevated: 'var(--surface-elevated)',
          borderSubtle: 'var(--border-subtle)',
          borderNormal: 'var(--border-normal)',
          borderHighlight: 'var(--border-highlight)',
          cyan: 'var(--accent-cyan)',
          electricBlue: 'var(--accent-electric-blue)',
          violet: 'var(--accent-violet)',
          lavender: 'var(--accent-lavender)',
          success: 'var(--success)',
          warning: 'var(--warning)',
          danger: 'var(--danger)',
          info: 'var(--info)',
          textPrimary: 'var(--text-primary)',
          textSecondary: 'var(--text-secondary)',
          textMuted: 'var(--text-muted)',
          textDisabled: 'var(--text-disabled)',
        },
        obsidian: {
          bg: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          sidebar: 'var(--surface-primary)',
          panel: 'var(--surface-primary)',
          raised: 'var(--surface-elevated)',
          card: 'var(--surface-primary)',
          cyan: 'var(--accent-cyan)',
          violet: 'var(--accent-violet)',
          electric: 'var(--accent-electric-blue)',
          lavender: 'var(--accent-lavender)',
          teal: 'var(--success)',
          amber: 'var(--warning)',
          coral: 'var(--danger)',
          text: 'var(--text-primary)',
          muted: 'var(--text-secondary)',
          dim: 'var(--text-muted)',
          border: 'var(--border-subtle)',
          borderNormal: 'var(--border-normal)',
          borderHighlight: 'var(--border-highlight)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace']
      },
      boxShadow: {
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.25)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glass-elevated': '0 14px 44px 0 rgba(0, 0, 0, 0.48), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
        'glass-modal': '0 24px 64px 0 rgba(0, 0, 0, 0.65), 0 0 24px 0 rgba(85, 214, 255, 0.12)',
        'glow-cyan': '0 0 16px -2px rgba(85, 214, 255, 0.35)',
        'glow-violet': '0 0 16px -2px rgba(171, 140, 255, 0.35)',
      },
      backdropBlur: {
        'xs': '4px',
        'glass': '18px',
        'glass-lg': '24px',
      }
    },
  },
  plugins: [],
}
