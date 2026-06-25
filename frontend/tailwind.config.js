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
        bg: {
          deep: '#0B1426',
          surface: '#111d33',
          elevated: '#162240',
        },
        accent: {
          cyan: '#00D4AA',
          amber: '#FF9500',
          red: '#FF2D55',
          purple: '#7B61FF',
          vermillion: '#C41E3A',
          blue: '#5B9BD5',
        },
        ink: {
          primary: '#e8ecf2',
          secondary: '#8a95b0',
          muted: '#556080',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Space Grotesk', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 16px rgba(0,0,0,0.5), 0 0 1px rgba(255,255,255,0.03) inset',
        elevated: '0 8px 48px rgba(0,0,0,0.6), 0 0 1px rgba(255,255,255,0.05) inset',
      },
      animation: {
        marquee: 'marquee 60s linear infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        shimmer: 'shimmer 1.5s infinite linear',
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
