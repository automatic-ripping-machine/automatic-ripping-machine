# HandBrake CLI - pre-compiled, published by publish-handbrake.yml
# Default pinned to the current VERSION_HANDBRAKE; CI overrides via --build-arg.
ARG HANDBRAKE_TAG=1.10.2
FROM uprightbass360/arm-handbrake:${HANDBRAKE_TAG} AS handbrake

# ── Base runtime ──────────────────────────────────────────────────────
# Shared base with HandBrake + deps + app code.
# Add a GPU layer (Dockerfile.nvidia/intel/amd) for hardware encoding,
# or use this image directly for CPU-only (x265/x264) transcoding.
FROM ubuntu:24.04
LABEL org.opencontainers.image.source="https://github.com/uprightbass360/automatic-ripping-machine-transcoder"
LABEL org.opencontainers.image.license="MIT"
LABEL org.opencontainers.image.description="ARM Transcoder base — add a GPU layer (Dockerfile.nvidia/intel/amd) for hardware encoding"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg mediainfo curl vainfo gosu rsync \
    libva2 libva-drm2 libdrm2 \
    libass9 libbz2-1.0 libfontconfig1 libfreetype6 libfribidi0 \
    libharfbuzz0b libjansson4 liblzma5 libmp3lame0 libnuma1 \
    libogg0 libopus0 libsamplerate0 libspeex1 libtheora0 \
    libturbojpeg libvorbis0a libvorbisenc2 libxml2 zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=handbrake /HandBrakeCLI /usr/local/bin/HandBrakeCLI

# App user — defaults to UID 1000 / GID 1000 to match ARM's default identity.
# The entrypoint remaps UID/GID at runtime via TRANSCODER_UID/TRANSCODER_GID
# env vars (set automatically by docker-compose from ARM_UID/ARM_GID).
# ubuntu:24.04 ships a default 'ubuntu' user at 1000:1000 which we
# remove first so our UID/GID assignments are clean.
ARG TRANSCODER_UID=1000
ARG TRANSCODER_GID=1000
RUN (userdel -r ubuntu 2>/dev/null; groupdel ubuntu 2>/dev/null; true) \
    && groupadd -g ${TRANSCODER_GID} transcoder \
    && groupadd -f render \
    && useradd -m -s /bin/bash -u ${TRANSCODER_UID} -g transcoder transcoder \
    && usermod -aG video transcoder \
    && usermod -aG render transcoder

WORKDIR /app
COPY requirements.txt .
COPY --from=contracts . /app/components/contracts
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY src/ /app/
COPY VERSION /app/
RUN mkdir -p /data/raw /data/completed /data/work /data/db /data/logs \
    && chown -R transcoder:transcoder /data /app

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Stamp VERSION with the actual build identity so the running image can
# distinguish release / RC / dev builds in the Settings -> Versions panel.
# - Release workflow passes IMAGE_TAG=<version>           -> e.g. 17.4.0
# - RC workflow passes      IMAGE_TAG=<version>-rc        -> e.g. 17.4.0-rc
# - Local docker compose build with no arg                -> e.g. 17.4.0-dev
# GPU layers (Dockerfile.nvidia/intel/amd) inherit this via FROM, so they
# do not need to set IMAGE_TAG themselves; vendor identity comes from the
# GPU_VENDOR env var the GPU layers set, surfaced via /system/stats.
ARG IMAGE_TAG=
RUN if [ -n "$IMAGE_TAG" ]; then \
        echo "$IMAGE_TAG" > /app/VERSION; \
    else \
        echo "$(cat /app/VERSION)-dev" > /app/VERSION; \
    fi \
    && cp /app/VERSION /etc/arm-transcoder-version

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
