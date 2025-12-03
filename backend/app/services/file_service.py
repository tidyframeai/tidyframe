"""
File processing service for handling uploads and identifying name columns
"""

import hashlib
import os
import uuid
from typing import Dict, List, Tuple

import magic
import pandas as pd
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class FileService:
    """Service for file operations and analysis"""

    def __init__(self):
        # Ensure directories exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)

    def save_uploaded_file(
        self, file_content: bytes, original_filename: str
    ) -> Tuple[str, str]:
        """
        Save uploaded file to disk

        Args:
            file_content: File content as bytes
            original_filename: Original filename from upload

        Returns:
            Tuple of (file_path, generated_filename)
        """

        # Generate unique filename
        file_extension = os.path.splitext(original_filename)[1].lower()
        generated_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, generated_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(
            "file_saved",
            original_filename=original_filename,
            file_path=file_path,
            size=len(file_content),
        )

        return file_path, generated_filename

    def identify_name_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Identify columns that likely contain names

        Args:
            df: DataFrame to analyze

        Returns:
            List of column names that likely contain names
        """

        name_columns = []

        # Required name column patterns (case insensitive)
        # ONLY accept 'name' and 'parse_string' - no other patterns
        name_patterns = ["name", "parse_string"]

        for column in df.columns:
            column_lower = column.lower().strip()

            # Check exact matches and partial matches
            for pattern in name_patterns:
                if pattern in column_lower:
                    name_columns.append(column)
                    break

        # If no obvious name columns found, try to identify by content
        if not name_columns:
            name_columns = self._identify_by_content(df)

        return name_columns

    def _identify_by_content(self, df: pd.DataFrame) -> List[str]:
        """
        Identify name columns by analyzing content patterns

        Args:
            df: DataFrame to analyze

        Returns:
            List of probable name columns
        """

        candidate_columns = []

        # Only consider string-like columns
        string_columns = df.select_dtypes(include=["object"]).columns

        for column in string_columns:
            # Skip if too many nulls
            non_null_count = df[column].notna().sum()
            if non_null_count < len(df) * 0.5:  # Less than 50% filled
                continue

            # Sample some non-null values
            sample_values = df[column].dropna().head(20).tolist()

            name_score = self._calculate_name_score(sample_values)

            if name_score > 0.3:  # Threshold for likely name content
                candidate_columns.append((column, name_score))

        # Sort by score and return top candidates
        candidate_columns.sort(key=lambda x: x[1], reverse=True)

        # Return up to 3 best candidates
        return [col[0] for col in candidate_columns[:3]]

    def _calculate_name_score(self, sample_values: List[str]) -> float:
        """
        Calculate likelihood that values are names

        Args:
            sample_values: List of sample values from column

        Returns:
            Score between 0 and 1 (higher = more likely to be names)
        """

        if not sample_values:
            return 0.0

        score = 0.0
        total_values = len(sample_values)

        for value in sample_values:
            if not isinstance(value, str):
                continue

            value = value.strip()
            if not value:
                continue

            # Check various name indicators
            words = value.split()

            # Names typically have 1-4 words
            if 1 <= len(words) <= 4:
                score += 0.2

            # Check for title prefixes
            titles = ["mr", "mrs", "ms", "dr", "prof", "rev", "hon"]
            if words and words[0].lower().rstrip(".") in titles:
                score += 0.3

            # Check for common suffixes
            suffixes = ["jr", "sr", "ii", "iii", "iv"]
            if words and words[-1].lower().rstrip(".") in suffixes:
                score += 0.2

            # Check for company indicators (negative score)
            company_words = ["llc", "inc", "corp", "ltd", "co", "company"]
            if any(word.lower() in company_words for word in words):
                score += 0.1  # Still counts as entity name

            # Check for trust indicators
            trust_words = ["trust", "estate"]
            if any(word.lower() in trust_words for word in words):
                score += 0.1

            # Names usually start with capital letters
            if all(word[0].isupper() for word in words if word):
                score += 0.1

            # Check for all caps (less likely to be personal names)
            if value.isupper():
                score -= 0.1

        return min(1.0, score / total_values)

    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """
        Get information about a file

        Args:
            file_path: Path to file

        Returns:
            Dict with file information
        """

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file stats
        stat = os.stat(file_path)

        # Get MIME type
        mime_type = magic.from_file(file_path, mime=True)

        # Calculate file hash for integrity check
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        return {
            "file_path": file_path,
            "file_size": stat.st_size,
            "mime_type": mime_type,
            "file_hash": file_hash,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
        }

    def preview_file(self, file_path: str, rows: int = 5) -> Dict[str, any]:
        """
        Preview file content

        Args:
            file_path: Path to file
            rows: Number of rows to preview

        Returns:
            Dict with preview data
        """

        try:
            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension == ".csv":
                from app.utils.file_utils import detect_encoding

                encoding = detect_encoding(file_path)
                df = pd.read_csv(file_path, encoding=encoding, nrows=rows)
            elif file_extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path, nrows=rows)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Identify potential name columns
            name_columns = self.identify_name_columns(df)

            return {
                "columns": list(df.columns),
                "data": df.to_dict("records"),
                "row_count": len(df),
                "name_columns": name_columns,
                "dtypes": df.dtypes.to_dict(),
            }

        except Exception as e:
            logger.error("file_preview_failed", file_path=file_path, error=str(e))
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete file safely

        Args:
            file_path: Path to file to delete

        Returns:
            True if successful
        """

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("file_deleted", file_path=file_path)
                return True
            return False
        except Exception as e:
            logger.error("file_deletion_failed", file_path=file_path, error=str(e))
            return False

    def cleanup_old_files(self, directory: str, max_age_hours: int = 24) -> int:
        """
        Clean up old files in directory

        Args:
            directory: Directory to clean
            max_age_hours: Maximum age in hours

        Returns:
            Number of files deleted
        """

        if not os.path.exists(directory):
            return 0

        import time

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)

                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(
                            "old_file_deleted",
                            file_path=file_path,
                            age_hours=file_age / 3600,
                        )
                    except Exception as e:
                        logger.error(
                            "old_file_deletion_failed",
                            file_path=file_path,
                            error=str(e),
                        )

        return deleted_count
