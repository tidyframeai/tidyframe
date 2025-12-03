"""
Name parsing validation utilities
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NameValidator:
    """Validator for name parsing results and input"""

    def __init__(self):
        # Common problematic patterns
        self.problematic_patterns = [
            # SQL injection attempts
            re.compile(
                r"(select|drop|delete|insert|update|create|alter)\s", re.IGNORECASE
            ),
            # HTML/XML tags
            re.compile(r"<[^>]+>"),
            # Email addresses (shouldn't be names)
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            # URLs
            re.compile(r"https?://[^\s]+"),
            # Excessive punctuation
            re.compile(r"[!@#$%^*]{3,}"),
            # Numbers that look suspicious (like phone numbers)
            re.compile(r"\b\d{10,}\b"),
        ]

        # Valid name characters (allowing international characters and joint indicators)
        # KEEP: &, and, AND for joint ownership
        self.valid_name_pattern = re.compile(r"^[a-zA-ZÀ-ÿĀ-žА-я\s\-'.&,/()]+$")

        # Single letter pattern (to filter out)
        self.single_letter_pattern = re.compile(r"^\s*[a-zA-Z]\s*$")

        # Invalid name patterns (special characters, numbers in wrong places)
        self.invalid_name_patterns = [
            re.compile(r"^[^a-zA-ZÀ-ÿĀ-žА-я]+$"),  # Only special characters
            re.compile(r"^\d+$"),  # Only numbers
            re.compile(r"[!@#$%^*+=<>?{}|\\~`]"),  # Problematic special chars
        ]

        # Common valid name prefixes and suffixes
        self.valid_prefixes = [
            "mr",
            "mrs",
            "ms",
            "dr",
            "prof",
            "rev",
            "hon",
            "sir",
            "dame",
        ]
        self.valid_suffixes = [
            "jr",
            "sr",
            "ii",
            "iii",
            "iv",
            "v",
            "md",
            "phd",
            "esq",
            "cpa",
        ]

        # Common business entity types - enhanced patterns
        self.business_entities = [
            "llc",
            "inc",
            "corp",
            "ltd",
            "co",
            "company",
            "corporation",
            "partnership",
            "lp",
            "limited",
            "enterprises",
            "associates",
            "group",
            "holdings",
            "investments",
            "l.l.c.",
            "l.l.c",
            "llp",
            "l.l.p.",
            "l.l.p",
            "limited liability company",
            "incorporated",
            "chtd",
            "chartered",
            "pllc",
            "p.l.l.c.",
            "p.l.l.c",
            "professional corporation",
            "professional llc",
            "pc",
            "p.c.",
            "properties",
            "development",
            "construction",
            "consulting",
            "services",
            "solutions",
            "systems",
            "technologies",
            "tech",
            "capital",
            "ventures",
            "fund",
            "funds",
            "management",
            "real estate",
            "realty",
            "property management",
            "farms",
            "farm llc",
            "ranch llc",
            "agriculture llc",
            "ag llc",
        ]

        # Trust/estate indicators - enhanced patterns
        self.trust_indicators = [
            "trust",
            "family trust",
            "revocable trust",
            "irrevocable trust",
            "living trust",
            "testamentary trust",
            "estate",
            "et al",
            "charitable trust",
            "remainder trust",
            "trust fund",
            "bypass trust",
            "generation skipping trust",
            "gst",
            "qtip trust",
            "marital trust",
            "credit shelter trust",
            "dynasty trust",
            "grat",
            "grantor trust",
            "trustee",
            "trustees",
            "trust agreement",
            "trust dated",
            "the trust of",
            "trust u/a",
            "trust dtd",
            "trust dt",
            "trust established",
            "trust created",
            "trust under will",
        ]

    def validate_input(self, name_text: str) -> Dict[str, any]:
        """
        Validate input name text for safety and reasonableness

        Args:
            name_text: Input name text to validate

        Returns:
            Dict with validation results
        """
        if not name_text:
            return {
                "is_valid": False,
                "error": "Empty input",
                "warnings": [],
                "sanitized_text": "",
            }

        # Clean whitespace
        cleaned_text = " ".join(name_text.split())
        warnings = []

        # Check length limits
        if len(cleaned_text) > 500:
            return {
                "is_valid": False,
                "error": "Input too long (max 500 characters)",
                "warnings": warnings,
                "sanitized_text": cleaned_text[:500],
            }

        # Check for problematic patterns
        for pattern in self.problematic_patterns:
            if pattern.search(cleaned_text):
                return {
                    "is_valid": False,
                    "error": "Input contains potentially harmful content",
                    "warnings": warnings,
                    "sanitized_text": "",
                }

        # Check for valid characters
        if not self.valid_name_pattern.match(cleaned_text):
            warnings.append("Contains unusual characters for names")

        # Check for excessive repetition
        words = cleaned_text.lower().split()
        if len(words) > len(set(words)) + 2:  # Allow some repetition
            warnings.append("Contains excessive word repetition")

        # Check for reasonable word count
        if len(words) > 20:
            warnings.append("Contains unusually many words for a name")

        return {
            "is_valid": True,
            "error": None,
            "warnings": warnings,
            "sanitized_text": cleaned_text,
        }

    def clean_name_part(self, name_part: str) -> Optional[str]:
        """
        Clean a single name part (first/last name) by filtering out
        invalid characters and single letters

        Args:
            name_part: Raw name part to clean

        Returns:
            Cleaned name part or None if invalid
        """
        if not name_part or not name_part.strip():
            return None

        cleaned = name_part.strip()

        # Filter out single letters (unless common initials)
        if self.single_letter_pattern.match(cleaned):
            return None

        # Check for invalid patterns
        for pattern in self.invalid_name_patterns:
            if pattern.search(cleaned):
                return None

        # Remove problematic special characters but keep valid ones
        # Keep: apostrophes, hyphens, spaces, dots for initials, &, /, and joint indicators
        # PRESERVE: &, and, AND for joint ownership detection
        cleaned = re.sub(r"[!@#$%^*+=<>?{}|\\~`]", "", cleaned)

        # Clean up multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Must have at least 2 characters after cleaning
        if len(cleaned) < 2:
            return None

        # Must contain at least one letter
        if not re.search(r"[a-zA-ZÀ-ÿĀ-žА-я]", cleaned):
            return None

        return cleaned

    def validate_parsing_result(self, result: Dict) -> Dict[str, any]:
        """
        Validate parsing result for consistency and reasonableness

        Args:
            result: Parsing result dictionary

        Returns:
            Dict with validation results and corrections
        """
        validation_warnings = []
        corrected_result = result.copy()

        # Validate entity type consistency
        first_name = result.get("first_name", "").strip()
        last_name = result.get("last_name", "").strip()
        entity_type = result.get("entity_type", "")

        # Check entity type logic
        if entity_type == "person":
            if not first_name and not last_name:
                validation_warnings.append("Person entity type but no names extracted")

            # Check for business indicators in person names
            full_name = f"{first_name} {last_name}".lower()
            if any(entity in full_name for entity in self.business_entities):
                validation_warnings.append(
                    "Person type but contains business entity indicators"
                )
                # Consider changing to company
                if not first_name or len(first_name.split()) > 3:
                    corrected_result["entity_type"] = "company"
                    corrected_result["first_name"] = ""
                    corrected_result["last_name"] = ""
                    validation_warnings.append("Changed to company entity type")

        elif entity_type == "company":
            if first_name or last_name:
                validation_warnings.append(
                    "Company entity type but names were extracted"
                )
                # Don't auto-correct, just warn

        # Validate confidence scores
        parsing_confidence = result.get("parsing_confidence", 0)
        gender_confidence = result.get("gender_confidence", 0)

        if not (0 <= parsing_confidence <= 1):
            corrected_result["parsing_confidence"] = max(0, min(1, parsing_confidence))
            validation_warnings.append("Parsing confidence was out of valid range")

        if not (0 <= gender_confidence <= 1):
            corrected_result["gender_confidence"] = max(0, min(1, gender_confidence))
            validation_warnings.append("Gender confidence was out of valid range")

        # Validate gender logic - trust Gemini's determination
        gender = result.get("gender", "")
        if gender not in ["male", "female", "unknown"]:
            # Only fix truly invalid values - default to male
            corrected_result["gender"] = "male"
            corrected_result["gender_confidence"] = 0.3
            validation_warnings.append("Invalid gender value, defaulted to male")
        # Trust Gemini's 'unknown' determination - don't override it
        # Gemini already defaults to male for ambiguous names (see improved_gemini_prompt.py line 237)

        # Check for missing middle initial when it should be extracted
        if entity_type == "person" and first_name:
            original_text = result.get("original_text", "")
            # Simple heuristic: if there's a single letter between first and last name
            words = original_text.split()
            if len(words) >= 3:
                potential_middle = words[1]
                if len(potential_middle) == 1 and potential_middle.isalpha():
                    if not result.get("middle_initial"):
                        corrected_result["middle_initial"] = potential_middle.upper()
                        validation_warnings.append("Extracted missed middle initial")

        # Validate agricultural flag
        is_agricultural = result.get("is_agricultural", False)
        original_text = result.get("original_text", "").lower()

        agricultural_terms = [
            "farm",
            "ranch",
            "agriculture",
            "livestock",
            "grain",
            "dairy",
        ]
        has_ag_terms = any(term in original_text for term in agricultural_terms)

        if is_agricultural and not has_ag_terms:
            validation_warnings.append(
                "Agricultural flag set but no agricultural terms found"
            )
        elif not is_agricultural and has_ag_terms:
            corrected_result["is_agricultural"] = True
            validation_warnings.append(
                "Added agricultural flag based on detected terms"
            )

        # Combine warnings
        existing_warnings = result.get("warnings", [])
        all_warnings = existing_warnings + validation_warnings
        corrected_result["warnings"] = all_warnings

        return {
            "is_valid": len(validation_warnings) < 5,  # Too many warnings = invalid
            "corrected_result": corrected_result,
            "validation_warnings": validation_warnings,
        }

    def detect_name_structure(self, name_text: str) -> Dict[str, any]:
        """
        Detect the structure and complexity of a name

        Args:
            name_text: Name text to analyze

        Returns:
            Dict with structure information
        """
        if not name_text:
            return {"complexity": "empty", "indicators": []}

        text_lower = name_text.lower()
        indicators = []
        complexity = "simple"

        # Check for joint names
        joint_patterns = ["&", " and ", "/", ", "]
        has_joint = any(pattern in text_lower for pattern in joint_patterns)
        if has_joint:
            indicators.append("joint_names")
            complexity = "complex"

        # Check for business entities
        if any(entity in text_lower for entity in self.business_entities):
            indicators.append("business_entity")

        # Check for trusts
        if any(trust in text_lower for trust in self.trust_indicators):
            indicators.append("trust_entity")

        # Check for titles/prefixes
        words = text_lower.split()
        if any(word in self.valid_prefixes for word in words):
            indicators.append("has_title")

        if any(word in self.valid_suffixes for word in words):
            indicators.append("has_suffix")

        # Check word count
        word_count = len(words)
        if word_count > 6:
            indicators.append("many_words")
            complexity = "complex"
        elif word_count <= 1:
            complexity = "simple"

        # Check for special characters
        special_chars = set(name_text) - set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
        )
        if special_chars:
            indicators.append("special_characters")
            if len(special_chars) > 2:
                complexity = "complex"

        return {
            "complexity": complexity,
            "indicators": indicators,
            "word_count": word_count,
            "special_characters": list(special_chars),
        }

    def detect_entity_type(self, name_text: str) -> Dict[str, any]:
        """
        Comprehensively detect entity type with confidence scoring

        Args:
            name_text: Name text to analyze

        Returns:
            Dict with entity type detection results
        """
        if not name_text:
            return {
                "entity_type": "unknown",
                "parsing_confidence": 0.0,
                "indicators": [],
            }

        text_lower = name_text.lower().strip()
        indicators = []
        scores = {"person": 0.0, "company": 0.0, "trust": 0.0}

        # Trust detection with weighted scoring
        trust_score = 0.0
        for indicator in self.trust_indicators:
            if indicator in text_lower:
                if indicator in ["trust", "estate"]:
                    trust_score += 0.3  # Common trust words
                elif indicator in ["trustee", "trustees", "trust agreement"]:
                    trust_score += 0.6  # Strong trust indicators
                elif indicator in ["family trust", "living trust", "revocable trust"]:
                    trust_score += 0.8  # Very strong trust indicators
                else:
                    trust_score += 0.4  # Medium trust indicators
                indicators.append(f"trust_indicator: {indicator}")

        scores["trust"] = min(trust_score, 1.0)

        # Company detection with weighted scoring
        company_score = 0.0
        for entity in self.business_entities:
            if entity in text_lower:
                if entity in ["llc", "inc", "corp", "ltd", "corporation"]:
                    company_score += 0.9  # Very strong company indicators
                elif entity in ["company", "enterprises", "group"]:
                    company_score += 0.7  # Strong company indicators
                elif entity in ["properties", "consulting", "services"]:
                    company_score += 0.5  # Medium company indicators
                else:
                    company_score += 0.6  # Default company indicators
                indicators.append(f"business_entity: {entity}")

        scores["company"] = min(company_score, 1.0)

        # Person detection logic
        person_score = 0.0

        # Check for personal titles
        for prefix in self.valid_prefixes:
            if prefix in text_lower:
                person_score += 0.6
                indicators.append(f"title: {prefix}")

        for suffix in self.valid_suffixes:
            if suffix in text_lower:
                person_score += 0.4
                indicators.append(f"suffix: {suffix}")

        # Check word structure for person names
        words = text_lower.split()
        if len(words) == 2:
            person_score += 0.3  # Two words could be first/last name
        elif len(words) == 3:
            person_score += 0.4  # Three words could be first/middle/last

        # Deduct points if entity indicators are present
        if scores["company"] > 0.5 or scores["trust"] > 0.5:
            person_score = max(0.0, person_score - 0.4)

        # Check for joint names (multiple people)
        joint_patterns = [" & ", " and ", "/", ", "]
        has_joint = any(pattern in text_lower for pattern in joint_patterns)
        if has_joint and scores["company"] < 0.5 and scores["trust"] < 0.5:
            person_score += 0.3
            indicators.append("joint_names_detected")

        scores["person"] = min(person_score, 1.0)

        # Determine final entity type
        max_score = max(scores.values())

        if max_score < 0.3:
            entity_type = "unknown"
            parsing_confidence = max_score
        else:
            entity_type = max(scores, key=scores.get)
            parsing_confidence = max_score

        return {
            "entity_type": entity_type,
            "parsing_confidence": parsing_confidence,
            "scores": scores,
            "indicators": indicators,
            "has_joint_names": has_joint if "has_joint" in locals() else False,
        }

    def suggest_improvements(self, result: Dict) -> List[str]:
        """
        Suggest improvements for parsing result

        Args:
            result: Parsing result

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        parsing_confidence = result.get("parsing_confidence", 0)
        entity_type = result.get("entity_type", "")

        # Low confidence suggestions
        if parsing_confidence < 0.5:
            suggestions.append("Consider manual review due to low parsing confidence")

        # Missing information suggestions
        if entity_type == "person":
            if not result.get("first_name"):
                suggestions.append(
                    "First name not identified - check if entity type is correct"
                )
            if not result.get("last_name"):
                suggestions.append("Last name not identified - verify input format")

        # Gender determination suggestions
        if result.get("gender") == "unknown" and entity_type == "person":
            suggestions.append(
                "Gender could not be determined - consider using additional context"
            )

        # Joint name suggestions
        if "joint_names" in result:
            suggestions.append(
                "Joint name detected - consider processing individual names separately"
            )

        return suggestions
