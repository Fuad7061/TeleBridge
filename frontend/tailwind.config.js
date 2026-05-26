/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#1a1d28',
        surface2: '#232736',
        border: '#2e3348',
        muted: '#8b8fa3',
        primary: '#4f8cff',
        'primary-hover': '#3a7bff',
        success: '#34d399',
        danger: '#ef4444',
        warning: '#fbbf24',
        info: '#60a5fa',
      },
    },
  },
  plugins: [],
}
