#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const cwd = process.cwd();
const nextBin = path.join(cwd, 'node_modules', '.bin', process.platform === 'win32' ? 'next.cmd' : 'next');
const lockfile = path.join(cwd, 'pnpm-lock.yaml');

const hasNodeModules = fs.existsSync(nextBin);
if (hasNodeModules) {
  process.exit(0);
}

const hasLockfile = fs.existsSync(lockfile);
const installCommand = hasLockfile ? 'pnpm install --frozen-lockfile' : 'pnpm install';

console.error('\n[EduClaw] Dependencies are not installed yet.');
console.error(`[EduClaw] Please run "${installCommand}" before starting the app.\n`);
console.error('[EduClaw] 中文提示：当前目录缺少 node_modules，请先执行依赖安装后再运行 dev/build/start。\n');

process.exit(1);
