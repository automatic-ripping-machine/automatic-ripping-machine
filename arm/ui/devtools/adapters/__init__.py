"""
Adapters that isolate ARM internals from devtools services.

All ARM-version knowledge is concentrated in these adapters: log file
access, route rendering and state queries. Services import only from
these adapters, so a change in ARM's internals is fixed in one place.
"""
