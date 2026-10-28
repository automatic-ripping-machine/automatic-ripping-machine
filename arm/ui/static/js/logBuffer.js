/* Keep byte decoding and ARM-only line filtering across successive log polls. */
(function (root) {
    'use strict';
    function createLogBuffer(armOnly) {
        let decoder = new TextDecoder('utf-8');
        let pending = '';
        return {
            reset: function () {
                decoder = new TextDecoder('utf-8');
                pending = '';
            },
            append: function (bytes) {
                const text = decoder.decode(bytes, {stream: true});
                if (!armOnly) { return text; }
                const lines = (pending + text).split('\n');
                pending = lines.pop();
                return lines.filter(function (line) { return line.includes('ARM:'); })
                    .map(function (line) { return line + '\n'; }).join('');
            }
        };
    }
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = createLogBuffer;
    } else {
        root.createLogBuffer = createLogBuffer;
    }
}(typeof window === 'undefined' ? globalThis : window));
