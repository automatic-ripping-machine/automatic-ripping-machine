/* Bounded log polling, shared by the page and direct module tests. */
(function (root) {
    'use strict';
    const createBuffer = typeof module !== 'undefined' && module.exports
        ? require('./logBuffer.js') : root.createLogBuffer;

    function startLogReader(options) {
        const output = options.output;
        const document = options.document || root.document;
        const fetch = options.fetch || root.fetch.bind(root);
        const schedule = options.setTimeout || root.setTimeout.bind(root);
        const tail = options.mode === 'tail';
        const base = options.url;
        const buffer = createBuffer(options.mode === 'armcat');
        let offset = 0;
        let fileId = '';

        function poll() {
            fetch(base + '&offset=' + offset + '&file_id=' + encodeURIComponent(fileId),
                {cache: 'no-store', credentials: 'same-origin'})
                .then(function (response) {
                    if (!response.ok) { throw new Error(response.status); }
                    const next = Number.parseInt(response.headers.get('X-Log-Offset') || offset, 10);
                    const start = Number.parseInt(response.headers.get('X-Log-Start') || '0', 10);
                    const nextId = response.headers.get('X-Log-Id') || '';
                    return response.arrayBuffer().then(function (bytes) {
                        if (start !== offset || (fileId && fileId !== nextId)) {
                            output.textContent = '';
                            buffer.reset();
                        }
                        const text = buffer.append(bytes);
                        offset = next;
                        fileId = nextId;
                        if (text) {
                            output.appendChild(document.createTextNode(text));
                            if (tail) { root.scrollTo(0, document.body.scrollHeight); }
                        }
                        schedule(poll, bytes.byteLength >= 1048576 ? 50 : 2000);
                    });
                })
                .catch(function () { schedule(poll, 5000); });
        }
        poll();
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = startLogReader;
    } else {
        root.startLogReader = startLogReader;
    }
}(typeof window === 'undefined' ? globalThis : window));
