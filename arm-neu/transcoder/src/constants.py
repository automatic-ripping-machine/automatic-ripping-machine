"""
Constants for ARM Transcoder
"""

# Timing constants
STABILIZE_CHECK_INTERVAL = 5  # seconds between file size checks
PROGRESS_UPDATE_THRESHOLD = 5.0  # percent change required to update DB
PROGRESS_UPDATE_MIN_INTERVAL = 10  # minimum seconds between DB updates
SHUTDOWN_TIMEOUT = 300  # seconds to wait for graceful shutdown
WORKER_POLL_TIMEOUT = 5.0  # seconds to wait for queue job

# FFmpeg/HandBrake constants
NVENC_PRESET_DEFAULT = "p4"  # NVENC preset (p1=fastest, p7=slowest)
FFMPEG_TIMEOUT = 36000  # 10 hours max for any single file
HANDBRAKE_TIMEOUT = 36000  # 10 hours max for any single file

# Validation constants
# Webhook body cap is a sanity guard against obvious garbage, not a gate on
# legitimate payloads. A 4K Blu-ray with 70+ titles ships ~12KB of typed
# track metadata under WebhookPayload.tracks; 64KB headroom keeps that
# working without enabling a useful denial-of-service vector (the sender is
# already authenticated by X-Webhook-Secret).
MAX_WEBHOOK_PAYLOAD_SIZE = 64 * 1024  # 64KB
MAX_TITLE_LENGTH = 500
MAX_BODY_LENGTH = 2000
MAX_PATH_LENGTH = 1000
MAX_JOB_ID_LENGTH = 50
MAX_RETRY_COUNT = 3

# Disk space constants
MINIMUM_FREE_SPACE_GB = 10
TRANSCODE_SPACE_MULTIPLIER = 0.6  # Estimate: output = input * 0.6

# Rate limiting
WEBHOOK_RATE_LIMIT = "10/minute"
API_RATE_LIMIT = "60/minute"

# Valid audio encoders
VALID_AUDIO_ENCODERS = [
    "copy",
    "aac",
    "ac3",
    "eac3",
    "flac",
    "mp3",
]

# Audio file extensions (audio CD rips)
AUDIO_FILE_EXTENSIONS = {".flac", ".mp3", ".ogg", ".wav", ".m4a", ".wma", ".aac", ".alac"}

# Valid subtitle modes
VALID_SUBTITLE_MODES = ["all", "none", "first"]
