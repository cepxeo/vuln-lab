import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// E1: the production build ships its source maps (dist/assets/*.js.map).
export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', sourcemap: true },
});
