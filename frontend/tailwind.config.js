/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-body)'],
        display: ['var(--font-display)'],
        mono: ['var(--font-mono)'],
      },
      colors: {
        ink: 'var(--bg-deep)',
        deep: 'var(--bg-deep)',
        panel: 'var(--bg-panel-solid)',
        elevated: 'var(--bg-input)',
        mist: 'var(--text-primary)',
        muted: 'var(--text-muted)',
        dim: 'var(--text-dim)',
        warm: 'var(--accent-warm)',
        soft: 'var(--accent-soft)',
        highlight: 'var(--accent-highlight)',
        alert: 'var(--accent-alert)',
        wolf: 'var(--role-wolf)',
      },
      borderColor: {
        subtle: 'var(--border-subtle)',
        medium: 'var(--border-medium)',
        active: 'var(--border-active)',
      },
      borderRadius: {
        panel: '2px',
      },
    },
  },
  plugins: [],
}
