// Run with: node --test test/unittest/test_log_buffer.js
const test = require('node:test');
const assert = require('node:assert/strict');
const createLogBuffer = require('../../arm/ui/static/js/logBuffer.js');
const encode = value => new TextEncoder().encode(value);

test('ARM marker and line text can arrive across different polls', () => {
    const buffer = createLogBuffer(true);
    assert.equal(buffer.append(encode('noise\nAR')), '');
    assert.equal(buffer.append(encode('M: message')), '');
    assert.equal(buffer.append(encode(' continued\nplain\nARM: next\n')),
        'ARM: message continued\nARM: next\n');
});

test('a line larger than the server limit is preserved without repeating bytes', () => {
    const buffer = createLogBuffer(true);
    const line = 'ARM: ' + 'x'.repeat(2 * 1024 * 1024) + '\n';
    const bytes = encode(line);
    let result = '';
    for (let offset = 0; offset < bytes.length; offset += 1024 * 1024) {
        result += buffer.append(bytes.slice(offset, offset + 1024 * 1024));
    }
    assert.equal(result, line);
});

test('UTF-8 characters split across polls decode correctly in both modes', () => {
    for (const armOnly of [true, false]) {
        const buffer = createLogBuffer(armOnly);
        const line = 'ARM: café 💿\n';
        let result = '';
        for (const byte of encode(line)) { result += buffer.append(Uint8Array.of(byte)); }
        assert.equal(result, line);
    }
});

test('rotation clears pending line text and incomplete UTF-8', () => {
    const buffer = createLogBuffer(true);
    buffer.append(encode('ARM: old partial'));
    buffer.reset();
    assert.equal(buffer.append(encode('plain\nARM: replacement\n')), 'ARM: replacement\n');
    const full = createLogBuffer(false);
    assert.equal(full.append(Uint8Array.of(0xc3)), '');
    full.reset();
    assert.equal(full.append(encode('new\n')), 'new\n');
});
