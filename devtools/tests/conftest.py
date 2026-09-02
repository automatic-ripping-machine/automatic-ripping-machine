"""Pytest config for host-side devtools tests (run with the ARM .venv python)."""
import sys
from pathlib import Path

# devapi_mcp.py relies on sys.path[0] being devtools/ when run as a script;
# pytest from the repo root does not provide that, so add it explicitly.
sys.path.insert(0, str(Path(__file__).parent.parent))
