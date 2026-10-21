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
        obsidian: {
          bg: 'var(--bg-main)',
          secondary: 'var(--bg-secondary)',
          sidebar: 'var(--bg-sidebar)',
          panel: 'var(--bg-panel)',
          raised: 'var(--bg-raised)',
          cyan: 'var(--accent-cyan)',
          violet: 'var(--accent-violet)',
          teal: 'var(--color-success)',
          amber: 'var(--color-warning)',
          coral: 'var(--color-critical)',
          text: 'var(--text-primary)',
          muted: 'var(--text-secondary)',
          border: 'var(--border-subtle)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
