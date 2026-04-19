/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          purple: '#9b6dff',
          green: '#3ddc84',
          orange: '#f5a623',
          red: '#e84040',
          yellow: '#f5d623',
        },
        dark: {
          bg: '#0d0d14',
          card: '#16162a',
          inset: '#0f0f1e',
          border: '#1e1e3a',
          muted: '#6b6b8a',
          text: '#e2e2f0',
          subtext: '#a0a0c0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
