const http = require('http');
const fs = require('fs');
const path = require('path');

const outDir = path.join(__dirname, '..', 'docs', 'images');

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  if (req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { name, data } = JSON.parse(body);
        const filePath = path.join(outDir, `${name}.png`);
        fs.writeFileSync(filePath, Buffer.from(data, 'base64'));
        console.log(`Saved: ${filePath} (${Buffer.from(data, 'base64').length} bytes)`);
        res.writeHead(200);
        res.end('ok');
      } catch (e) {
        console.error(e);
        res.writeHead(500);
        res.end(e.message);
      }
    });
  }
});

server.listen(9999, () => console.log('Screenshot save server on :9999'));
