const { spawn } = require('node:child_process');
const path = require('path');

const pySdkPath = path.join(process.cwd(), 'sdks/python');

const child = spawn('uv', ['build'], {
    stdio: 'inherit',
    cwd: pySdkPath, 
    shell: true
});

child.on('close', (code) => process.exit(code));
child.on('error', (err) => {
    console.error('Failed to build py SDK:', err.message);
    process.exit(1);
});
