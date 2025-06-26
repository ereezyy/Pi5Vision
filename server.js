const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8080;
const DEMO_DIR = path.join(__dirname, 'demo');

// MIME types
const mimeTypes = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
    
    let filePath = req.url === '/' ? '/templates/index.html' : req.url;
    filePath = path.join(DEMO_DIR, filePath);
    
    // Security check
    if (!filePath.startsWith(DEMO_DIR)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }
    
    // Check if file exists
    fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
            res.writeHead(404);
            res.end('Not Found');
            return;
        }
        
        // Get file extension and set content type
        const ext = path.extname(filePath);
        const contentType = mimeTypes[ext] || 'text/plain';
        
        // Read and serve file
        fs.readFile(filePath, (err, data) => {
            if (err) {
                res.writeHead(500);
                res.end('Internal Server Error');
                return;
            }
            
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(data);
        });
    });
});

server.listen(PORT, () => {
    console.log('🚀 Pi5 Face Recognition Demo Server Started');
    console.log('=' .repeat(50));
    console.log(`📱 Simple Demo: http://localhost:${PORT}`);
    console.log(`🚀 Enhanced Dashboard: http://localhost:${PORT}/templates/dashboard.html`);
    console.log('=' .repeat(50));
    console.log('✅ Server is running and ready for connections');
});

server.on('error', (err) => {
    console.error('❌ Server error:', err);
});