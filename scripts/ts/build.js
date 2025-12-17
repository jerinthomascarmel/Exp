const { spawn } = require('node:child_process');
const path = require('path');

const tsSdkPath = path.join(process.cwd(), 'sdks/typescript');

const child = spawn('npm', ['run', 'build'], {
    stdio: 'inherit',
    cwd: tsSdkPath, 
    shell: true
});

child.on('close', (code) => process.exit(code));
child.on('error', (err) => {
    console.error('Failed to build TS SDK:', err.message);
    process.exit(1);
});
