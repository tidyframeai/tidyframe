"""
Centralized fallback tracking service for comprehensive parsing warnings
Tracks WHY fallback was used and provides detailed statistics
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class FallbackReason(str, Enum):
    """Standardized fallback reasons for consistent tracking"""

    API_ERROR = "api_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout"
    JSON_PARSE_ERROR = "json_parse_error"
    EMPTY_RESPONSE = "empty_response"
    VALIDATION_FAILED = "validation_failed"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    UNKNOWN_ERROR = "unknown_error"


class FallbackTracker:
    """Centralized service for tracking parsing fallbacks and warnings"""

    def __init__(self):
        self.session_stats = {
            "total_processed": 0,
            "gemini_success": 0,
            "fallback_used": 0,
            "fallback_reasons": {},
            "low_confidence_count": 0,
            "warnings_generated": 0,
        }

    def create_parsing_result(
        self,
        parsing_method: str,
        success: bool,
        confidence: float = 0.0,
        fallback_reason: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        original_text: str = "",
        **result_data,
    ) -> Dict[str, Any]:
        """
        Create standardized parsing result with fallback tracking

        Args:
            parsing_method: "gemini" or "fallback"
            success: Whether parsing was successful
            confidence: Confidence score (0-1)
            fallback_reason: Reason for fallback if applicable
            warnings: List of warning messages
            original_text: Original input text
            **result_data: Additional result fields

        Returns:
            Standardized parsing result dictionary
        """

        # Update session statistics
        self.session_stats["total_processed"] += 1

        if parsing_method == "gemini" and success:
            self.session_stats["gemini_success"] += 1
        elif parsing_method == "fallback":
            self.session_stats["fallback_used"] += 1
            if fallback_reason:
                self.session_stats["fallback_reasons"][fallback_reason] = (
                    self.session_stats["fallback_reasons"].get(fallback_reason, 0) + 1
                )

        if confidence < 0.7:
            self.session_stats["low_confidence_count"] += 1

        # Ensure warnings list
        if warnings is None:
            warnings = []

        # Add automatic warnings based on conditions
        auto_warnings = self._generate_automatic_warnings(
            parsing_method, success, confidence, fallback_reason
        )
        warnings.extend(auto_warnings)

        if warnings:
            self.session_stats["warnings_generated"] += len(warnings)

        # Create standardized result
        result = {
            # Core parsing results
            "first_name": result_data.get("first_name", ""),
            "last_name": result_data.get("last_name", ""),
            "entity_type": result_data.get("entity_type", "unknown"),
            "gender": result_data.get("gender", "unknown"),
            "gender_confidence": result_data.get("gender_confidence", 0.0),
            "is_agricultural": result_data.get("is_agricultural", False),
            # Parsing metadata
            "parsing_method": parsing_method,
            "parsing_confidence": confidence,
            "fallback_reason": fallback_reason,
            "gemini_used": parsing_method == "gemini",
            # Warnings and quality indicators
            "warnings": warnings,
            "has_warnings": len(warnings) > 0,
            "low_confidence": confidence < 0.7,
            # Additional metadata
            "original_text": original_text,
            "parsing_timestamp": datetime.now(timezone.utc).isoformat(),
            "parsing_success": success,
            # Include any additional result data
            **{
                k: v
                for k, v in result_data.items()
                if k
                not in [
                    "first_name",
                    "last_name",
                    "entity_type",
                    "gender",
                    "gender_confidence",
                    "is_agricultural",
                ]
            },
        }

        # Log fallback usage for monitoring
        if parsing_method == "fallback":
            logger.warning(
                "fallback_parsing_used",
                original_text=original_text,
                reason=fallback_reason,
                confidence=confidence,
                warnings_count=len(warnings),
            )
        elif confidence < 0.7:
            logger.warning(
                "low_confidence_parsing",
                original_text=original_text,
                parsing_method=parsing_method,
                confidence=confidence,
                warnings_count=len(warnings),
            )

        return result

    def _generate_automatic_warnings(
        self,
        parsing_method: str,
        success: bool,
        confidence: float,
        fallback_reason: Optional[str],
    ) -> List[str]:
        """Generate automatic warnings based on parsing conditions"""
        warnings = []

        # Fallback usage warning
        if parsing_method == "fallback":
            if fallback_reason:
                reason_msg = self._get_friendly_fallback_reason(fallback_reason)
                warnings.append(
                    f"Gemini API unavailable ({reason_msg}) - used fallback parsing"
                )
            else:
                warnings.append("Gemini API unavailable - used fallback parsing")

        # Confidence warnings
        if confidence < 0.5:
            warnings.append("Very low parsing confidence - manual review recommended")
        elif confidence < 0.7:
            warnings.append("Low parsing confidence - verification suggested")

        # Success warnings
        if not success:
            warnings.append("Parsing failed - result may be incomplete")

        return warnings

    def _get_friendly_fallback_reason(self, reason: str) -> str:
        """Convert fallback reason to user-friendly message"""
        reason_map = {
            FallbackReason.API_ERROR: "API error",
            FallbackReason.QUOTA_EXCEEDED: "API quota exceeded",
            FallbackReason.TIMEOUT: "request timeout",
            FallbackReason.JSON_PARSE_ERROR: "response parsing error",
            FallbackReason.EMPTY_RESPONSE: "empty API response",
            FallbackReason.VALIDATION_FAILED: "response validation failed",
            FallbackReason.RATE_LIMIT: "rate limit exceeded",
            FallbackReason.NETWORK_ERROR: "network error",
            FallbackReason.AUTH_ERROR: "authentication error",
            FallbackReason.UNKNOWN_ERROR: "unknown error",
        }
        return reason_map.get(reason, reason)

    def track_batch_processing(
        self,
        total_rows: int,
        gemini_used_count: int,
        fallback_used_count: int,
        fallback_reasons: Dict[str, int],
    ) -> Dict[str, Any]:
        """Track batch processing statistics"""

        batch_stats = {
            "total_rows": total_rows,
            "gemini_success_rate": (
                (gemini_used_count / total_rows * 100) if total_rows > 0 else 0
            ),
            "fallback_usage_rate": (
                (fallback_used_count / total_rows * 100) if total_rows > 0 else 0
            ),
            "fallback_reasons": fallback_reasons,
            "processing_quality": (
                "high"
                if gemini_used_count / total_rows > 0.95
                else "medium" if gemini_used_count / total_rows > 0.8 else "low"
            ),
        }

        # Log batch statistics
        logger.info(
            "batch_processing_stats",
            total_rows=total_rows,
            gemini_success_rate=batch_stats["gemini_success_rate"],
            fallback_usage_rate=batch_stats["fallback_usage_rate"],
            processing_quality=batch_stats["processing_quality"],
            fallback_reasons=fallback_reasons,
        )

        return batch_stats

    def create_warning_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive warning summary from parsing results"""

        if not results:
            return {"total_results": 0}

        summary = {
            "total_results": len(results),
            "gemini_used": 0,
            "fallback_used": 0,
            "fallback_reasons": {},
            "low_confidence_results": 0,
            "results_with_warnings": 0,
            "total_warnings": 0,
            "quality_score": 0.0,
            "recommendations": [],
        }

        for result in results:
            # Count parsing methods
            if result.get("parsing_method") == "gemini":
                summary["gemini_used"] += 1
            elif result.get("parsing_method") == "fallback":
                summary["fallback_used"] += 1

                # Track fallback reasons
                reason = result.get("fallback_reason")
                if reason:
                    summary["fallback_reasons"][reason] = (
                        summary["fallback_reasons"].get(reason, 0) + 1
                    )

            # Count quality indicators
            if result.get("parsing_confidence", 0) < 0.7:
                summary["low_confidence_results"] += 1

            warnings = result.get("warnings", [])
            if warnings:
                summary["results_with_warnings"] += 1
                summary["total_warnings"] += len(warnings)

        # Calculate quality score
        total = summary["total_results"]
        quality_factors = [
            summary["gemini_used"] / total,  # Gemini usage rate
            (total - summary["low_confidence_results"]) / total,  # High confidence rate
            (total - summary["results_with_warnings"])
            / total
            * 0.5,  # Low warning rate
        ]
        summary["quality_score"] = sum(quality_factors) / len(quality_factors)

        # Generate recommendations
        summary["recommendations"] = self._generate_recommendations(summary)

        return summary

    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on parsing statistics"""
        recommendations = []
        total = summary["total_results"]

        if total == 0:
            return recommendations

        # Fallback usage recommendations
        fallback_rate = summary["fallback_used"] / total
        if fallback_rate > 0.1:  # More than 10% fallback usage
            recommendations.append(
                f"{fallback_rate * 100:.1f}% of rows used fallback parsing - "
                f"consider checking Gemini API status or quota limits"
            )

        # Low confidence recommendations
        low_confidence_rate = summary["low_confidence_results"] / total
        if low_confidence_rate > 0.2:  # More than 20% low confidence
            recommendations.append(
                f"{low_confidence_rate * 100:.1f}% of results have low confidence - "
                f"manual review recommended for critical data"
            )

        # Warning rate recommendations
        warning_rate = summary["results_with_warnings"] / total
        if warning_rate > 0.3:  # More than 30% have warnings
            recommendations.append(
                f"{warning_rate * 100:.1f}% of results have warnings - "
                f"review data quality and input formatting"
            )

        # Specific fallback reason recommendations
        for reason, count in summary["fallback_reasons"].items():
            rate = count / total
            if rate > 0.05:  # More than 5% for any single reason
                friendly_reason = self._get_friendly_fallback_reason(reason)
                recommendations.append(
                    f"Frequent fallback due to {friendly_reason} ({rate * 100:.1f}%) - "
                    f"investigate API connectivity or configuration"
                )

        return recommendations

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get current session statistics"""
        stats = self.session_stats.copy()

        # Calculate rates
        total = stats["total_processed"]
        if total > 0:
            stats["gemini_success_rate"] = (stats["gemini_success"] / total) * 100
            stats["fallback_rate"] = (stats["fallback_used"] / total) * 100
            stats["low_confidence_rate"] = (stats["low_confidence_count"] / total) * 100
        else:
            stats["gemini_success_rate"] = 0
            stats["fallback_rate"] = 0
            stats["low_confidence_rate"] = 0

        return stats

    def reset_session_stats(self):
        """Reset session statistics"""
        self.session_stats = {
            "total_processed": 0,
            "gemini_success": 0,
            "fallback_used": 0,
            "fallback_reasons": {},
            "low_confidence_count": 0,
            "warnings_generated": 0,
        }
