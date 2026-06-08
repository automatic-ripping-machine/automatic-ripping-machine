"""Dump the FastAPI app's OpenAPI schema to stdout.

Used by scripts/codegen.sh as the upstream of the TypeScript codegen
pipeline. Imports the app directly rather than running a live HTTP
server so it works in CI without a uvicorn process.
"""
import json
import sys

from backend.main import app


def main() -> None:
    sys.stdout.write(json.dumps(app.openapi(), indent=2))


if __name__ == "__main__":
    main()
