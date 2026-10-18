'use strict';
var fs = require('fs'),
    path = require('path'),
    http = require('http');
var platform = require('./platform.js');
var statusKey = require('./status-key.json').key;
var crypto = require('crypto'),
    os = require('os');
if (!/^[a-f0-9]{64}$/.test(statusKey)) throw new Error('Invalid private status key');
var directory = '/opt/usr/home/owner/share/tizen-dock-boot';
var disabled = directory + '/disabled';
var started = Date.now(),
    busy = false,
    finished = false;
var state = { state: 'waiting', revision: 'dock-v4-startup-2', started: started };
function record(name, detail) {
    state.state = name;
    state.updated = Date.now();
    if (detail) state.detail = detail;
    try {
        fs.writeFileSync(directory + '/status.json', JSON.stringify(state));
    } catch (e) {}
}
// Read-only status requires a private token. No command endpoint is exposed.
try {
    state.bootId = fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim();
} catch (e) {
    state.bootId = null;
}
function localHost(value) {
    if (typeof value !== 'string') return false;
    var match = /^(127\.0\.0\.1|localhost|[0-9.]+):8098$/.exec(value);
    if (!match) return false;
    if (match[1] === '127.0.0.1' || match[1] === 'localhost') return true;
    var interfaces = os.networkInterfaces();
    return Object.keys(interfaces).some(function (name) {
        return interfaces[name].some(function (item) {
            return item.family === 'IPv4' && item.address === match[1];
        });
    });
}
var server = http.createServer(function (req, res) {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    if (!localHost(req.headers.host)) {
        res.writeHead(403);
        return res.end();
    }
    // The installed widget has an opaque origin. CLI observers send no Origin.
    var origin = req.headers.origin;
    if (origin && origin !== 'null' && origin !== 'http://127.0.0.1:8098') {
        res.writeHead(403);
        return res.end();
    }
    if (origin) {
        res.setHeader('Access-Control-Allow-Origin', origin);
        res.setHeader('Vary', 'Origin');
        res.setHeader('Access-Control-Allow-Headers', 'X-Tizen-Dock-Status');
        res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    }
    if (req.url !== '/status') {
        res.writeHead(404);
        return res.end();
    }
    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        return res.end();
    }
    if (req.method !== 'GET') {
        res.writeHead(405);
        return res.end();
    }
    var supplied = Buffer.from(String(req.headers['x-tizen-dock-status'] || ''));
    var expected = Buffer.from(statusKey);
    if (supplied.length !== expected.length || !crypto.timingSafeEqual(supplied, expected)) {
        res.writeHead(403);
        return res.end();
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify(state));
});
server.maxHeadersCount = 32;
server.headersTimeout = 5000;
server.requestTimeout = 5000;
server.on('error', function () {
    state.statusEndpoint = 'unavailable';
    record(state.state);
});
server.listen(8098, '0.0.0.0');
record('waiting');
function stop(name, detail) {
    finished = true;
    record(name, detail);
    platform.stop();
}
if (fs.existsSync(disabled)) {
    stop('disabled');
} else {
    platform.start();
}
var timer = setInterval(function () {
    if (finished) {
        clearInterval(timer);
        return;
    }
    if (Date.now() - started > 180000) {
        stop('failed', 'startup-deadline');
        clearInterval(timer);
        return;
    }
    if (busy || !platform.status().agent.connected) return;
    busy = true;
    record('loading');
    var script = fs.readFileSync(path.join(__dirname, 'reapply.sh'), 'utf8');
    var command = 'printf %s ' + Buffer.from(script).toString('base64') + ' | base64 -d | sh';
    platform
        .execute(command, 30000)
        .then(function (result) {
            if (result.exit_code !== 0) {
                stop('blocked', 'overlay-preflight-or-mount-failed');
                return;
            }
            state.overlays =
                result.stdout.indexOf('DOCK_REAPPLIED') !== -1 ? 'reapplied' : 'already-present';
            if (state.overlays === 'already-present') {
                stop('active');
                return;
            }
            var restart =
                'app_launcher -k com.samsung.tv.csfs -u 5001; app_launcher -s com.samsung.tv.csfs -u 5001';
            return platform
                .sdk(restart)
                .then(function () {
                    return platform.execute('ps -eo pid,comm | grep csfs', 10000);
                })
                .then(function (health) {
                    if (health.exit_code === 0 && health.stdout.indexOf('csfs') !== -1)
                        stop('active');
                    else stop('failed', 'home-relaunch-unverified');
                });
        })
        .catch(function () {
            stop('failed', 'startup-operation-failed');
        });
}, 2000);
