// Exercise the same polling module that the Flask-rendered log page loads.
const test = require('node:test');
const assert = require('node:assert/strict');
const startLogReader = require('../../arm/ui/static/js/logReader.js');

test('polling preserves partial lines and resets display on rotation', async () => {
    const encoder = new TextEncoder();
    const firstLine = encoder.encode('ARM: café\n');
    const parts = [firstLine.slice(0, 2), firstLine.slice(2, 9), firstLine.slice(9)];
    const responses = [];
    let offset = 0;
    for (const data of parts) {
        responses.push({data, start: offset, next: offset + data.length, id: 'first'});
        offset += data.length;
    }
    responses.push({data: encoder.encode('ARM: replacement\n'), start: 0, next: 17, id: 'second'});
    const requests = [];
    const timers = [];
    const output = {
        textContent: '',
        appendChild: function (node) { this.textContent += node.textContent; }
    };
    startLogReader({
        mode: 'armcat',
        url: '/logreader?logfile=page-test.log&mode=full',
        output,
        document: {getElementById: () => output, createTextNode: text => ({textContent: text})},
        setTimeout: (callback, delay) => timers.push({callback, delay}),
        fetch: async url => {
            requests.push(url);
            const response = responses.shift();
            assert.ok(response);
            const headers = {'X-Log-Start': String(response.start), 'X-Log-Offset': String(response.next),
                'X-Log-Id': response.id};
            return {ok: true, headers: {get: key => headers[key]},
                arrayBuffer: async () => response.data.buffer.slice(response.data.byteOffset,
                    response.data.byteOffset + response.data.byteLength)};
        }
    });
    async function nextPoll() {
        await new Promise(setImmediate);
        const timer = timers.shift();
        assert.equal(timer.delay, 2000, 'a successful poll schedules the normal interval');
        timer.callback();
    }
    await nextPoll();
    assert.equal(output.textContent, '');
    await nextPoll();
    await new Promise(setImmediate);
    assert.equal(output.textContent, 'ARM: café\n');
    await nextPoll();
    await new Promise(setImmediate);
    assert.equal(output.textContent, 'ARM: replacement\n');
    assert.equal(requests.length, 4);
    assert.ok(requests.every(url => url.includes('mode=full')));
    assert.ok(requests[1].includes('offset=2&file_id=first'));
});
