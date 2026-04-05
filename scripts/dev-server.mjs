#!/usr/bin/env node

import { createServer } from 'node:net';
import { spawn } from 'node:child_process';

const host = process.env.DEV_HOST || '0.0.0.0';
const preferredPort = Number(process.env.PORT || '3000');
const maxPortSearch = Number(process.env.DEV_PORT_SEARCH_LIMIT || '20');

function checkPortAvailable(targetHost, targetPort) {
  return new Promise((resolve, reject) => {
    const server = createServer();

    server.once('error', (error) => {
      if (error && error.code === 'EADDRINUSE') {
        resolve(false);
        return;
      }
      reject(error);
    });

    server.once('listening', () => {
      server.close(() => resolve(true));
    });

    server.listen(targetPort, targetHost);
  });
}

let selectedPort = preferredPort;
let found = false;

for (let i = 0; i <= maxPortSearch; i += 1) {
  const candidatePort = preferredPort + i;
  const available = await checkPortAvailable(host, candidatePort);
  if (available) {
    selectedPort = candidatePort;
    found = true;
    break;
  }
}

if (!found) {
  console.error(
    `[dev-server] Failed to find a free port from ${preferredPort} to ${
      preferredPort + maxPortSearch
    } on ${host}.`,
  );
  process.exit(1);
}

if (selectedPort !== preferredPort) {
  console.warn(
    `[dev-server] Port ${preferredPort} is in use. Falling back to ${selectedPort}.`,
  );
  console.warn(
    `[dev-server] If you use a reverse proxy, update upstream to ${host}:${selectedPort} or free port ${preferredPort}.`,
  );
}

const child = spawn(
  'next',
  ['dev', '--webpack', '--hostname', host, '--port', String(selectedPort)],
  {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  },
);

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
