"""
Optimized Celery worker for high-performance file processing and name parsing

Features:
- Intelligent batch processing with Gemini API optimization
- High-performance caching with duplicate detection
- Concurrent processing with cost optimization
- Smart payload filtering (only name/addressee data sent to API)
- Proper column ordering (processed columns FIRST, original columns LAST)
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
import redis
import structlog

from app.core.celery_app import celery_app
from app.models.job import JobStatus
from app.services.fallback_tracker import FallbackTracker
from app.services.file_service import FileService
from app.utils.file_utils import detect_encoding, validate_file
from app.utils.job_db import update_job_status

# Set up logger first
logger = structlog.get_logger()

# ARCHITECTURE FIX: Use the CORRECT service with hierarchical entity classification
try:
    from app.services.gemini_service import ConsolidatedGeminiService

    logger.info(
        "loaded_correct_gemini_service",
        service="ConsolidatedGeminiService",
        source="gemini_service.py",
        features="hierarchical_entity_classification",
    )
except ImportError as e:
    logger.error("failed_to_load_correct_gemini_service", error=str(e))
    ConsolidatedGeminiService = None


class OptimizedFileProcessorService:
    """High-performance file processing service with intelligent optimizations"""

    # Constants for data filtering
    SKIP_COLUMN_WORDS = ["category", "type", "status", "class", "code"]
    NON_NAME_VALUES = ["other", "n/a", "unknown", "none", "null", ""]

    def __init__(self):
        # CRITICAL: Validate correct service is loaded with entity classification
        if ConsolidatedGeminiService is None:
            logger.error(
                "critical_service_missing",
                error="ConsolidatedGeminiService not available",
                impact="Entity classification will fail",
            )
            self.batch_processor = None
        else:
            self.batch_processor = ConsolidatedGeminiService()

            # RUNTIME VALIDATION: Verify hierarchical prompt is available
            if hasattr(self.batch_processor, "prompts") and hasattr(
                self.batch_processor.prompts, "PROPERTY_OWNERSHIP_PROMPT"
            ):
                logger.info(
                    "service_validation_passed",
                    service="ConsolidatedGeminiService",
                    prompt_available=True,
                    entity_classification="enabled",
                )
            else:
                logger.error(
                    "service_validation_failed",
                    service="ConsolidatedGeminiService",
                    prompt_available=False,
                    entity_classification="disabled",
                    impact="0% entity classification accuracy",
                )

        self.file_service = FileService()
        self.fallback_tracker = FallbackTracker()

        # Performance settings
        self.chunk_size = 500  # Process in chunks for progress tracking
        self.enable_detailed_logging = True

    def extract_name_data_optimized(
        self, df: pd.DataFrame, name_columns: List[str]
    ) -> Tuple[List[str], List[int]]:
        """Extract ONLY name/addressee text - never send full row data to API"""
        name_texts = []
        row_indices = []

        for idx, row in df.iterrows():
            # CRITICAL: Only extract name/addressee text for API calls
            name_parts = []

            # Extract from identified name columns
            for col in name_columns:
                if pd.notna(row[col]) and str(row[col]).strip():
                    name_parts.append(str(row[col]).strip())

            # Also check for 'addressee' columns (but be smart about what we include)
            addressee_cols = [col for col in df.columns if "addressee" in col.lower()]
            for col in addressee_cols:
                # Skip if it's already in name_columns
                if col in name_columns:
                    continue

                # Skip metadata columns like "Addressee Category", "Addressee Type", etc.
                col_lower = col.lower()
                if any(skip_word in col_lower for skip_word in self.SKIP_COLUMN_WORDS):
                    continue

                # Check if this column has actual name data
                if pd.notna(row[col]) and str(row[col]).strip():
                    value = str(row[col]).strip()
                    # Skip non-name values
                    if value.lower() in self.NON_NAME_VALUES:
                        continue
                    # If it looks like a name, add it
                    name_parts.append(value)

            # Combine name parts intelligently
            combined_name = " ".join(name_parts).strip()

            # CRITICAL: Remove "Other" if it somehow got into the combined name
            combined_name = (
                combined_name.replace(" Other", "").replace("Other ", "").strip()
            )

            # CRITICAL: Remove single letters from the name string before processing
            # Split, filter out single letters, and rejoin
            name_tokens = combined_name.split()
            cleaned_tokens = [
                token for token in name_tokens if len(token.rstrip(".,")) > 1
            ]
            combined_name = " ".join(cleaned_tokens).strip()

            if combined_name:
                name_texts.append(combined_name)
            else:
                name_texts.append("")  # Empty name

            row_indices.append(idx)

        return name_texts, row_indices

    async def process_file_optimized(
        self,
        job_id: str,
        file_path: str,
        user_id: str = None,
        parsing_config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Process file with maximum speed and cost efficiency"""
        start_time = time.time()
        logger.info("optimized_processing_started", job_id=job_id, file_path=file_path)

        try:
            # Update job status
            update_job_status(job_id, JobStatus.PROCESSING)
            set_job_progress_sync(job_id, 5)

            # Load and validate file
            df = await self._load_file_async(file_path)
            total_rows = len(df)
            logger.info("file_loaded", rows=total_rows)

            # Validate row count
            from app.core.config import settings

            if total_rows > settings.MAX_ROWS_PER_FILE:
                raise ValueError(
                    f"File too large: {total_rows} rows (max: {settings.MAX_ROWS_PER_FILE})"
                )

            set_job_progress_sync(job_id, 15)

            # Identify name columns with config support
            name_columns = self._identify_name_columns_with_config(df, parsing_config)
            if not name_columns:
                raise ValueError(
                    "No name columns found in file. Please specify a column to process."
                )

            logger.info("name_columns_identified", columns=name_columns)
            set_job_progress_sync(job_id, 25)

            # Extract ONLY name data for API processing (critical optimization)
            name_texts, row_indices = self.extract_name_data_optimized(df, name_columns)

            set_job_progress_sync(job_id, 35)

            # Process names with optimized batch processing
            def progress_callback(processed: int, total: int):
                progress = 35 + (processed / total) * 50  # 35% to 85%
                set_job_progress_sync(job_id, int(progress))

            # Check if batch processor is available before using it
            if self.batch_processor is None:
                logger.error("batch_processor_unavailable", job_id=job_id)
                raise RuntimeError(
                    "Gemini service is not available. Cannot process names."
                )

            batch_result = await self.batch_processor.parse_names_batch(
                name_texts, progress_callback=progress_callback
            )

            set_job_progress_sync(job_id, 85)

            # Convert ParsedName objects to dictionaries for compatibility
            result_dicts = []
            for r in batch_result.results:
                try:
                    if hasattr(r, "to_dict") and callable(getattr(r, "to_dict")):
                        result_dict = r.to_dict()
                        # Ensure all required fields are present
                        result_dict.setdefault("warnings", [])
                        result_dict.setdefault("original_text", "")
                        result_dicts.append(result_dict)
                    elif hasattr(r, "__dict__"):
                        # If it's a dataclass or similar object, convert to dict
                        result_dict = {}
                        for key in [
                            "first_name",
                            "last_name",
                            "entity_type",
                            "gender",
                            "gender_confidence",
                            "parsing_confidence",
                            "parsing_method",
                            "fallback_reason",
                            "warnings",
                            "original_text",
                        ]:
                            if key == "warnings":
                                result_dict[key] = getattr(r, key, [])
                            else:
                                result_dict[key] = getattr(r, key, "")
                        result_dicts.append(result_dict)
                    elif isinstance(r, dict):
                        # Ensure dict has all required fields
                        r.setdefault("warnings", [])
                        r.setdefault("original_text", "")
                        result_dicts.append(r)
                    else:
                        # Fallback for unknown types
                        logger.warning(
                            "unknown_result_type", result_type=type(r).__name__
                        )
                        result_dicts.append(
                            {
                                "first_name": "",
                                "last_name": "",
                                "entity_type": "unknown",
                                "gender": "unknown",
                                "gender_confidence": 0.0,
                                "parsing_confidence": 0.0,
                                "parsing_method": "error",
                                "fallback_reason": "Object conversion failed",
                                "warnings": ["Failed to convert result object"],
                                "original_text": "",
                            }
                        )
                except Exception as e:
                    logger.error(
                        "result_conversion_error",
                        error=str(e),
                        result_type=type(r).__name__,
                    )
                    result_dicts.append(
                        {
                            "first_name": "",
                            "last_name": "",
                            "entity_type": "unknown",
                            "gender": "unknown",
                            "gender_confidence": 0.0,
                            "parsing_confidence": 0.0,
                            "parsing_method": "error",
                            "fallback_reason": f"Conversion error: {str(e)}",
                            "warnings": [f"Failed to convert: {str(e)}"],
                            "original_text": "",
                        }
                    )

            # Create optimized results DataFrame with proper column ordering and fallback tracking
            results_df = self._create_optimized_results_dataframe(
                df, result_dicts, name_columns, row_indices
            )

            # Generate comprehensive warning summary
            warning_summary = self.fallback_tracker.create_warning_summary(result_dicts)

            # Calculate analytics from results
            entity_stats = {
                "person_count": 0,
                "company_count": 0,
                "trust_count": 0,
                "unknown_count": 0,
                "error_count": 0,
            }

            confidence_stats = {
                "high_confidence_count": 0,  # >= 0.9
                "medium_confidence_count": 0,  # 0.7 - 0.89
                "low_confidence_count": 0,  # < 0.7
                "avg_confidence": 0.0,
            }

            total_confidence = 0.0
            valid_rows = 0

            for result in result_dicts:
                # Count entity types
                entity_type = result.get("entity_type", "unknown").lower()
                if entity_type == "person":
                    entity_stats["person_count"] += 1
                elif entity_type == "company":
                    entity_stats["company_count"] += 1
                elif entity_type == "trust":
                    entity_stats["trust_count"] += 1
                elif entity_type == "unknown":
                    entity_stats["unknown_count"] += 1
                else:
                    entity_stats["error_count"] += 1

                # Count confidence levels
                confidence = result.get("parsing_confidence", 0.0)
                if confidence > 0:
                    valid_rows += 1
                    total_confidence += confidence

                    if confidence >= 0.9:
                        confidence_stats["high_confidence_count"] += 1
                    elif confidence >= 0.7:
                        confidence_stats["medium_confidence_count"] += 1
                    else:
                        confidence_stats["low_confidence_count"] += 1

            if valid_rows > 0:
                confidence_stats["avg_confidence"] = total_confidence / valid_rows

            set_job_progress_sync(job_id, 95)

            # Save results with performance metrics and warning summary
            file_paths = await self._save_optimized_results(
                results_df,
                job_id,
                batch_result,
                start_time,
                result_dicts,
                warning_summary,
            )

            set_job_progress_sync(job_id, 100)

            # Calculate final statistics
            processing_time = time.time() - start_time
            performance_stats = self.batch_processor.get_performance_stats()

            processing_results = {
                "total_rows": total_rows,
                "processed_rows": total_rows,
                "successful_parses": batch_result.successful_parses,
                "failed_parses": total_rows - batch_result.successful_parses,
                "success_rate": (
                    (batch_result.successful_parses / total_rows) * 100
                    if total_rows > 0
                    else 0
                ),
                "processing_time": processing_time,
                "results_path": file_paths["csv_path"],
                "cache_hit_rate": performance_stats["cache_hit_rate"],
                "api_calls_made": batch_result.api_call_count,
                "estimated_cost": batch_result.cost_estimate,
                "cost_savings": performance_stats.get("cost_savings_from_cache", 0),
                "tokens_used": batch_result.total_tokens_used,
                "performance_stats": performance_stats,
                # Add analytics
                "entity_stats": entity_stats,
                "avg_confidence": confidence_stats["avg_confidence"],
                "high_confidence_count": confidence_stats["high_confidence_count"],
                "medium_confidence_count": confidence_stats["medium_confidence_count"],
                "low_confidence_count": confidence_stats["low_confidence_count"],
                # Add fallback tracking and warnings
                # Use batch_result stats as primary source, fallback to warning_summary
                "fallback_stats": {
                    "gemini_used": (
                        batch_result.gemini_used
                        if hasattr(batch_result, "gemini_used")
                        else warning_summary.get("gemini_used", 0)
                    ),
                    "fallback_used": (
                        batch_result.fallback_used
                        if hasattr(batch_result, "fallback_used")
                        else warning_summary.get("fallback_used", 0)
                    ),
                    "fallback_reasons": warning_summary.get("fallback_reasons", {}),
                    "fallback_rate": (
                        (batch_result.fallback_used / total_rows * 100)
                        if total_rows > 0 and hasattr(batch_result, "fallback_used")
                        else 0
                    ),
                },
                "warning_stats": {
                    "results_with_warnings": warning_summary["results_with_warnings"],
                    "total_warnings": warning_summary["total_warnings"],
                    "warning_rate": (
                        (warning_summary["results_with_warnings"] / total_rows * 100)
                        if total_rows > 0
                        else 0
                    ),
                },
                "quality_score": warning_summary["quality_score"],
                "recommendations": warning_summary["recommendations"],
            }

            update_job_status(
                job_id, JobStatus.COMPLETED, processing_results=processing_results
            )

            logger.info(
                "optimized_processing_completed",
                job_id=job_id,
                total_rows=total_rows,
                success_rate=processing_results["success_rate"],
                processing_time=processing_time,
                cache_hit_rate=performance_stats["cache_hit_rate"],
                api_calls=batch_result.api_call_count,
                cost_estimate=batch_result.cost_estimate,
            )

            return {"status": "completed", **processing_results, **file_paths}

        except Exception as e:
            logger.error("optimized_processing_failed", job_id=job_id, error=str(e))
            set_job_progress_sync(job_id, -1)
            update_job_status(job_id, JobStatus.FAILED, error_message=str(e))

            return {
                "status": "failed",
                "error": str(e),
                "total_rows": 0,
                "processed_rows": 0,
                "successful_parses": 0,
                "failed_parses": 0,
                "processing_time": time.time() - start_time,
            }

    async def _load_file_async(self, file_path: str) -> pd.DataFrame:
        """Load file asynchronously with enhanced error handling"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect encoding and validate
        encoding = detect_encoding(file_path)
        validate_file(file_path)

        # Load based on file type
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".csv":
            # Try multiple encodings for CSV files
            encodings_to_try = [encoding, "utf-8", "latin-1", "cp1252", "iso-8859-1"]
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    logger.info("csv_loaded_successfully", encoding=enc, rows=len(df))
                    return df
                except UnicodeDecodeError:
                    continue
            raise ValueError("Could not decode CSV file with any supported encoding")

        elif file_extension in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
            logger.info("excel_loaded_successfully", rows=len(df))
            return df

        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _identify_name_columns_with_config(
        self, df: pd.DataFrame, parsing_config: Dict[str, Any] = None
    ) -> List[str]:
        """Identify name columns with user configuration support"""
        from app.api.files.schemas import ProcessingConfig

        if parsing_config:
            config = ProcessingConfig(**parsing_config)
        else:
            config = ProcessingConfig()

        # User-specified columns take priority
        if (
            config
            and config.primary_name_column
            and config.primary_name_column in df.columns
        ):
            return [config.primary_name_column]
        elif config and config.name_columns:
            available_columns = [
                col for col in config.name_columns if col in df.columns
            ]
            if available_columns:
                return available_columns

        # Auto-detect name columns
        name_columns = self.file_service.identify_name_columns(df)
        if name_columns:
            return name_columns

        # Fallback to common column names
        fallback_columns = [
            "name",
            "names",
            "full_name",
            "fullname",
            "owner",
            "person",
            "client",
            "addressee",
        ]
        found_fallbacks = [col for col in fallback_columns if col in df.columns]
        if found_fallbacks:
            return found_fallbacks

        return []

    def _create_optimized_results_dataframe(
        self,
        original_df: pd.DataFrame,
        parsing_results: List[Dict[str, Any]],
        name_columns: List[str],
        row_indices: List[int],
    ) -> pd.DataFrame:
        """Create results DataFrame with PROCESSED COLUMNS FIRST, ORIGINAL COLUMNS LAST"""

        # CRITICAL: Processed columns go FIRST - Enhanced with fallback tracking
        processed_columns = [
            "entity_type",
            "first_name",
            "last_name",
            "gender",
            "gender_confidence",
            "parsing_confidence",
            "parsing_method",
            "fallback_reason",
            "gemini_used",
            "has_warnings",
            "low_confidence",
            "warnings",
            "original_name_text",
        ]

        # Create DataFrame with processed results first
        results_data = {}

        # Add processed columns FIRST
        for col in processed_columns:
            if col == "warnings":
                # Convert warnings list to string for CSV compatibility
                results_data[col] = [
                    (
                        "; ".join(result.get(col, []))
                        if isinstance(result.get(col), list)
                        else str(result.get(col, ""))
                    )
                    for result in parsing_results
                ]
            elif col == "original_name_text":
                results_data[col] = [
                    result.get("original_text", "") for result in parsing_results
                ]
            elif col in ["gemini_used", "has_warnings", "low_confidence"]:
                # Boolean fields
                results_data[col] = [
                    result.get(col, False) for result in parsing_results
                ]
            else:
                results_data[col] = [result.get(col, "") for result in parsing_results]

        # Create processed DataFrame
        processed_df = pd.DataFrame(results_data)

        # Add ALL original columns AFTER processed columns
        for col in original_df.columns:
            processed_df[col] = original_df[col].values

        # Add metadata columns at the end
        processed_df["processing_timestamp"] = datetime.now(timezone.utc).isoformat()
        processed_df["source_name_columns"] = ", ".join(name_columns)
        processed_df["row_index"] = row_indices

        return processed_df

    async def _save_optimized_results(
        self,
        results_df: pd.DataFrame,
        job_id: str,
        batch_result: Any,
        start_time: float,
        result_dicts: List[Dict[str, Any]],
        warning_summary: Dict[str, Any] = None,
    ) -> Dict[str, str]:
        """Save results with comprehensive performance metrics"""
        from app.core.config import settings

        # Generate filenames with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"processed_results_{job_id}_{timestamp}.csv"
        excel_filename = f"processed_results_{job_id}_{timestamp}.xlsx"

        csv_path = os.path.join(settings.RESULTS_DIR, csv_filename)
        excel_path = os.path.join(settings.RESULTS_DIR, excel_filename)

        # Ensure results directory exists
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)

        # Save CSV (primary format) with UTF-8-sig encoding for Excel compatibility
        # UTF-8-sig adds BOM (Byte Order Mark) that Excel needs to detect UTF-8
        results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # Save Excel with performance analytics
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            # Main results sheet
            results_df.to_excel(writer, sheet_name="Processed Results", index=False)

            # Performance metrics sheet
            perf_stats = self.batch_processor.get_performance_stats()
            processing_time = time.time() - start_time

            metrics_data = {
                "Metric": [
                    "Total Names Processed",
                    "Successful Parses",
                    "Failed Parses",
                    "Success Rate (%)",
                    "Cache Hit Rate (%)",
                    "API Calls Made",
                    "Total Tokens Used",
                    "Estimated Cost ($)",
                    "Cost Savings from Cache ($)",
                    "Processing Time (seconds)",
                    "Names per Second",
                    "Average Tokens per Name",
                    "Cost per Name ($)",
                    "Processing Timestamp",
                ],
                "Value": [
                    len(batch_result.results),
                    batch_result.successful_parses,
                    len(batch_result.results) - batch_result.successful_parses,
                    round(
                        (batch_result.successful_parses / len(batch_result.results))
                        * 100,
                        2,
                    ),
                    round(perf_stats["cache_hit_rate"] * 100, 2),
                    batch_result.api_call_count,
                    batch_result.total_tokens_used,
                    round(batch_result.cost_estimate, 4),
                    round(perf_stats.get("cost_savings_from_cache", 0), 4),
                    round(processing_time, 2),
                    round(len(batch_result.results) / max(processing_time, 0.001), 2),
                    round(perf_stats["average_tokens_per_request"], 1),
                    round(perf_stats["cost_per_request"], 6),
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                ],
            }

            metrics_df = pd.DataFrame(metrics_data)
            metrics_df.to_excel(writer, sheet_name="Performance Metrics", index=False)

            # Entity analysis sheet
            entity_analysis = self._create_entity_analysis(result_dicts)
            entity_df = pd.DataFrame(entity_analysis)
            entity_df.to_excel(writer, sheet_name="Entity Analysis", index=False)

            # Fallback and warning analysis sheet
            if warning_summary:
                fallback_analysis = self._create_fallback_analysis(warning_summary)
                fallback_df = pd.DataFrame(fallback_analysis)
                fallback_df.to_excel(
                    writer, sheet_name="Fallback Analysis", index=False
                )

        return {
            "csv_path": csv_path,
            "excel_path": excel_path,
            "csv_filename": csv_filename,
            "excel_filename": excel_filename,
        }

    def _create_entity_analysis(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create detailed entity analysis"""
        entity_counts = {}
        gender_counts = {}
        confidence_ranges = {
            "Low (0-0.5)": 0,
            "Medium (0.5-0.8)": 0,
            "High (0.8-1.0)": 0,
        }

        for result in results:
            # Entity type counts
            entity_type = result.get("entity_type", "unknown")
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

            # Gender counts for persons
            if entity_type == "person":
                gender = result.get("gender", "unknown")
                gender_counts[gender] = gender_counts.get(gender, 0) + 1

            # Confidence ranges
            confidence = result.get("parsing_confidence", 0)
            if confidence < 0.5:
                confidence_ranges["Low (0-0.5)"] += 1
            elif confidence < 0.8:
                confidence_ranges["Medium (0.5-0.8)"] += 1
            else:
                confidence_ranges["High (0.8-1.0)"] += 1

        analysis = []

        # Entity types
        analysis.append({"Category": "Entity Types", "Value": ""})
        for entity_type, count in entity_counts.items():
            pct = (count / len(results)) * 100
            analysis.append(
                {
                    "Category": f"  {entity_type.title()}",
                    "Value": f"{count} ({pct:.1f}%)",
                }
            )

        analysis.append({"Category": "", "Value": ""})

        # Gender distribution
        if gender_counts:
            analysis.append({"Category": "Gender Distribution (Persons)", "Value": ""})
            total_persons = sum(gender_counts.values())
            for gender, count in gender_counts.items():
                pct = (count / total_persons) * 100
                analysis.append(
                    {
                        "Category": f"  {gender.title()}",
                        "Value": f"{count} ({pct:.1f}%)",
                    }
                )

            analysis.append({"Category": "", "Value": ""})

        # Confidence ranges
        analysis.append({"Category": "Parsing Confidence", "Value": ""})
        for range_label, count in confidence_ranges.items():
            pct = (count / len(results)) * 100
            analysis.append(
                {"Category": f"  {range_label}", "Value": f"{count} ({pct:.1f}%)"}
            )

        return analysis

    def _create_fallback_analysis(
        self, warning_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create detailed fallback and warning analysis"""
        analysis = []
        total = warning_summary.get("total_results", 0)

        if total == 0:
            return [{"Category": "No data", "Value": "No results to analyze"}]

        # Parsing method distribution
        analysis.append({"Category": "Parsing Methods", "Value": ""})
        gemini_count = warning_summary.get("gemini_used", 0)
        fallback_count = warning_summary.get("fallback_used", 0)

        gemini_pct = (gemini_count / total) * 100
        fallback_pct = (fallback_count / total) * 100

        analysis.append(
            {
                "Category": f"  Gemini API Success",
                "Value": f"{gemini_count} ({gemini_pct:.1f}%)",
            }
        )
        analysis.append(
            {
                "Category": f"  Fallback Used",
                "Value": f"{fallback_count} ({fallback_pct:.1f}%)",
            }
        )
        analysis.append({"Category": "", "Value": ""})

        # Fallback reasons
        fallback_reasons = warning_summary.get("fallback_reasons", {})
        if fallback_reasons:
            analysis.append({"Category": "Fallback Reasons", "Value": ""})
            for reason, count in fallback_reasons.items():
                pct = (count / total) * 100
                # Convert reason to friendly name
                friendly_reason = self._get_friendly_fallback_reason(reason)
                analysis.append(
                    {
                        "Category": f"  {friendly_reason}",
                        "Value": f"{count} ({pct:.1f}%)",
                    }
                )
            analysis.append({"Category": "", "Value": ""})

        # Warning statistics
        results_with_warnings = warning_summary.get("results_with_warnings", 0)
        total_warnings = warning_summary.get("total_warnings", 0)
        low_confidence = warning_summary.get("low_confidence_results", 0)

        analysis.append({"Category": "Quality Indicators", "Value": ""})
        analysis.append(
            {
                "Category": f"  Results with Warnings",
                "Value": f"{results_with_warnings} ({(results_with_warnings / total) * 100:.1f}%)",
            }
        )
        analysis.append(
            {"Category": f"  Total Warnings Generated", "Value": f"{total_warnings}"}
        )
        analysis.append(
            {
                "Category": f"  Low Confidence Results",
                "Value": f"{low_confidence} ({(low_confidence / total) * 100:.1f}%)",
            }
        )
        analysis.append({"Category": "", "Value": ""})

        # Overall quality score
        quality_score = warning_summary.get("quality_score", 0) * 100
        analysis.append(
            {"Category": "Overall Quality Score", "Value": f"{quality_score:.1f}%"}
        )

        # Recommendations
        recommendations = warning_summary.get("recommendations", [])
        if recommendations:
            analysis.append({"Category": "", "Value": ""})
            analysis.append({"Category": "Recommendations", "Value": ""})
            for i, rec in enumerate(recommendations, 1):
                analysis.append({"Category": f"  {i}.", "Value": rec})

        return analysis

    def _get_friendly_fallback_reason(self, reason: str) -> str:
        """Convert fallback reason to user-friendly message"""
        reason_map = {
            "api_error": "API Error",
            "quota_exceeded": "Quota Exceeded",
            "timeout": "Request Timeout",
            "json_parse_error": "Response Parse Error",
            "empty_response": "Empty Response",
            "validation_failed": "Validation Failed",
            "rate_limit": "Rate Limit",
            "network_error": "Network Error",
            "auth_error": "Authentication Error",
            "unknown_error": "Unknown Error",
        }
        return reason_map.get(reason, reason.replace("_", " ").title())


def set_job_progress_sync(job_id: str, progress: int):
    """Store job progress in Redis synchronously"""
    try:
        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"job_progress:{job_id}"
        r.setex(key, 3600, str(progress))  # 1 hour TTL
    except Exception as e:
        logger.error("sync_job_progress_failed", job_id=job_id, error=str(e))


@celery_app.task(bind=True)
def process_file(
    self,
    job_id: str,
    file_path: str,
    user_id: str = None,
    parsing_config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    OPTIMIZED file processing with intelligent batch processing, caching, and cost optimization

    Features:
    - Smart payload filtering (only name/addressee data sent to API)
    - Intelligent batch processing with concurrency
    - High-performance caching with duplicate detection
    - Proper column ordering (processed columns FIRST, original columns LAST)
    - Comprehensive cost and performance optimization

    Args:
        job_id: Processing job ID
        file_path: Path to uploaded file
        user_id: User ID (None for anonymous)
        parsing_config: Parsing configuration options

    Returns:
        Dict with processing results and performance metrics
    """

    try:
        # Initialize optimized processor service
        processor_service = OptimizedFileProcessorService()

        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                processor_service.process_file_optimized(
                    job_id, file_path, user_id, parsing_config
                )
            )
            return result
        finally:
            # Cleanup
            try:
                if hasattr(processor_service.batch_processor, "cleanup"):
                    if asyncio.iscoroutinefunction(
                        processor_service.batch_processor.cleanup
                    ):
                        loop.run_until_complete(
                            processor_service.batch_processor.cleanup()
                        )
                    else:
                        processor_service.batch_processor.cleanup()
            except Exception as e:
                logger.warning("cleanup_error", error=str(e))
            finally:
                loop.close()

    except Exception as e:
        logger.error("optimized_file_processing_failed", job_id=job_id, error=str(e))

        # Update progress to indicate failure
        set_job_progress_sync(job_id, -1)
        update_job_status(job_id, JobStatus.FAILED, error_message=str(e))

        return {
            "status": "failed",
            "error": str(e),
            "total_rows": 0,
            "processed_rows": 0,
            "successful_parses": 0,
            "failed_parses": 0,
        }


@celery_app.task
def validate_uploaded_file(file_path: str) -> Dict[str, Any]:
    """
    Validate uploaded file before processing

    Args:
        file_path: Path to uploaded file

    Returns:
        Dict with validation results
    """
    try:
        # Basic file validation
        if not os.path.exists(file_path):
            return {"valid": False, "error": "File not found"}

        # Check file size
        file_size = os.path.getsize(file_path)
        from app.core.config import settings

        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size_bytes:
            return {
                "valid": False,
                "error": f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)",
            }

        # Validate file type and content
        validate_file(file_path)

        # Try to read file to check format
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == ".csv":
            encoding = detect_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding, nrows=5)  # Read first 5 rows
        elif file_extension in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path, nrows=5)
        else:
            return {"valid": False, "error": f"Unsupported file type: {file_extension}"}

        # Check if file has data
        if len(df) == 0:
            return {"valid": False, "error": "File is empty"}

        # Identify potential name columns
        file_service = FileService()
        name_columns = file_service.identify_name_columns(df)

        if not name_columns:
            return {"valid": False, "error": "No name columns found in file"}

        return {
            "valid": True,
            "file_size": file_size,
            "columns": list(df.columns),
            "name_columns": name_columns,
            "preview_rows": len(df),
        }

    except Exception as e:
        logger.error("file_validation_failed", file_path=file_path, error=str(e))
        return {"valid": False, "error": str(e)}
