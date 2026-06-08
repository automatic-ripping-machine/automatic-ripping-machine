# arm-neu — integrated v3 stack

Monorepo home of the "neu" services, wired to build and run together.

## Layout
- `ripper/`     — canonical ripper (exposes `/api/v1/*`, port 8080)
- `ui/`         — SvelteKit + FastAPI BFF dashboard (port 8888)
- `transcoder/` — FastAPI transcoder + webhook receiver (port 5000)
- `contracts/`  — shared pydantic models (`arm-contracts`), consumed at build time
- `auth/`       — shared auth library (`arm-auth`), not yet wired into any service

Each service keeps its own `docker-compose.yml` for standalone dev. The files in THIS
directory are the integrated umbrella stack that builds every service locally.

## Requirements
- Docker Compose v2 with BuildKit: `export DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1`

## Shared libraries (contracts)
Services consume `contracts` via a BuildKit **named build context**. The umbrella files supply
it from the sibling subtree:
`build.additional_contexts.contracts: ./contracts`. The Dockerfiles are identical to the
standalone repos (which supply the same context from their `components/contracts` submodule),
so subtree syncs never diverge.

## Run
```bash
cp .env.example .env        # then edit paths/secrets
docker compose up -d --build
```

### Variants (compose overlays)
| Goal | Command |
|------|---------|
| GPU transcoding | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build` |
| NFS media guard | `docker compose -f docker-compose.yml -f docker-compose.nfs.yml up -d --build` |
| Local dev (hot reload) | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` |
| Ripper only (no transcoder) | `cp .env.ripper-only.example .env && docker compose -f docker-compose.ripper-only.yml -f docker-compose.nfs.yml up -d --build` |
| Remote transcoder | `cp .env.remote-transcoder.example .env && docker compose -f docker-compose.remote-transcoder.yml -f docker-compose.nfs.yml up -d --build` |

## Status
Structure + buildability only. A verified end-to-end run (optical hardware, base images, media)
is a follow-up. The legacy root stack (`../docker-compose.yml`, `../Dockerfile-UI`) is untouched
and still usable independently.
