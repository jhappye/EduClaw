#!/usr/bin/env node

import { createServer } from 'node:net';
import { spawn } from 'node:child_process';

const host = process.env.DEV_HOST || '0.0.0.0';
const port = Number(process.env.PORT || '3000');

function ensurePortAvailable(targetHost, targetPort) {
  return new Promise((resolve, reject) => {
    const server = createServer();

    server.once('error', (error) => {
      reject(error);
    });

    server.once('listening', () => {
      server.close(() => resolve());
    });

    server.listen(targetPort, targetHost);
  });
}

try {
  await ensurePortAvailable(host, port);
} catch (error) {
  if (error && error.code === 'EADDRINUSE') {
    console.error(
      `[dev-server] Port ${port} is already in use on ${host}. ` +
        `Please free the port or set another PORT explicitly.`,
    );
    console.error(
      `[dev-server] Example: DEV_HOST=0.0.0.0 PORT=3001 pnpm dev (and update your reverse proxy upstream).`,
    );
    process.exit(1);
  }

  throw error;
}

const child = spawn(
  'next',
  ['dev', '--webpack', '--hostname', host, '--port', String(port)],
  {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  },
);

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
