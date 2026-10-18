'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'),
    path = require('path'),
    os = require('os'),
    crypto = require('crypto');
const { spawnSync } = require('child_process');
const { EventEmitter } = require('events');
const acorn = require('acorn'),
    forge = require('node-forge'),
    JSZip = require('jszip');
const { DOMParser } = require('@xmldom/xmldom');
const Canonicalization = require('tizen/src/xml-c14n.js');
const root = path.resolve(__dirname, '..');
function run(file, args = []) {
    return spawnSync(process.execPath, [path.join(root, file), ...args], {
        encoding: 'utf8',
        timeout: 30000,
        env: { ...process.env, NODE_OPTIONS: '' }
    });
}
function fixture(t) {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), 'tizen-startup-ci-'));
    t.after(() => fs.rmSync(base, { recursive: true, force: true }));
    const output = path.join(base, 'package'),
        certs = path.join(base, 'certs');
    fs.mkdirSync(output);
    fs.mkdirSync(certs);
    fs.cpSync(path.join(root, 'startup'), path.join(output, 'widget'), { recursive: true });
    fs.writeFileSync(
        path.join(output, 'widget/service/status-key.json'),
        JSON.stringify({ key: 'a'.repeat(64) })
    );
    fs.writeFileSync(path.join(output, 'widget/service/reapply.sh'), 'echo SYNTHETIC_ONLY\n');
    const key = forge.pki.rsa.generateKeyPair({ bits: 2048 });
    function certificate(name, device) {
        const cert = forge.pki.createCertificate();
        cert.publicKey = key.publicKey;
        cert.serialNumber = name === 'author' ? '01' : '02';
        cert.validity.notBefore = new Date('2025-01-01');
        cert.validity.notAfter = new Date('2030-01-01');
        cert.setSubject([{ name: 'commonName', value: 'Synthetic CI only' }]);
        cert.setIssuer(cert.subject.attributes);
        cert.setExtensions([
            { name: 'subjectAltName', altNames: [{ type: 2, value: 'deviceid=' + device }] }
        ]);
        cert.sign(key.privateKey, forge.md.sha256.create());
        const p12 = forge.pkcs12.toPkcs12Asn1(key.privateKey, [cert], 'synthetic-ci-only', {
            algorithm: '3des'
        });
        fs.writeFileSync(
            path.join(certs, name + '.p12'),
            Buffer.from(forge.asn1.toDer(p12).getBytes(), 'binary')
        );
        return cert;
    }
    certificate('author', 'synthetic-device');
    const cert = certificate('distributor', 'synthetic-device');
    fs.writeFileSync(path.join(certs, 'author.pw'), 'synthetic-ci-only');
    fs.writeFileSync(
        path.join(certs, 'device-profile.xml'),
        '<synthetic-no-samsung-authorization/>'
    );
    const id = path.join(base, 'device-id');
    fs.writeFileSync(id, 'synthetic-device');
    return { base, output, certs, id, cert, args: [output, certs, id] };
}
test('startup lifecycle and status authorization boundaries', () => {
    const r = run('tests/test_startup.cjs');
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /eight status/);
});
test('TV source and widget scripts remain compatible with ECMAScript 2019', () => {
    const folder = path.join(root, 'startup/service');
    for (const file of fs.readdirSync(folder).filter((n) => n.endsWith('.js')))
        acorn.parse(fs.readFileSync(path.join(folder, file), 'utf8'), {
            ecmaVersion: 2019,
            sourceType: 'script'
        });
    const html = fs.readFileSync(path.join(root, 'startup/index.html'), 'utf8');
    assert(html.includes('src="app.js"'));
    assert(html.includes('href="app.css"'));
    const app = fs.readFileSync(path.join(root, 'startup/app.js'), 'utf8');
    acorn.parse(app, { ecmaVersion: 2019 });
    assert(app.includes('__STATUS_KEY__'));
    assert(!fs.existsSync(path.join(folder, 'status-key.json')));
});
test('synthetic package signs actual widget source and verifies signatures', async (t) => {
    const f = fixture(t),
        r = run('scripts/sign-startup.cjs', f.args);
    assert.equal(r.status, 0, r.stderr);
    const zip = await JSZip.loadAsync(fs.readFileSync(path.join(f.output, 'startup.wgt')));
    for (const name of ['author-signature.xml', 'signature1.xml']) {
        const doc = new DOMParser().parseFromString(
            await zip.file(name).async('string'),
            'text/xml'
        );
        const signed = doc.getElementsByTagName('SignedInfo')[0],
            value = doc.getElementsByTagName('SignatureValue')[0].textContent.replace(/\s/g, '');
        const canonical = new Canonicalization().process(signed, {
            defaultNsForPrefix: { ds: 'http://www.w3.org/2000/09/xmldsig#' }
        });
        assert(
            crypto.verify(
                'RSA-SHA512',
                Buffer.from(canonical),
                forge.pki.publicKeyToPem(f.cert.publicKey),
                Buffer.from(value, 'base64')
            )
        );
        for (const ref of Array.from(doc.getElementsByTagName('Reference'))) {
            const uri = ref.getAttribute('URI');
            if (uri === '#prop') continue;
            const file = zip.file(decodeURIComponent(uri));
            assert(file, 'Every signed reference must exist');
            const expected = ref
                .getElementsByTagName('DigestValue')[0]
                .textContent.replace(/\s/g, '');
            assert.equal(
                crypto
                    .createHash('sha512')
                    .update(await file.async('nodebuffer'))
                    .digest('base64'),
                expected
            );
        }
    }
    const manifest = JSON.parse(fs.readFileSync(path.join(f.output, 'package.json')));
    assert.equal(
        manifest.device_sha256,
        crypto.createHash('sha256').update('synthetic-device').digest('hex')
    );
    for (const [file, digest] of Object.entries(manifest.files))
        assert.equal(
            crypto
                .createHash('sha256')
                .update(fs.readFileSync(path.join(f.output, file)))
                .digest('hex'),
            digest
        );
});
test('RSA verification rejects extra nested DigestAlgorithm elements (GHSA-86w9-cpqp-85rv)', () => {
    const transitiveRequire = require('module').createRequire(require.resolve('tizen'));
    assert.equal(transitiveRequire.resolve('node-forge'), require.resolve('node-forge'));
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicExponent: 3
    });
    const key = forge.pki.publicKeyFromPem(publicKey.export({ type: 'spki', format: 'pem' }));
    const digest = crypto.createHash('sha256').update('nested DigestAlgorithm regression').digest();
    const asn1 = forge.asn1;
    const element = (type, constructed, value) =>
        asn1.create(asn1.Class.UNIVERSAL, type, constructed, value);
    const oid = element(asn1.Type.OID, false, asn1.oidToDer(forge.oids.sha256).getBytes());
    const nil = element(asn1.Type.NULL, false, '');
    const garbage = element(asn1.Type.OCTETSTRING, false, 'unconsumed bytes');
    function signature(children, extraOuter = []) {
        const info = element(asn1.Type.SEQUENCE, true, [
            element(asn1.Type.SEQUENCE, true, children),
            element(asn1.Type.OCTETSTRING, false, digest.toString('binary')),
            ...extraOuter
        ]);
        const der = Buffer.from(asn1.toDer(info).getBytes(), 'binary');
        const encoded = Buffer.concat([
            Buffer.from([0, 1]), Buffer.alloc(256 - der.length - 3, 0xff),
            Buffer.from([0]), der
        ]);
        // Construct controlled signed encodings to exercise verification, including
        // malformed encodings that the vulnerable version incorrectly accepts.
        return crypto.privateEncrypt({ key: privateKey, padding: crypto.constants.RSA_NO_PADDING }, encoded)
            .toString('binary');
    }
    for (const valid of [[oid], [oid, nil]]) {
        assert.equal(key.verify(digest.toString('binary'), signature(valid)), true);
    }
    for (const invalid of [[oid, nil, garbage], [oid, garbage], [oid, nil, nil]]) {
        assert.throws(() => key.verify(digest.toString('binary'), signature(invalid)), /DigestInfo/);
    }
    assert.throws(() => key.verify(digest.toString('binary'), signature([oid, nil], [garbage])), /DigestInfo/);
});

test('startup signing does not call forge RSA verification (GHSA-86w9-cpqp-85rv)', (t) => {
    const f = fixture(t);
    const preload = path.join(f.base, 'forbid-forge-verification.cjs');
    fs.writeFileSync(preload, `
        const forge = require(${JSON.stringify(require.resolve('node-forge'))});
        const original = forge.pki.rsa.setPublicKey;
        forge.pki.setRsaPublicKey = forge.pki.rsa.setPublicKey = function (...args) {
            const key = original(...args);
            key.verify = () => { throw Error('Vulnerable forge RSA verification reached'); };
            return key;
        };
    `);
    const result = spawnSync(process.execPath,
        ['--require', preload, path.join(root, 'scripts/sign-startup.cjs'), ...f.args],
        { encoding: 'utf8', timeout: 30000, env: { ...process.env, NODE_OPTIONS: '' } });
    assert.equal(result.status, 0, result.stderr);
    assert(fs.existsSync(path.join(f.output, 'startup.wgt')));
});
test('certificate for a different TV is rejected without output', (t) => {
    const f = fixture(t);
    fs.writeFileSync(f.id, 'another-device');
    const r = run('scripts/sign-startup.cjs', f.args);
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /does not authorize/);
    assert(!fs.existsSync(path.join(f.output, 'startup.wgt')));
});
test('widget symlinks are rejected before package creation', (t) => {
    const f = fixture(t);
    fs.symlinkSync(path.join(f.base, 'device-id'), path.join(f.output, 'widget/private-link'));
    const r = run('scripts/sign-startup.cjs', f.args);
    assert.notEqual(r.status, 0);
    assert(!fs.existsSync(path.join(f.output, 'startup.wgt')));
});
test('root-agent accepts authenticated root identity and rejects forgery/non-root', () => {
    const { RootAgentServer } = require('../startup/service/root-agent.js');
    for (const mode of ['root', 'forged', 'non-root']) {
        const server = new RootAgentServer({ secret: Buffer.alloc(32, 7) });
        assert.equal(server.bindHost, '127.0.0.1');
        const socket = new EventEmitter();
        let hello;
        socket.write = (data) => {
            hello = data;
        };
        socket.destroy = () => {
            socket.destroyed = true;
            socket.emit('close');
        };
        server._handle(socket);
        const nonce = Buffer.from(hello.trim().split('\t')[1], 'hex');
        const payload = 'AUTH\t123\t' + (mode === 'non-root' ? '1' : '0') + '\t0\t0\t0\tffffffff\t';
        const mac =
            mode === 'forged'
                ? '0'.repeat(64)
                : crypto
                      .createHmac('sha256', server.secret)
                      .update(nonce)
                      .update('\x00')
                      .update(payload)
                      .digest('hex');
        socket.emit('data', Buffer.from(payload + '\t' + mac + '\n'));
        if (mode === 'root') assert(server._conn);
        else assert(socket.destroyed);
        server.close();
        if (!socket.destroyed) socket.destroy();
    }
});
