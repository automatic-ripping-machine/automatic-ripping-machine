# ARM-v3 Devtools Cost Analysis

Generated 2026-09-02. The figures here are measurements from the sweep that
produced the other three reports in this directory, plus arithmetic on those
measurements at the stated token rates. Nothing else is asserted.

The tool list the MCP advertises - 76 tools - measures 23,355 characters of
tool definitions, roughly 5,838 tokens, and it rides in every session's
context whether the tools are used or not. At $3 per million tokens that is
$0.018 per session; at $15 per million tokens, $0.088.

The four structural index queries behind the dead-code, hotspot and
untested-symbol findings returned 33,328 characters in total, roughly 8,332
tokens. At $3 per million tokens that is $0.025; at $15 per million tokens,
$0.125.

Those four queries replaced reading the analysis corpus directly. The
corpus - arm/ and scripts/, excluding tests - is 127 files, 14,670 lines,
540,103 characters, roughly 135,000 tokens. 8,332 tokens is 94% less than
that: $0.025 against $0.405 at $3 per million tokens, and $0.125 against
$2.025 at $15 per million tokens.

The output caps are properties of the code, not projections. Log reads are
truncated. External MCP server results are cut at 20,000 characters. Index
queries return compact encoded tables instead of file contents. The mutation
audit classifies every tool read_only, mutating or destructive, and
destructive tools require dry_run, so no call has to be re-run to learn what
it would do.
