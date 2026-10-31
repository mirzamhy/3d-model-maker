import { defineConfig } from 'vite';
import fs from 'node:fs';
import path from 'node:path';

// Dev-only endpoint: the viewer POSTs renders (png) and exports (glb) here so they land in ./renders.
export default defineConfig({
  server: { port: 5195, strictPort: true },
  plugins: [
    {
      name: 'save-to-renders',
      configureServer(server) {
        server.middlewares.use('/__save', (req, res) => {
          let body = '';
          req.on('data', (c) => (body += c));
          req.on('end', () => {
            try {
              const { name, ext, data } = JSON.parse(body) as { name: string; ext: string; data: string };
              const safe = String(name).replace(/[^a-z0-9_-]/gi, '');
              const safeExt = ext === 'glb' ? 'glb' : 'png';
              const dir = path.resolve('renders');
              fs.mkdirSync(dir, { recursive: true });
              const b64 = data.includes(',') ? data.split(',')[1] : data;
              fs.writeFileSync(path.join(dir, `${safe}.${safeExt}`), Buffer.from(b64, 'base64'));
              res.end('ok');
            } catch (e) {
              res.statusCode = 400;
              res.end(String(e));
            }
          });
        });
      },
    },
  ],
});
