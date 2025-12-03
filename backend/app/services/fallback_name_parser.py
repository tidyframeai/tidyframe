"""
Fallback name parser for when Gemini AI is unavailable
Provides basic name parsing functionality without AI
"""

import re
from typing import Dict, List, Optional

try:
    import structlog

    logger = structlog.get_logger()
except ImportError:
    # For testing without full environment
    class MockLogger:
        def error(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

    logger = MockLogger()


class FallbackNameParser:
    """Rule-based name parser using same logic as Gemini prompt for consistency"""

    # Entity markers to remove during name extraction
    ENTITY_MARKERS = {
        "trust",
        "ttee",
        "trs",
        "tste",
        "trustee",
        "rev",
        "revocable",
        "irrevocable",
        "living",
        "family",
        "marital",
        "residuary",
        "charitable",
        "foundation",
        "estate",
        "life",
        "le",
        "l/e",
        "agreement",
        "dated",
        "dtd",
        "llc",
        "llp",
        "inc",
        "corp",
        "ltd",
        "limited",
        "company",
        "co",
        "properties",
        "enterprises",
        "holdings",
        "group",
        "partnership",
        "lp",
        "farms",
        "etal",
        "et",
        "al",
        "and",
        "&",
        "or",
        "the",
        "of",
        "a",
        "an",
    }

    # Common first names for recognition
    COMMON_FIRST_NAMES = {
        # Male
        "john",
        "james",
        "robert",
        "michael",
        "david",
        "william",
        "richard",
        "joseph",
        "thomas",
        "christopher",
        "charles",
        "daniel",
        "matthew",
        "kenneth",
        "steven",
        "edward",
        "brian",
        "ronald",
        "anthony",
        "kevin",
        "jason",
        "gary",
        "timothy",
        "larry",
        "frank",
        "scott",
        "eric",
        "paul",
        "mark",
        "dennis",
        "jerry",
        "aaron",
        "henry",
        "nathan",
        "douglas",
        "cole",
        "dale",
        "warren",
        "edwin",
        "russell",
        "conrad",
        "carl",
        "harold",
        "walter",
        "raymond",
        "patrick",
        "peter",
        "eugene",
        "randy",
        "louis",
        "philip",
        "johnny",
        "billy",
        "alan",
        "roger",
        "gerald",
        "keith",
        "marvin",
        "virgil",
        "harry",
        # Female
        "mary",
        "patricia",
        "jennifer",
        "linda",
        "elizabeth",
        "barbara",
        "susan",
        "jessica",
        "sarah",
        "karen",
        "lisa",
        "nancy",
        "betty",
        "margaret",
        "sandra",
        "ashley",
        "kimberly",
        "emily",
        "donna",
        "michelle",
        "dorothy",
        "carol",
        "amanda",
        "melissa",
        "deborah",
        "stephanie",
        "rebecca",
        "sharon",
        "laura",
        "cynthia",
        "kathleen",
        "helen",
        "amy",
        "angela",
        "brenda",
        "emma",
        "anna",
        "pamela",
        "nicole",
        "ruth",
        "katherine",
        "christine",
        "debra",
        "rachel",
        "janet",
        "maria",
        "diane",
        "julie",
        "joyce",
        "virginia",
        "kelly",
        "beulah",
        "phyllis",
        "beverly",
        "alice",
        "joan",
        "judith",
        "rose",
        "janice",
        "gloria",
        "martha",
        "paula",
        "shari",
        "eva",
        "cleo",
    }

    # Common last names
    COMMON_LAST_NAMES = {
        "smith",
        "johnson",
        "williams",
        "brown",
        "jones",
        "garcia",
        "miller",
        "davis",
        "rodriguez",
        "martinez",
        "hernandez",
        "lopez",
        "gonzalez",
        "wilson",
        "anderson",
        "thomas",
        "taylor",
        "moore",
        "jackson",
        "martin",
        "lee",
        "thompson",
        "white",
        "harris",
        "clark",
        "lewis",
        "robinson",
        "walker",
        "young",
        "allen",
        "king",
        "wright",
        "scott",
        "hill",
        "green",
        "adams",
        "nelson",
        "baker",
        "hall",
        "campbell",
        "mitchell",
        "carter",
        "roberts",
        "birch",
        "cheslak",
        "mcculley",
        "daake",
        "hansen",
        "pudenz",
        "mills",
        "hadley",
        "schmid",
        "cross",
        "fry",
        "bonde",
        "schimanski",
        "woerhler",
        "jensen",
        "arkfeld-mohr",
        "meyer",
        "meter",
    }

    # Surname prefixes (keep with last name)
    SURNAME_PREFIXES = [
        "mc",
        "mac",
        "o'",
        "van",
        "von",
        "de",
        "la",
        "del",
        "della",
        "di",
        "da",
        "des",
        "der",
        "den",
        "le",
        "los",
        "las",
    ]

    # Title prefixes and suffixes to remove
    PREFIXES = {
        "dr",
        "dr.",
        "doctor",
        "mr",
        "mr.",
        "mrs",
        "mrs.",
        "ms",
        "ms.",
        "miss",
        "prof",
        "prof.",
        "professor",
        "rev",
        "rev.",
        "reverend",
        "hon",
        "hon.",
        "honorable",
        "judge",
        "sir",
        "dame",
        "lord",
        "lady",
    }

    SUFFIXES = {
        "jr",
        "jr.",
        "junior",
        "sr",
        "sr.",
        "senior",
        "ii",
        "iii",
        "iv",
        "v",
        "esq",
        "esq.",
        "esquire",
        "phd",
        "ph.d",
        "md",
        "m.d",
        "dds",
        "d.d.s",
        "llb",
        "ll.b",
        "jd",
        "j.d",
        "cpa",
        "c.p.a",
        "mba",
        "m.b.a",
    }

    # Entity keywords (for classification only)
    ENTITY_KEYWORDS = {
        "llc",
        "inc",
        "corp",
        "corporation",
        "company",
        "co",
        "limited",
        "ltd",
        "trust",
        "estate",
        "partnership",
        "associates",
        "group",
        "foundation",
        "fund",
        "bank",
        "credit union",
        "society",
        "organization",
        "association",
    }

    def parse_name(self, name_text: str) -> Dict[str, Optional[str]]:
        """
        Parse a name into components using rule-based logic

        Args:
            name_text: The raw name string to parse

        Returns:
            Dictionary with parsed name components
        """
        if not name_text:
            return self._empty_result()

        # Clean and normalize the input
        name_text = name_text.strip()

        # Check if it's an entity
        if self._is_entity(name_text):
            return self._parse_entity(name_text)

        # Check for multiple names (couples)
        if self._has_multiple_names(name_text):
            return self._parse_multiple_names(name_text)

        # Parse as individual name
        return self._parse_individual_name(name_text)

    def _empty_result(self) -> Dict[str, Optional[str]]:
        """Return empty result structure"""
        return {
            "first_name": None,
            "last_name": None,
            "middle_name": None,
            "prefix": None,
            "suffix": None,
            "entity_name": None,
            "entity_type": None,
            "is_entity": False,
            "confidence": 0.5,
            "parser_type": "fallback",
            "parsing_method": "fallback",  # Required field for metrics tracking
            "parsing_confidence": 0.5,
            "gemini_used": False,
            "has_warnings": False,
            "warnings": [],
        }

    def _is_entity(self, name_text: str) -> bool:
        """Check if the text represents an entity rather than a person"""
        lower_text = name_text.lower()

        # Check for entity keywords
        for keyword in self.ENTITY_KEYWORDS:
            if keyword in lower_text:
                return True

        # Check for patterns like "The X Foundation"
        if lower_text.startswith("the "):
            return True

        return False

    def _parse_entity(self, name_text: str) -> Dict[str, Optional[str]]:
        """Parse entity name with intelligent name extraction for trusts"""
        result = self._empty_result()
        result["entity_name"] = name_text
        result["is_entity"] = True
        result["confidence"] = 0.7

        # Try to identify entity type
        lower_text = name_text.lower()
        if "trust" in lower_text or "estate" in lower_text:
            result["entity_type"] = "trust"
            # For trusts, extract beneficiary names while maintaining trust entity type
            extracted_names = self._extract_person_from_trust(name_text)
            result["first_name"] = extracted_names.get("first_name", "")
            result["last_name"] = extracted_names.get("last_name", "")
            # Keep entity_type as trust but show extracted names
            result["is_entity"] = False  # This allows showing person names
            result.pop("entity_name", None)  # Remove entity_name to show person names
        elif any(
            x in lower_text
            for x in [
                "llc",
                "inc",
                "corp",
                "corporation",
                "company",
                "limited",
                "ltd",
                "properties",
                "enterprises",
                "holdings",
                "group",
            ]
        ):
            result["entity_type"] = "company"  # Lowercase
            # Companies don't get person names extracted
        elif any(x in lower_text for x in ["foundation", "fund"]):
            result["entity_type"] = "trust"  # Group with trusts
        else:
            result["entity_type"] = "unknown"  # Lowercase

        return result

    def _has_multiple_names(self, name_text: str) -> bool:
        """Check if text contains multiple names (e.g., couples)"""
        # Look for patterns like "John & Mary Smith", "John and Mary Smith", or "Name/Name"
        return bool(re.search(r"(\s+(&|and)\s+|/)", name_text, re.IGNORECASE))

    def _parse_multiple_names(self, name_text: str) -> Dict[str, Optional[str]]:
        """Parse text containing multiple names with intelligent analysis"""
        # Enhanced joint name parsing with position-based preference

        # Handle slash patterns first: "Hamilton/Kim & Robert"
        if "/" in name_text:
            # For slash patterns, split and analyze differently
            if "&" in name_text:
                # Pattern: "Name/Name & Name" → prefer name after &
                amp_parts = name_text.split("&")
                if len(amp_parts) > 1:
                    # Use the part after & as it often indicates preference
                    second_part = amp_parts[1].strip()
                    parsed_names = self._parse_person_name_parts(second_part)

                    # If no last name found, try to get it from first part
                    if not parsed_names.get("last_name"):
                        first_part = amp_parts[0].strip()
                        if "/" in first_part:
                            # Extract potential last name before slash
                            last_name_candidate = first_part.split("/")[0].strip()
                            parsed_names["last_name"] = last_name_candidate
                else:
                    # Just slash pattern: "Name/Name"
                    slash_parts = name_text.split("/")
                    first_part = slash_parts[0].strip()
                    parsed_names = self._parse_person_name_parts(first_part)
            else:
                # Just slash pattern: "Name/Name"
                slash_parts = name_text.split("/")
                first_part = slash_parts[0].strip()
                parsed_names = self._parse_person_name_parts(first_part)
        else:
            # Standard & or 'and' patterns
            parts = re.split(r"\s+(?:&|and)\s+", name_text, flags=re.IGNORECASE)
            if not parts:
                return self._empty_result()

            # Handle complex patterns like "Clark Jason R & Shari A"
            first_part = parts[0].strip()
            parsed_names = self._parse_person_name_parts(first_part)

        result = self._empty_result()
        result["first_name"] = parsed_names.get("first_name", "")
        result["last_name"] = parsed_names.get("last_name", "")
        result["entity_type"] = "person"
        result["parsing_method"] = "fallback"
        result["parsing_confidence"] = 0.8

        return result

    def _parse_individual_name(self, name_text: str) -> Dict[str, Optional[str]]:
        """Parse an individual person's name using enhanced heuristics"""
        result = self._empty_result()
        result["parsing_confidence"] = 0.6
        result["entity_type"] = "person"
        result["parsing_method"] = "fallback"

        # Check if it has "LastName, FirstName" pattern (with comma)
        if "," in name_text and name_text.count(",") == 1:
            parts = name_text.split(",")
            result["last_name"] = parts[0].strip()
            result["first_name"] = parts[1].strip()
        else:
            # Use standard person name parsing for non-trust individuals
            parsed_names = self._parse_person_name_parts(name_text)
            result["first_name"] = parsed_names.get("first_name", "")
            result["last_name"] = parsed_names.get("last_name", "")

        return result

    def parse_batch(self, names: List[str]) -> List[Dict[str, Optional[str]]]:
        """Parse a batch of names"""
        results = []
        for name in names:
            try:
                result = self.parse_name(name)
                results.append(result)
            except Exception as e:
                logger.error(f"Error parsing name '{name}': {e}")
                results.append(self._empty_result())

        return results

    def _extract_person_from_trust(self, trust_text: str) -> Dict[str, str]:
        """
        Extract person names from trust using name recognition instead of position
        Examples:
        - "Cole Beulah Revocable Trust" → {"first_name": "Cole", "last_name": "Beulah"}
        - "Mcculley Phyllis J Trust" → {"first_name": "Phyllis", "last_name": "Mcculley"}
        - "Birch Dale F Family Trust" → {"first_name": "Dale", "last_name": "Birch"}
        - "Cheslak Family Trust" → {"first_name": "", "last_name": "Cheslak"}
        - "Daake Dennis R. Living Trust" → {"first_name": "Dennis", "last_name": "Daake"}
        """

        # Step 1: Extract only name words
        words = trust_text.split()
        name_words = []

        for word in words:
            clean_word = word.strip(".,()").lower()
            original_word = word.strip(".,()")

            # Skip entity markers
            if clean_word in self.ENTITY_MARKERS:
                continue
            # Skip single letters (middle initials)
            if len(clean_word) == 1 and clean_word.isalpha():
                continue
            # Skip numbers
            if any(char.isdigit() for char in clean_word):
                continue

            name_words.append(original_word)

        if not name_words:
            return {"first_name": "", "last_name": ""}

        # Handle joint names with & or /
        joint_text = " ".join(name_words)
        if "&" in joint_text or "/" in joint_text:
            # Split on joint separator and take first person (prioritize male if identifiable)
            separator = "&" if "&" in joint_text else "/"
            parts = joint_text.split(separator)
            if parts:
                # TODO: Add gender detection for prioritization
                first_person = parts[0].strip()
                name_words = first_person.split()

        # Special handling for Family Trust
        if "family trust" in trust_text.lower():
            if len(name_words) == 1:
                # Single name family trust - use as last name only
                return {"first_name": "", "last_name": name_words[0]}
            # Multiple names in family trust - continue with name recognition

        # Step 2: Use name recognition to determine order
        if len(name_words) == 1:
            # Single name - default to last name for trusts
            return {"first_name": "", "last_name": name_words[0]}
        elif len(name_words) == 2:
            return self._recognize_two_names(name_words[0], name_words[1])
        else:
            # 3+ names - try to identify first and last
            # Check for compound surnames
            compound_last = self._check_compound_surname(name_words)
            if compound_last:
                # Found compound surname
                remaining = [w for w in name_words if w not in compound_last.split()]
                if remaining:
                    return self._recognize_name_with_known_last(
                        remaining[0], compound_last
                    )
                return {"first_name": "", "last_name": compound_last}

            # Default: use first two significant names
            return self._recognize_two_names(name_words[0], name_words[1])

    def _parse_trust_name_parts(self, name_text: str) -> Dict[str, str]:
        """
        Parse person names from trust context
        For trusts, the pattern is typically: LastName FirstName [Middle] Trust
        """
        parts = name_text.strip().split()
        if not parts:
            return {"first_name": "", "last_name": ""}

        # Remove middle initials (single letters with or without period)
        filtered_parts = []
        for part in parts:
            clean_part = part.strip(".,()").replace(",", "")
            # Skip single letters (middle initials)
            if len(clean_part) == 1 and clean_part.isalpha():
                continue
            # Skip if it's just an initial with period like "R." or "J."
            if len(part) <= 2 and "." in part:
                continue
            filtered_parts.append(clean_part)

        if len(filtered_parts) == 0:
            return {"first_name": "", "last_name": ""}
        elif len(filtered_parts) == 1:
            # Single name - treat as last name for trusts
            return {"first_name": "", "last_name": filtered_parts[0]}
        elif len(filtered_parts) == 2:
            # For trust context, assume LastName FirstName pattern
            # Example: "Cole Beulah" → last="Cole", first="Beulah"
            return {"first_name": filtered_parts[1], "last_name": filtered_parts[0]}
        else:
            # 3+ parts: first is last name, second is first name
            return {"first_name": filtered_parts[1], "last_name": filtered_parts[0]}

    def _parse_person_name_parts(self, name_text: str) -> Dict[str, str]:
        """
        Parse individual person name for non-trust entities
        Handles both FirstName LastName and LastName FirstName patterns
        """
        parts = name_text.strip().split()
        if not parts:
            return {"first_name": "", "last_name": ""}

        # Remove middle initials (single letters)
        filtered_parts = []
        for part in parts:
            clean_part = part.strip(".,()").replace(",", "")
            if len(clean_part) == 1 and clean_part.isalpha():
                continue  # Skip middle initials
            filtered_parts.append(clean_part)

        if len(filtered_parts) == 0:
            return {"first_name": "", "last_name": ""}
        elif len(filtered_parts) == 1:
            # Single name - could be first or last
            return {"first_name": filtered_parts[0], "last_name": ""}
        elif len(filtered_parts) == 2:
            # For non-trust persons, check the context
            first_part, second_part = filtered_parts

            # If there was a comma in the original text, it's LastName, FirstName
            if "," in name_text:
                return {"first_name": second_part, "last_name": first_part}

            # For agricultural/ownership data, the pattern is typically LastName FirstName
            # So default to that interpretation
            return {"first_name": second_part, "last_name": first_part}
        else:
            # 3+ parts: In agricultural data, pattern is LastName FirstName Middle...
            # So first part is last name, second is first name
            return {"first_name": filtered_parts[1], "last_name": filtered_parts[0]}

    def _looks_like_surname(self, name_part: str) -> bool:
        """Simple heuristic to detect if a name part looks like a surname"""
        return (
            len(name_part) > 4
            and not name_part.lower().endswith(("ie", "y", "a"))
            and name_part[0].isupper()
        )

    def _recognize_two_names(self, name1: str, name2: str) -> Dict[str, str]:
        """
        Determine which of two names is first vs last using dynamic scoring
        NO hardcoded default - each case evaluated individually
        """
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        # Calculate scores for each name (0-100 scale)
        name1_first_score = self._score_as_first_name(name1_lower)
        name1_last_score = self._score_as_last_name(name1_lower)
        name2_first_score = self._score_as_first_name(name2_lower)
        name2_last_score = self._score_as_last_name(name2_lower)

        # Calculate score differences
        name1_diff = abs(name1_last_score - name1_first_score)
        name2_diff = abs(name2_last_score - name2_first_score)

        # Determine order based on scores
        if (
            name1_last_score > name1_first_score
            and name2_first_score > name2_last_score
        ):
            # name1 strongly prefers last, name2 strongly prefers first
            # → LastName FirstName pattern
            return {"first_name": name2, "last_name": name1}
        elif (
            name1_first_score > name1_last_score
            and name2_last_score > name2_first_score
        ):
            # name1 strongly prefers first, name2 strongly prefers last
            # → FirstName LastName pattern
            return {"first_name": name1, "last_name": name2}
        elif name1_diff < 20 and name2_diff < 20:
            # Both names are ambiguous (score differences < 20)
            # Use additional heuristics

            # Check for gender indicators
            if name1_lower.endswith(("a", "y", "ie", "ine", "elle")):
                # name1 has female ending, more likely first name
                return {"first_name": name1, "last_name": name2}
            elif name2_lower.endswith(("a", "y", "ie", "ine", "elle")):
                # name2 has female ending, more likely first name
                return {"first_name": name2, "last_name": name1}

            # Check length (shorter names often first names)
            if len(name1) < len(name2) - 2:
                return {"first_name": name1, "last_name": name2}
            elif len(name2) < len(name1) - 2:
                return {"first_name": name2, "last_name": name1}

            # Apply dataset frequency heuristic
            # Property records show 70% LastName FirstName pattern
            # But only apply this as last resort
            if name1_last_score >= name2_last_score:
                return {"first_name": name2, "last_name": name1}
            else:
                return {"first_name": name1, "last_name": name2}
        else:
            # One name has clear preference, use that to guide decision
            if name1_diff > name2_diff:
                # name1 has stronger preference
                if name1_last_score > name1_first_score:
                    return {"first_name": name2, "last_name": name1}
                else:
                    return {"first_name": name1, "last_name": name2}
            else:
                # name2 has stronger preference
                if name2_last_score > name2_first_score:
                    return {"first_name": name1, "last_name": name2}
                else:
                    return {"first_name": name2, "last_name": name1}

    def _score_as_first_name(self, name_lower: str) -> int:
        """Calculate probability score that name is a first name (0-100 scale)"""
        # Base scores for very common first names
        very_common = {
            "john",
            "mary",
            "james",
            "linda",
            "robert",
            "patricia",
            "michael",
            "jennifer",
            "david",
            "elizabeth",
            "william",
            "barbara",
        }
        common = {
            "dennis",
            "phyllis",
            "warren",
            "marilyn",
            "edwin",
            "gloria",
            "virgil",
            "carl",
            "harold",
            "beverly",
            "donald",
            "nancy",
        }
        often = {"cole", "dale", "drew", "blake", "jordan", "tyler", "amber", "crystal"}
        sometimes = {"parker", "carter", "taylor", "morgan", "cameron", "hunter"}

        # Start with base score
        if name_lower in very_common:
            score = 95
        elif name_lower in common:
            score = 85
        elif name_lower in often:
            score = 75
        elif name_lower in sometimes:
            score = 65
        elif name_lower in self.COMMON_FIRST_NAMES:
            score = 80  # Default for other known first names
        else:
            score = 45  # Ambiguous default

        # Adjustments
        # Female name endings
        if name_lower.endswith(("y", "ie", "a", "ine", "elle", "ette", "een", "lyn")):
            score += 10

        # Length bonus for typical first names
        if 3 <= len(name_lower) <= 7:
            score += 5

        # Penalties
        # Has surname prefix
        for prefix in self.SURNAME_PREFIXES:
            if name_lower.startswith(prefix):
                score -= 20
                break

        # Has surname ending
        if name_lower.endswith(("son", "sen", "berg", "stein", "man", "mann")):
            score -= 15

        return max(0, min(100, score))  # Clamp to 0-100

    def _score_as_last_name(self, name_lower: str) -> int:
        """Calculate probability score that name is a last name (0-100 scale)"""
        # Base scores for common surnames
        very_common = {
            "smith",
            "johnson",
            "williams",
            "brown",
            "jones",
            "davis",
            "miller",
            "wilson",
            "moore",
            "taylor",
            "anderson",
            "thomas",
        }
        common = {
            "hansen",
            "peterson",
            "nelson",
            "robinson",
            "clark",
            "lewis",
            "walker",
            "hall",
            "allen",
            "young",
            "king",
            "wright",
            "lopez",
        }
        regional = {
            "mcculley",
            "daake",
            "pudenz",
            "chicoine",
            "birch",
            "cheslak",
            "glasnapp",
            "fry",
            "mills",
            "musselman",
            "petersen",
        }
        often = {"baker", "carter", "parker", "mason", "hunter", "turner", "cooper"}

        # Start with base score
        if name_lower in very_common:
            score = 95
        elif name_lower in common:
            score = 85
        elif name_lower in regional:
            score = 75
        elif name_lower in often:
            score = 65
        elif name_lower in self.COMMON_LAST_NAMES:
            score = 80  # Default for other known surnames
        else:
            score = 45  # Ambiguous default

        # Adjustments
        # Surname prefix bonus
        for prefix in self.SURNAME_PREFIXES:
            if name_lower.startswith(prefix):
                score += 20
                break

        # Surname ending bonus
        if name_lower.endswith(
            (
                "son",
                "sen",
                "berg",
                "stein",
                "man",
                "mann",
                "ley",
                "field",
                "ford",
                "wood",
                "worth",
                "ski",
                "wicz",
                "owski",
                "enko",
            )
        ):
            score += 15

        # Length bonus for typical surnames
        if 5 <= len(name_lower) <= 12:
            score += 10

        # Penalties
        # Common first name
        if name_lower in self.COMMON_FIRST_NAMES:
            score -= 10

        return max(0, min(100, score))  # Clamp to 0-100

    def _check_compound_surname(self, name_words: List[str]) -> Optional[str]:
        """Check if name words contain a compound surname"""
        for i, word in enumerate(name_words):
            word_lower = word.lower()
            for prefix in self.SURNAME_PREFIXES:
                if word_lower == prefix and i < len(name_words) - 1:
                    # Found surname prefix, combine with next word
                    return f"{word} {name_words[i + 1]}"

        # Check for hyphenated surnames
        for word in name_words:
            if "-" in word:
                return word

        return None

    def _recognize_name_with_known_last(
        self, first_candidate: str, last_name: str
    ) -> Dict[str, str]:
        """Helper when we know the last name and need to verify first name"""
        return {"first_name": first_candidate, "last_name": last_name}


# Global instance for reuse
_fallback_parser = None


def get_fallback_parser() -> FallbackNameParser:
    """Get or create the global fallback parser instance"""
    global _fallback_parser
    if _fallback_parser is None:
        _fallback_parser = FallbackNameParser()
    return _fallback_parser
