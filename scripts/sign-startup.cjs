'use strict';
// Signing never falls back to an unsigned package or another TV's certificate.
process.umask(0o077);
const fs = require('fs'),
    path = require('path'),
    crypto = require('crypto');
const [output, certs, deviceFile] = process.argv.slice(2);
const req = require('module').createRequire(path.resolve(__dirname, '../package.json'));
const forge = req('node-forge'),
    JSZip = req('jszip'),
    Signature = req('tizen').Signature;
const password = fs.readFileSync(path.join(certs, 'author.pw'), 'utf8').trim();
function load(name) {
    return forge.pkcs12.pkcs12FromAsn1(
        forge.asn1.fromDer(fs.readFileSync(path.join(certs, name)).toString('binary')),
        false,
        password
    );
}
const distributor = load('distributor.p12'),
    device = fs.readFileSync(deviceFile, 'utf8').trim();
let covered = [];
for (const c of distributor.safeContents)
    for (const b of c.safeBags)
        if (b.cert) {
            const ext = b.cert.getExtension('subjectAltName');
            for (const n of (ext && ext.altNames) || []) {
                const m = /deviceid=(.+)$/.exec(n.value || '');
                if (m) covered.push(m[1]);
            }
        }
if (!device || !covered.includes(device))
    throw Error('Distributor certificate does not authorize the selected TV');
function collect(root, rel) {
    let files = [];
    for (const name of fs.readdirSync(path.join(root, rel)).sort()) {
        const next = path.join(rel, name);
        const stat = fs.lstatSync(path.join(root, next));
        if (stat.isSymbolicLink()) throw Error('Symlink in widget');
        if (stat.isDirectory()) files = files.concat(collect(root, next));
        else
            files.push({
                uri: encodeURIComponent(next.replace(/\\/g, '/')),
                data: fs.readFileSync(path.join(root, next))
            });
    }
    return files;
}
const digest = (data) => crypto.createHash('sha256').update(data).digest('hex');
(async () => {
    let files = collect(path.join(output, 'widget'), '');
    files = await new Signature('AuthorSignature', files).sign(load('author.p12'));
    files = await new Signature('DistributorSignature', files).sign(distributor);
    const zip = new JSZip();
    for (const f of files) zip.file(decodeURIComponent(f.uri), f.data);
    const data = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
    fs.writeFileSync(path.join(output, 'startup.wgt'), data);
    const profile = fs.readFileSync(path.join(certs, 'device-profile.xml'));
    fs.writeFileSync(path.join(output, 'device-profile.xml'), profile);
    fs.writeFileSync(
        path.join(output, 'package.json'),
        JSON.stringify(
            {
                version: 'v4',
                device_sha256: digest(device),
                files: { 'startup.wgt': digest(data), 'device-profile.xml': digest(profile) }
            },
            null,
            2
        )
    );
    console.log('Signed startup package; target device authorization verified.');
})().catch((e) => {
    console.error('Startup signing failed: ' + e.name);
    process.exitCode = 1;
});
