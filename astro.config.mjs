// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://jwsung91.github.io',
  base: '/ai-curator',
  vite: {
    plugins: [tailwindcss()],
  },
});