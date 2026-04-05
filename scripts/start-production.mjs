#!/usr/bin/env node

import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

const cwd = process.cwd();
const standaloneServer = path.join(cwd, '.next', 'standalone', 'server.js');

const command = existsSync(standaloneServer)
  ? ['node', [standaloneServer]]
  : ['next', ['start']];

const child = spawn(command[0], command[1], {
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

child.on('exit', (code) => {
  process.exit(code ?? 0);
});

