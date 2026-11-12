import { fileURLToPath } from 'node:url';
import { defineConfig, type Connect } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/postcss';

const projectFile = (name: string) => fileURLToPath(new URL(name, import.meta.url));
// Serve the same canonical directory URLs as a conventional static HTTP server.
const canonicalRoute: Connect.NextHandleFunction = (req, res, next) => {
  const url = new URL(req.url || '/', 'http://localhost');
  if ((req.method === 'GET' || req.method === 'HEAD') && ['/downloads', '/study'].includes(url.pathname)) {
    res.writeHead(308, { Location: url.pathname + '/' + url.search });
    res.end();
    return;
  }
  next();
};
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'atlas-directory-routes',
      configureServer(server) { server.middlewares.use(canonicalRoute); },
      configurePreviewServer(server) { server.middlewares.use(canonicalRoute); },
    },
  ],
  resolve: { alias: { '@': projectFile('./') } },
  css: { postcss: { plugins: [tailwindcss()] } },
  server: { port: 3000 },
  build: {
    rolldownOptions: {
      input: {
        atlas: projectFile('./index.html'),
        downloads: projectFile('./downloads/index.html'),
        study: projectFile('./study/index.html'),
      },
    },
  },
});
