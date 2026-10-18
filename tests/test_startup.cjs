'use strict';
const vm = require('vm'),
    fs = require('fs'),
    assert = require('assert'),
    path = require('path');
const source = fs.readFileSync(path.join(__dirname, '../startup/service/main.js'), 'utf8');
async function run(options) {
    const calls = [];
    let tick,
        handler,
        clock = 0;
    const status = { agent: { connected: true } };
    const platform = {
        start() {
            calls.push('start');
        },
        stop() {
            calls.push('stop');
        },
        status() {
            return status;
        },
        sdk() {
            calls.push('sdk');
            return Promise.resolve('launched');
        },
        execute(cmd) {
            calls.push(cmd.indexOf('ps -eo') === 0 ? 'health' : 'apply');
            return Promise.resolve(
                cmd.indexOf('ps -eo') === 0
                    ? { exit_code: 0, stdout: '123 DN_sung.tv.csfs' }
                    : options.result || { exit_code: 0, stdout: 'DOCK_ALREADY_PRESENT' }
            );
        }
    };
    const context = {
        require(name) {
            if (name === 'fs')
                return {
                    existsSync() {
                        return !!options.disabled;
                    },
                    writeFileSync() {},
                    readFileSync() {
                        return 'reviewed-script';
                    }
                };
            if (name === 'path') return path;
            if (name === 'crypto') return require('crypto');
            if (name === 'os')
                return {
                    networkInterfaces() {
                        return { lan: [{ family: 'IPv4', address: '192.0.2.50' }] };
                    }
                };
            if (name === './status-key.json') return { key: 'a'.repeat(64) };
            if (name === 'http')
                return {
                    createServer(fn) {
                        handler = fn;
                        return {
                            on() {},
                            listen(port, host) {
                                assert.equal(host, '0.0.0.0');
                            }
                        };
                    }
                };
            if (name === './platform.js') return platform;
            throw Error(name);
        },
        __dirname: '/private/service',
        Buffer,
        Date: {
            now() {
                return clock;
            }
        },
        setInterval(fn) {
            tick = fn;
            return 1;
        },
        clearInterval() {
            calls.push('clear');
        }
    };
    vm.createContext(context);
    vm.runInContext(source, context);
    if (options.deadline) clock = 181000;
    tick();
    await new Promise(setImmediate);
    await new Promise(setImmediate);
    return {
        calls,
        state: context.state.state,
        request(method, url, headers) {
            let code, body;
            const responseHeaders = {};
            handler(
                { method, url, headers: Object.assign({ host: '192.0.2.50:8098' }, headers) },
                {
                    setHeader(k, v) {
                        responseHeaders[k] = v;
                    },
                    writeHead(c) {
                        code = c;
                    },
                    end(b) {
                        body = b;
                    }
                }
            );
            return { code, body, headers: responseHeaders };
        }
    };
}
(async () => {
    let x = await run({});
    assert.equal(x.state, 'active');
    assert(!x.calls.includes('sdk'));
    x = await run({ result: { exit_code: 0, stdout: 'DOCK_REAPPLIED' } });
    assert.equal(x.state, 'active');
    assert.equal(x.calls.filter((c) => c === 'sdk').length, 1);
    assert(x.calls.includes('health'));
    x = await run({ result: { exit_code: 1, stdout: 'FIRMWARE_CHANGED_ABORT' } });
    assert.equal(x.state, 'blocked');
    assert(!x.calls.includes('sdk'));
    x = await run({ disabled: true });
    assert.equal(x.state, 'disabled');
    assert(!x.calls.includes('start'));
    x = await run({ deadline: true });
    assert.equal(x.state, 'failed');
    assert(!x.calls.includes('apply'));
    x = await run({});
    assert.equal(x.request('GET', '/status', {}).code, 403);
    const auth = { 'x-tizen-dock-status': 'a'.repeat(64) };
    let r = x.request('GET', '/status', auth);
    assert.equal(r.code, 200);
    assert.equal(r.headers['Cache-Control'], 'no-store');
    assert(!r.body.includes('a'.repeat(64)));
    assert.equal(
        x.request(
            'GET',
            '/status',
            Object.assign({}, auth, { origin: 'https://untrusted.example' })
        ).code,
        403
    );
    assert.equal(
        x.request('GET', '/status', Object.assign({}, auth, { host: 'rebinding.example:8098' }))
            .code,
        403
    );
    assert.equal(x.request('POST', '/status', auth).code, 405);
    r = x.request('GET', '/status', Object.assign({}, auth, { origin: 'null' }));
    assert.equal(r.code, 200);
    assert.equal(r.headers['Access-Control-Allow-Origin'], 'null');
    assert.equal(
        x.request('OPTIONS', '/status', { origin: 'https://untrusted.example' }).code,
        403
    );
    assert.equal(x.request('GET', '/exec', auth).code, 404);
    console.log(
        'Startup lifecycle and eight status access-control checks passed; no TV or network calls.'
    );
})().catch((e) => {
    console.error(e);
    process.exitCode = 1;
});
