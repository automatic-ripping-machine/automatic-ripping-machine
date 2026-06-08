# ARM Configuration for arm-transcoder

Configuration files for integrating [Automatic Ripping Machine](https://github.com/automatic-ripping-machine/automatic-ripping-machine) with arm-transcoder.

## Files

| File | Purpose |
|------|---------|
| `arm.yaml` | ARM config overlay - disables built-in transcoding and sets up webhook |
| `notify_transcoder.sh` | Bash notification script for authenticated webhooks |

## Automated Setup

The quickest way to configure ARM is with the setup script. Run it on the ARM machine (or anywhere with access to ARM's config directory):

```bash
# Simple webhook (no authentication)
./scripts/setup-arm.sh \
  --url http://TRANSCODER_IP:5000/webhook/arm \
  --config /etc/arm/config

# Authenticated webhook (recommended)
./scripts/setup-arm.sh \
  --url http://TRANSCODER_IP:5000/webhook/arm \
  --config /etc/arm/config \
  --secret your-secret-here

# With Docker container restart
./scripts/setup-arm.sh \
  --url http://TRANSCODER_IP:5000/webhook/arm \
  --config /etc/arm/config \
  --secret your-secret-here \
  --restart
```

The script patches `arm.yaml` in place (idempotent, safe to re-run) and optionally deploys `notify_transcoder.sh` with your URL and secret baked in. It prints a test curl command when finished.

## Manual Setup

### 1. Shared Storage

Both machines need access to the same storage paths (via NFS, SMB/CIFS, or any shared mount):

```
ARM Ripper                                    Transcoder
─────────                                     ──────────
/home/arm/media/raw/        ←shared mount→    /data/raw/       (RAW_PATH)
/home/arm/media/completed/  ←shared mount→    /data/completed/  (COMPLETED_PATH)
```

On the ARM machine, export or mount these paths. On the transcoder, set `HOST_RAW_PATH` and `HOST_COMPLETED_PATH` in `.env` to point to the same shared storage.

### 2. ARM Configuration

Copy `arm.yaml` to your ARM container's config directory:

```bash
# If running ARM in Docker
docker cp arm.yaml arm:/etc/arm/config/arm.yaml

# Or mount it in your ARM docker-compose.yml:
#   volumes:
#     - ./config/arm/arm.yaml:/etc/arm/config/arm.yaml
```

Edit the file and replace `TRANSCODER_IP` with the actual IP or hostname of your transcoder machine:

```yaml
TRANSCODER_URL: "http://TRANSCODER_IP:5000/webhook/arm"
```

### 3. Authentication (Optional)

ARM's `TRANSCODER_URL` uses the Apprise library internally, which does not support custom HTTP headers. If you need webhook authentication (`WEBHOOK_SECRET`), use the bash script instead:

1. Copy `notify_transcoder.sh` to your ARM machine:
   ```bash
   docker cp notify_transcoder.sh arm:/home/arm/scripts/notify_transcoder.sh
   docker exec arm chmod +x /home/arm/scripts/notify_transcoder.sh
   ```

2. Edit the script and set your transcoder URL and secret:
   ```bash
   TRANSCODER_URL="http://TRANSCODER_IP:5000/webhook/arm"
   WEBHOOK_SECRET="your-secret-here"
   ```

3. Update `arm.yaml` to use the script instead of TRANSCODER_URL:
   ```yaml
   TRANSCODER_URL: ""
   BASH_SCRIPT: "/home/arm/scripts/notify_transcoder.sh"
   ```

4. Set the same secret in arm-transcoder's `.env`:
   ```
   WEBHOOK_SECRET=your-secret-here
   ```

### 4. Verify

After ripping a disc, check that the notification reaches arm-transcoder:

```bash
# Check transcoder logs
docker compose logs -f arm-transcoder

# Check job was created
curl http://TRANSCODER_IP:5000/jobs

# Manual test (simulates what ARM sends)
curl -X POST http://TRANSCODER_IP:5000/webhook/arm \
  -H "Content-Type: application/json" \
  -d '{"title": "ARM notification", "body": "Test Movie (2024) rip complete. Starting transcode.", "type": "info"}'
```

## How It Works

1. ARM rips the disc to MKV files in `RAW_PATH` (e.g., `/home/arm/media/raw/Movie Title (2024)/`)
2. With `SKIP_TRANSCODE: true`, ARM skips its built-in HandBrake step
3. ARM sends a notification via `TRANSCODER_URL` or `BASH_SCRIPT`
4. arm-transcoder receives the webhook, extracts the title, and queues a transcode job
5. The transcoder finds source files in `RAW_PATH/<title>/` and transcodes them to `COMPLETED_PATH/`
6. After successful transcode, source files are cleaned up (if `DELETE_SOURCE=true`)
