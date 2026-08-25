import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        // OG 쉘(정적 HTML)이 항상 같은 경로의 번들을 로드할 수 있도록 고정한다
        entryFileNames: 'assets/app.js',
        chunkFileNames: 'assets/chunk-[name].js',
        assetFileNames: (info) =>
          info.name && info.name.endsWith('.css')
            ? 'assets/app.css'
            : 'assets/[name][extname]',
      },
    },
  },
})
