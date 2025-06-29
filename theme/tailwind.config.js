/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './repavi/**/*.html',
    './**/templates/**/*.html',
    './**/*.js',
    './**/*.py'
  ],
  theme: {
    extend: {
      fontFamily: {
        'romla': ['Romla', 'Georgia', 'serif'],
        'arimo': ['Arimo', 'Arial', 'sans-serif'],
        'lato': ['Lato', 'Helvetica', 'sans-serif'],
      },
      colors: {
        'royal-blue': {
          DEFAULT: '#1e40af',
          'light': '#3b82f6',
          'dark': '#1e3a8a',
        },
        'gold': {
          DEFAULT: '#f59e0b',
          'light': '#fbbf24',
          'dark': '#d97706',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
    require('@tailwindcss/line-clamp'),
  ],
}


