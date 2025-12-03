"""
File utilities for validation and processing
"""

import os

import chardet
import magic
import structlog

from app.core.config import settings

logger = structlog.get_logger()


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding

    Args:
        file_path: Path to file

    Returns:
        Detected encoding or 'utf-8' as fallback
    """

    try:
        with open(file_path, "rb") as f:
            # Read first 100KB for detection
            sample = f.read(100000)

        result = chardet.detect(sample)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)

        # Don't force utf-8 for ASCII since it's compatible
        # and often correct for simple files
        if confidence < 0.5 and encoding not in ["ascii", "utf-8"]:
            encoding = "utf-8"

        logger.info(
            "encoding_detected",
            file_path=file_path,
            encoding=encoding,
            confidence=result.get("confidence"),
        )

        return encoding

    except Exception as e:
        logger.warning("encoding_detection_failed", file_path=file_path, error=str(e))
        return "utf-8"


def validate_file(file_path: str) -> bool:
    """
    Validate uploaded file

    Args:
        file_path: Path to file

    Returns:
        True if valid

    Raises:
        ValueError: If file is invalid
    """

    if not os.path.exists(file_path):
        raise ValueError("File not found")

    # Check file size
    file_size = os.path.getsize(file_path)
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)"
        )

    if file_size == 0:
        raise ValueError("File is empty")

    # Check file extension
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension not in settings.ALLOWED_FILE_TYPES:
        raise ValueError(f"File type not allowed: {file_extension}")

    # Check MIME type using python-magic
    try:
        mime_type = magic.from_file(file_path, mime=True)

        # Map extensions to expected MIME types
        expected_mimes = {
            ".csv": ["text/csv", "text/plain", "application/csv"],
            ".xlsx": [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ],
            ".xls": ["application/vnd.ms-excel", "application/excel"],
            ".txt": ["text/plain", "text/csv"],
        }

        if file_extension in expected_mimes:
            if mime_type not in expected_mimes[file_extension]:
                logger.warning(
                    "mime_type_mismatch",
                    file_path=file_path,
                    extension=file_extension,
                    mime_type=mime_type,
                )
                # Don't fail completely, but log warning

    except Exception as e:
        logger.warning("mime_type_check_failed", file_path=file_path, error=str(e))

    # Virus scanning (if enabled)
    if settings.VIRUS_SCANNING_ENABLED:
        scan_result = scan_for_viruses(file_path)
        if not scan_result:
            raise ValueError("File failed virus scan")

    return True


def scan_for_viruses(file_path: str) -> bool:
    """
    Scan file for viruses using ClamAV

    Args:
        file_path: Path to file

    Returns:
        True if clean, False if infected
    """

    try:
        # Try to use pyclamd if available
        import pyclamd

        cd = pyclamd.ClamdUnixSocket()
        # cd = pyclamd.ClamdNetworkSocket()  # Alternative for network socket

        if cd.ping():
            scan_result = cd.scan_file(file_path)

            if scan_result is None:
                # No threats found
                logger.info("virus_scan_clean", file_path=file_path)
                return True
            else:
                # Threat found
                logger.warning(
                    "virus_scan_threat_found", file_path=file_path, threats=scan_result
                )
                return False
        else:
            logger.warning("clamav_not_available")
            return True  # Allow file if scanner not available

    except ImportError:
        logger.info("pyclamd_not_installed")
        return True  # Allow file if scanner not installed

    except Exception as e:
        logger.error("virus_scan_failed", file_path=file_path, error=str(e))
        return True  # Allow file if scan fails (avoid blocking legitimate files)


def get_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    Calculate file hash

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('md5', 'sha256', etc.)

    Returns:
        Hex digest of file hash
    """

    import hashlib

    hash_func = getattr(hashlib, algorithm)()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def safe_filename(filename: str) -> str:
    """
    Create safe filename by removing dangerous characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """

    import re

    # Remove path components
    filename = os.path.basename(filename)

    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove any null bytes
    filename = filename.replace("\x00", "")

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext

    # Ensure filename is not empty
    if not filename.strip():
        filename = "unnamed_file"

    return filename


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """

    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.1f} GB"
