# Stage 1: Build frontend (always runs on the build host — output is static)
FROM --platform=$BUILDPLATFORM node:26-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.14-slim

LABEL org.opencontainers.image.source="https://github.com/uprightbass360/automatic-ripping-machine-ui"
LABEL org.opencontainers.image.license="MIT"
LABEL org.opencontainers.image.description="Replacement dashboard for ARM (SvelteKit + FastAPI)"

WORKDIR /app

COPY requirements.txt .
COPY --from=contracts . components/contracts
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION .
COPY backend/ backend/

# Copy built frontend into place for static serving
COPY --from=frontend-build /app/frontend/build frontend/build

# Stamp VERSION with the actual build identity so the running image can
# distinguish release / RC / dev builds in the Settings -> Versions panel.
# - Release workflow passes IMAGE_TAG=<version>           -> e.g. 17.3.0
# - RC workflow passes      IMAGE_TAG=<version>-rc        -> e.g. 17.3.0-rc
# - Local docker compose build with no arg                -> e.g. 17.3.0-dev
ARG IMAGE_TAG=
RUN if [ -n "$IMAGE_TAG" ]; then \
        echo "$IMAGE_TAG" > /app/VERSION; \
    else \
        echo "$(cat /app/VERSION)-dev" > /app/VERSION; \
    fi

EXPOSE 8888

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
