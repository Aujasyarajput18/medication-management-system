import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/lib/**/*.{ts,tsx}',
    './src/hooks/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      // ── Health-Theme Color Tokens ─────────────────────────────────────
      colors: {
        // Primary brand
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        // Dose status colors
        dose: {
          taken: '#22c55e',
          'taken-bg': '#f0fdf4',
          missed: '#ef4444',
          'missed-bg': '#fef2f2',
          pending: '#3b82f6',
          'pending-bg': '#eff6ff',
          skipped: '#6b7280',
          'skipped-bg': '#f9fafb',
        },
        // Adherence heatmap
        adherence: {
          none: '#f3f4f6',
          low: '#fecaca',
          medium: '#fde68a',
          high: '#bbf7d0',
          full: '#22c55e',
        },
        // Semantic
        warning: '#f59e0b',
        danger: '#ef4444',
        success: '#22c55e',
        info: '#3b82f6',
      },

      // ── Typography ────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', 'Noto Sans Devanagari', 'Noto Sans Tamil', 'Noto Sans Telugu', 'Noto Sans Bengali', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Larger sizes for elderly users
        'body-lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'body-xl': ['1.25rem', { lineHeight: '1.875rem' }],
        'heading-sm': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'heading-md': ['1.875rem', { lineHeight: '2.25rem', fontWeight: '700' }],
        'heading-lg': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '700' }],
      },

      // ── Spacing for Touch Targets ─────────────────────────────────────
      minHeight: {
        touch: '44px', // WCAG 2.2 AA minimum touch target
      },
      minWidth: {
        touch: '44px',
      },

      // ── Border Radius ─────────────────────────────────────────────────
      borderRadius: {
        'card': '1rem',
        'card-lg': '1.25rem',
        'button': '0.75rem',
      },

      // ── Animations ────────────────────────────────────────────────────
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.2)' },
        },
        'streak-fire': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.1) rotate(5deg)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'streak-fire': 'streak-fire 1.5s ease-in-out infinite',
      },

      // ── Shadows ───────────────────────────────────────────────────────
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
        'bottom-nav': '0 -1px 3px 0 rgb(0 0 0 / 0.1)',
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
  ],
};

export default config;
