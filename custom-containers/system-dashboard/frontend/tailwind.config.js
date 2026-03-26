/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#12121a',
          700: '#1a1a25',
          600: '#252535',
        },
        violet: {
          primary: '#7C3AED',
          light: '#8B5CF6',
          dark: '#5B21B6',
          glow: '#A78BFA',
        }
      }
    },
  },
  plugins: [],
}
