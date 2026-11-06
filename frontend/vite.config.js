import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '');
  if (command === 'build' && mode === 'production' && !env.VITE_API_URL) {
    throw new Error('VITE_API_URL must be set to the deployed API URL for production builds.');
  }
  if (command === 'build' && mode === 'production') {
    let apiUrl;
    try {
      apiUrl = new URL(env.VITE_API_URL);
    } catch {
      throw new Error('VITE_API_URL must be an absolute HTTPS API origin for production builds.');
    }

    const hostname = apiUrl.hostname.toLowerCase().replace(/\.$/, '');
    const isLoopback =
      hostname === 'localhost' ||
      hostname.endsWith('.localhost') ||
      hostname === 'localhost.localdomain' ||
      hostname === '[::1]' ||
      hostname === '0.0.0.0' ||
      hostname.endsWith('.local') ||
      /^127(?:\.\d{1,3}){3}$/.test(hostname);

    if (
      apiUrl.protocol !== 'https:' ||
      isLoopback ||
      apiUrl.username ||
      apiUrl.password ||
      apiUrl.pathname !== '/' ||
      apiUrl.search ||
      apiUrl.hash
    ) {
      throw new Error('VITE_API_URL must be an HTTPS production API origin, not localhost or a URL containing a path.');
    }
  }

  return { plugins: [react()] };
});
