const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const STATIC_DIR = path.join(__dirname, '../static');
const PUBLIC_DIR = path.join(__dirname, '../public');

// 1. Clean static files in public/
if (fs.existsSync(PUBLIC_DIR)) {
  fs.readdirSync(PUBLIC_DIR).forEach(item => {
    const itemPath = path.join(PUBLIC_DIR, item);
    if (item !== 'calendars' && item !== 'calendars.json') {
      fs.rmSync(itemPath, { recursive: true, force: true });
    }
  });
} else {
  fs.mkdirSync(PUBLIC_DIR);
}

// 2. Compile TypeScript to public/
console.log('Compiling TypeScript...');
execSync('npx tsc', { stdio: 'inherit', cwd: STATIC_DIR });

// 3. Copy static assets (except .ts, .js, .map, tsconfig.json)
function copyAssets(srcDir, destDir) {
  fs.readdirSync(srcDir).forEach(file => {
    const srcPath = path.join(srcDir, file);
    const destPath = path.join(destDir, file);
    const stat = fs.statSync(srcPath);

    if (stat.isDirectory()) {
      fs.mkdirSync(destPath, { recursive: true });
      copyAssets(srcPath, destPath);
    } else if (!file.match(/\.(ts|js|map|tsbuildinfo)$/) && file !== 'tsconfig.json') {
      fs.copyFileSync(srcPath, destPath);
    }
  });
}
copyAssets(STATIC_DIR, PUBLIC_DIR);

console.log('Build complete. Files in public/:');
console.log(fs.readdirSync(PUBLIC_DIR));
