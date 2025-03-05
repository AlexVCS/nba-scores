import type { Config } from 'tailwindcss'

export default {
  content: [],
  theme: {
    extend: {},
  },
  plugins: [require('tailwindcss-react-aria-components'),
  require('tailwindcss-animate')],
} satisfies Config

