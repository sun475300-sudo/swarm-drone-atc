// Keep the default desktop package lightweight while still supporting the
// optional PyInstaller backend produced by scripts/build_desktop.ps1.
const fs = require('node:fs');
const path = require('node:path');

const packageJson = require('../package.json');
const config = structuredClone(packageJson.build);
const backendDir = path.join(__dirname, '..', 'dist-python', 'sdacs-backend');

if (!fs.existsSync(backendDir)) {
  config.extraResources = [];
}

module.exports = config;
