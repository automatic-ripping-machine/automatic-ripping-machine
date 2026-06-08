"""
Utility functions and validators for ARM Transcoder
"""

import logging
import re
import shutil
from pathlib import Path

from constants import (
    MINIMUM_FREE_SPACE_GB,
    TRANSCODE_SPACE_MULTIPLIER,
    VALID_AUDIO_ENCODERS,
    VALID_SUBTITLE_MODES,
)

logger = logging.getLogger(__name__)


class PathValidator:
    """Validates and sanitizes file paths to prevent traversal attacks."""

    def __init__(self, allowed_base_paths: list[str]):
        """
        Initialize validator with allowed base paths.

        Args:
            allowed_base_paths: List of absolute paths that are allowed
        """
        self.allowed_bases = [Path(p).resolve() for p in allowed_base_paths]

    def validate(self, path_str: str) -> Path:
        """
        Validate and resolve a path, ensuring it's within allowed directories.

        Args:
            path_str: Path string to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is invalid or outside allowed directories
        """
        if not path_str:
            raise ValueError("Path cannot be empty")

        # Remove any null bytes
        path_str = path_str.replace("\x00", "")

        # Check for obviously malicious patterns
        dangerous_patterns = ["../", "..\\", "~", "${", "$ENV"]
        for pattern in dangerous_patterns:
            if pattern in path_str:
                raise ValueError(f"Path contains dangerous pattern: {pattern}")

        try:
            path = Path(path_str)

            # Reject absolute paths from user input
            if path.is_absolute():
                raise ValueError("Absolute paths are not allowed")

            # Try to resolve against each allowed base
            for base in self.allowed_bases:
                try:
                    resolved = (base / path).resolve()

                    # Verify the resolved path is actually within the base
                    resolved.relative_to(base)

                    # Additional check: ensure no symlinks escape the base
                    if resolved.exists() and resolved.is_symlink():
                        target = resolved.readlink()
                        if target.is_absolute():
                            target.relative_to(base)

                    return resolved

                except (ValueError, OSError):
                    continue

            # If we get here, path doesn't resolve to any allowed base
            raise ValueError(
                f"Path '{path_str}' is not within allowed directories"
            )

        except Exception as e:
            logger.warning(f"Path validation failed for '{path_str}': {e}")
            raise ValueError(f"Invalid path: {e}")

    def validate_existing(self, path_str: str) -> Path:
        """
        Validate path and verify it exists.

        Args:
            path_str: Path string to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is invalid or doesn't exist
        """
        path = self.validate(path_str)

        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")

        return path


class CommandValidator:
    """Validates command arguments for subprocess calls."""

    @staticmethod
    def validate_audio_encoder(encoder: str) -> str:
        """
        Validate audio encoder name.

        Args:
            encoder: Encoder name to validate

        Returns:
            Validated encoder name

        Raises:
            ValueError: If encoder is invalid
        """
        if encoder not in VALID_AUDIO_ENCODERS:
            raise ValueError(
                f"Invalid audio encoder: {encoder}. "
                f"Valid options: {', '.join(VALID_AUDIO_ENCODERS)}"
            )
        return encoder

    @staticmethod
    def validate_subtitle_mode(mode: str) -> str:
        """
        Validate subtitle mode.

        Args:
            mode: Subtitle mode to validate

        Returns:
            Validated mode

        Raises:
            ValueError: If mode is invalid
        """
        if mode not in VALID_SUBTITLE_MODES:
            raise ValueError(
                f"Invalid subtitle mode: {mode}. "
                f"Valid options: {', '.join(VALID_SUBTITLE_MODES)}"
            )
        return mode

    @staticmethod
    def validate_preset_name(preset: str) -> str:
        """
        Validate HandBrake preset name.

        Args:
            preset: Preset name to validate

        Returns:
            Validated preset name

        Raises:
            ValueError: If preset contains invalid characters
        """
        # Allow alphanumeric, spaces, hyphens, underscores, and periods
        if not re.match(r"^[a-zA-Z0-9 \-_.]+$", preset):
            raise ValueError(
                f"Invalid preset name: {preset}. "
                "Only alphanumeric, spaces, hyphens, underscores, and periods allowed."
            )

        if len(preset) > 100:
            raise ValueError("Preset name too long (max 100 characters)")

        return preset


def get_disk_space_info(path: str) -> dict:
    """
    Get disk space information for a path.

    Args:
        path: Path to check

    Returns:
        Dict with total, used, free space in bytes
    """
    try:
        stat = shutil.disk_usage(path)
        return {
            "total_bytes": stat.total,
            "used_bytes": stat.used,
            "free_bytes": stat.free,
            "free_gb": stat.free / (1024**3),
        }
    except Exception as e:
        logger.error(f"Failed to get disk space for {path}: {e}")
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "free_gb": 0,
        }


def check_sufficient_disk_space(
    target_path: str,
    required_bytes: int,
    minimum_free_gb: float = MINIMUM_FREE_SPACE_GB,
) -> tuple[bool, str]:
    """
    Check if there's sufficient disk space for a transcode operation.

    Args:
        target_path: Path where output will be written
        required_bytes: Estimated bytes needed for output
        minimum_free_gb: Minimum free space to maintain (GB)

    Returns:
        Tuple of (sufficient: bool, message: str)
    """
    try:
        space_info = get_disk_space_info(target_path)
        free_gb = space_info["free_gb"]
        required_gb = required_bytes / (1024**3)

        if free_gb < minimum_free_gb:
            return (
                False,
                f"Insufficient disk space: {free_gb:.1f}GB free, "
                f"{minimum_free_gb}GB minimum required",
            )

        if required_bytes > space_info["free_bytes"]:
            return (
                False,
                f"Insufficient disk space: {free_gb:.1f}GB free, "
                f"{required_gb:.1f}GB required for transcode",
            )

        return (True, f"Sufficient space: {free_gb:.1f}GB free")

    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return (False, f"Error checking disk space: {e}")


def estimate_transcode_size(source_size: int) -> int:
    """
    Estimate output size for a transcode operation.

    Args:
        source_size: Size of source file in bytes

    Returns:
        Estimated output size in bytes
    """
    # Conservative estimate: assume output is 60% of input size
    return int(source_size * TRANSCODE_SPACE_MULTIPLIER)


def clean_title_for_filesystem(title: str) -> str:
    """
    Clean a title string for use as a filesystem path component.

    Args:
        title: Title string to clean

    Returns:
        Cleaned title safe for filesystem use
    """
    # Remove or replace characters not allowed in filesystems
    # Windows: < > : " / \ | ? *
    # Unix: only / is forbidden, but we're more restrictive for portability
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)

    # Replace multiple spaces with single space
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Trim whitespace
    cleaned = cleaned.strip()

    # Ensure not empty
    if not cleaned:
        cleaned = "untitled"

    # Limit length (255 is typical max filename, leave room for extensions)
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()

    return cleaned


def sanitize_log_message(message: str, sensitive_keys: list[str] = None) -> str:
    """
    Sanitize log messages to remove sensitive information.

    Args:
        message: Log message to sanitize
        sensitive_keys: List of sensitive keys to mask

    Returns:
        Sanitized message
    """
    if sensitive_keys is None:
        sensitive_keys = ["password", "secret", "token", "key", "api_key"]

    sanitized = message
    for key in sensitive_keys:
        # Match key=value or key: value patterns
        pattern = rf'{key}[=:]\s*["\']?([^"\'\s,}}]+)["\']?'
        sanitized = re.sub(pattern, f'{key}="***"', sanitized, flags=re.IGNORECASE)

    return sanitized
