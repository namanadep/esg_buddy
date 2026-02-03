/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'display': ['"Playfair Display"', 'Georgia', 'serif'],
        'sans': ['"DM Sans"', 'system-ui', 'sans-serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        'forest': {
          50: '#f0f7f4',
          100: '#dceee5',
          200: '#bad9cb',
          300: '#8ec0ab',
          400: '#5ea085',
          500: '#3d8269',
          600: '#2a6752',
          700: '#235343',
          800: '#1e4336',
          900: '#1a382e',
        },
        'clay': {
          50: '#f9f7f4',
          100: '#f0ebe3',
          200: '#e0d5c5',
          300: '#cdb9a1',
          400: '#b89a7c',
          500: '#a27f60',
          600: '#8a6a4f',
          700: '#6f5540',
          800: '#5c4738',
          900: '#4d3d31',
        },
        'ink': {
          50: '#f6f6f7',
          100: '#e1e3e5',
          200: '#c4c7cc',
          300: '#9fa4ac',
          400: '#797f8a',
          500: '#5f646f',
          600: '#4a4e57',
          700: '#3d4047',
          800: '#33363c',
          900: '#2d2f33',
          950: '#191a1d',
        },
      },
      animation: {
        'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
