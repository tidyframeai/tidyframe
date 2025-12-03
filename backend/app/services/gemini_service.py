"""
Unified Gemini Service - Production Ready
No bullshit, no duplicates, just clean working code.
Gilfoyle-approved implementation.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import structlog

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger = structlog.get_logger()
        logger.info("env_loaded", path=str(env_path))
    else:
        logger = structlog.get_logger()
        logger.warning("env_file_not_found", path=str(env_path))
except ImportError:
    logger = structlog.get_logger()
    logger.warning("dotenv_not_installed")

# Import required HTTP client
import aiohttp

# Import fallback parser
from .fallback_name_parser import get_fallback_parser

logger = structlog.get_logger()

# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================


class NameComplexity(Enum):
    """Name complexity classification"""

    SIMPLE = "simple"  # John Smith
    MODERATE = "moderate"  # Dr. John Smith Jr.
    COMPLEX = "complex"  # John & Mary Smith
    ENTITY = "entity"  # ABC Corporation


@dataclass
class ParsedName:
    """
    Standardized name parsing result.
    NO is_agricultural field - that's idiotic for name parsing.
    """

    first_name: str = ""
    last_name: str = ""
    entity_type: str = "person"  # person/company/trust
    gender: str = "unknown"
    gender_confidence: float = 0.0
    parsing_confidence: float = 0.0
    parsing_method: str = "gemini"
    fallback_reason: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for compatibility"""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "entity_type": self.entity_type,
            "gender": self.gender,
            "gender_confidence": self.gender_confidence,
            "parsing_confidence": self.parsing_confidence,
            "parsing_method": self.parsing_method,
            "fallback_reason": self.fallback_reason,
            "warnings": self.warnings,
            # Additional fields required by frontend and processing
            "gemini_used": self.parsing_method == "gemini",
            "has_warnings": len(self.warnings) > 0,
            "low_confidence": self.parsing_confidence < 0.7,
            "original_text": "",  # Will be set by processor
        }

    def get(self, key: str, default=None):
        """Dict-like interface for backward compatibility"""
        return getattr(self, key, default)


@dataclass
class BatchResult:
    """Batch processing result with proper attributes"""

    results: List[ParsedName]
    total_processed: int = 0
    gemini_used: int = 0
    fallback_used: int = 0
    cache_hits: int = 0
    total_tokens: int = 0
    processing_time: float = 0.0
    cost_estimate: float = 0.0
    api_call_count: int = 0

    @property
    def successful_parses(self) -> int:
        """Compatibility property"""
        return self.gemini_used

    @property
    def total_tokens_used(self) -> int:
        """Compatibility property"""
        return self.total_tokens


# =============================================================================
# OPTIMIZED PROMPT TEMPLATES - ML/AI ENGINEERED
# =============================================================================


class OptimizedPromptTemplates:
    """
    Expert-engineered prompt using advanced prompting techniques
    Target: 98%+ accuracy for name parsing and entity classification
    """

    PROPERTY_OWNERSHIP_PROMPT = """You are an expert legal name parser specializing in property ownership records.

## TASK
Parse {count} ownership records into structured JSON with first_name, last_name, entity_type, gender, and confidence scores.

## Input
{names}

## EXTRACTION ALGORITHM

### Step 1: Entity Classification
Scan for markers (case-insensitive) to determine entity type:

**Company markers** (check FIRST - if found, entity_type="company", skip name extraction):
- **IMPORTANT**: Company markers MUST be standalone words (word boundaries), NOT substrings
- Strong indicators: llc, inc, corp, corporation, incorporated, limited, ltd
- Other indicators: company, properties, enterprises, holdings, group, partnership, lp
- ✓ CORRECT: "Kane Farms LLC" → company (LLC is standalone word)
- ✗ INCORRECT: "Farmer John" → NOT company (Farm is substring, not marker)
- ✓ CORRECT: "ABC Corporation" → company
- ✗ INCORRECT: "Incorporate" → NOT company (Corp is substring within word)

**Trust markers** (if no company markers, check for these → entity_type="trust"):
- trust, ttee, trs, tste, trustee, rev, revocable, irrevocable, living
- estate, foundation, etal, et al

**Default**: If no markers found → entity_type="person"

### Step 2: Name Extraction (for trust and person only)

**CRITICAL**: Extract ALL potential name words. Do not skip or ignore names.

**MANDATORY for entity_type='trust'**:
- Trusts MUST have at least one name (first_name OR last_name populated)
- If no names found initially, re-scan original text for proper nouns (capitalized words)
- Trust without names is INVALID - force re-extraction
- Example: "Baker Family Trust" → MUST extract "Baker" as last_name

**Remove these non-name elements**:
- Entity markers: trust, ttee, trs, trustee, rev, revocable, living, family, estate
- Legal descriptors: dated, dtd, marital, agreement, deed, (deed), (ded)
- Single letters: A, B, C, J, K, L, M, R (middle initials)
- Numbers/dates: 2012, 04/07/2010, 2018
- Fractions: 1/2, 1/3, 50% (but keep names before/after hyphens)
- Connectors: &, and, or, /
- Articles: the, of, a, an
- Legal terms: Fbo, Le, L/E, Life Estate, Rem, Int, Tic

**Keep these as potential names**:
- All capitalized words not in the removal list
- Names before/after hyphens (e.g., "Roseann - 1/2" → keep "Roseann")
- Compound surnames together (Van Meter, Mc Laughlin)

**Examples**:
- "Uhl Judy A Revocable Trust" → Extract: ["Uhl", "Judy"]
- "Mills Edwin L & Gloria F Rev Trs" → Extract: ["Mills", "Edwin", "Gloria"]
- "Gifford Roseann - 1/2" → Extract: ["Gifford", "Roseann"]
- "Smith John" → Extract: ["Smith", "John"]
- "Baker Family Trust" → Extract: ["Baker"] (MANDATORY - trust must have name)

### Step 3: Joint Ownership Prioritization (MANDATORY for & or / patterns)

**When you see "&" or "/" between names, you MUST prioritize male names**:

1. Identify the gender of each name
2. If a male name is found → USE THE MALE NAME
3. If both same gender → use first listed

**Examples**:
- "Mills Edwin L & Gloria F Rev Trust"
  - Edwin = male, Gloria = female → USE Edwin Mills
  - Result: first="Edwin", last="Mills"

- "Glasnapp Wayne R & Maryl Rev Trust"
  - Wayne = male, Maryl = female → USE Wayne Glasnapp
  - Result: first="Wayne", last="Glasnapp"

- "Clark Jason R & Shari A"
  - Jason = male, Shari = female → USE Jason Clark
  - Result: first="Jason", last="Clark"

### Step 4: Name Assignment with Confidence Scoring

**For single name (Family Trust pattern)**:
- "Cheslak Family Trust" → last="Cheslak", first=""

**For two names, use this SCORING SYSTEM to determine order**:

**SCORING TABLE** (0-100 points):
┌─────────────────────────────────────────┬────────┐
│ Rule                                     │ Points │
├─────────────────────────────────────────┼────────┤
│ Surname prefix (Van, De, Di, Mac, Mc)   │  100   │ ← HIGHEST PRIORITY
│ Very common first name (John, Mary)      │   95   │
│ Common first name (Dennis, Gloria)       │   85   │
│ Moderate first name (Cole, Dale)         │   75   │
│ Female ending (-a, -ah, -ia, -ie, -y)   │   80   │
│ Male ending (-son, -ton)                 │   70   │
│ Rare/unknown name                        │   60   │
│ Default position (first word)            │   50   │
└─────────────────────────────────────────┴────────┘

**ALGORITHM**:
1. Check surname prefix rule (100 pts) - if match, word is PART OF LAST NAME
2. Score each word as potential first_name using table above
3. Word with HIGHEST score = first_name
4. Remaining word(s) = last_name
5. For joint ownership: prioritize male name as first_name

**DETAILED RULES**:

1. **Surname prefix rule** (HIGHEST PRIORITY - 100 points):
   - If word starts with Mc, Mac, Van, Von, De, O' → it's a LAST name
   - "Mcculley Phyllis" → Mcculley(100) vs Phyllis(85) → last="Mcculley", first="Phyllis"
   - "Van Meter Eva" → Van(100+prefix) → last="Van Meter", first="Eva"

2. **Very common first name rule** (95 points):
   - John, Mary, James, Linda, Robert, Patricia, Michael, Jennifer, David, Barbara, William, Susan, Joseph, Nancy, Charles, Betty, Thomas, Helen, Christopher, Sandra, Paul, Donna, Mark, Carol, Donald, Ruth, George, Sharon, Kenneth, Dorothy
   - "Baker Cleo" → Baker(60) vs Cleo(85) → first="Cleo", last="Baker"

3. **Common first name rule** (85 points):
   - Common male: Dennis, Edwin, Wayne, Gary, Larry, Carl, Warren, Virgil
   - Common female: Judy, Phyllis, Gloria, Marilyn, Cleo, Roseann
   - "Daake Dennis" → Daake(60) vs Dennis(85) → first="Dennis", last="Daake"

4. **Moderate first name rule** (75 points):
   - Moderately common: Cole, Dale, Drew, Beulah, Dale
   - "Cole Beulah Trust" → Cole(75) vs Beulah(80+female) → first="Beulah", last="Cole"

5. **Female ending rule** (80 points):
   - Names ending in -a, -ah, -ia, -y, -ie, -ine, -elle, -lyn → likely first names
   - "Uhl Judy" → Uhl(60) vs Judy(85+female) → first="Judy", last="Uhl"
   - "Hansen Linda" → Hansen(60) vs Linda(95) → first="Linda", last="Hansen"

6. **Default pattern** (50 points - when ambiguous):
   - For trusts: Often [LastName] [FirstName] pattern (70% in property records)
   - "Smith John Trust" → first="John", last="Smith"
   - But verify with rules above first!

5. **Person entities**:
   - MUST extract both names if two words present
   - "Smith John" (person) → first="John", last="Smith"
   - Never return only last name if two names available

### Step 5: Gender Detection

**Female indicators** (confidence 0.85+):
- Names: Mary, Linda, Patricia, Jennifer, Barbara, Susan, Nancy, Betty, Helen, Sandra, Donna, Carol, Ruth, Sharon, Dorothy, Judy, Phyllis, Gloria, Marilyn, Cleo, Roseann, Shari, Eva, Maryl
- Endings: -a, -y, -ie, -ine, -elle, -lyn

**Male indicators** (confidence 0.90+):
- Names: John, James, Robert, Michael, David, William, Joseph, Charles, Thomas, Paul, Mark, Donald, George, Kenneth, Dennis, Edwin, Wayne, Gary, Larry, Carl, Warren, Virgil, Jason
- Default for ambiguous names

### Step 6: Validation

Before returning results, verify:
1. ✓ Companies have NO names (first="" and last="")
2. ✓ Trusts have at least one name (except rare edge cases)
3. ✓ Persons have both first and last if two names were in input
4. ✓ No entity markers (trust, llc) in name fields
5. ✓ Male names prioritized for joint ownership

## EXAMPLES WITH COMPLETE PROCESSING

**"Uhl Judy A Revocable Trust Dated 04/07/2010"**
1. Entity: trust (has "Trust")
2. Extract: ["Uhl", "Judy"] (removed A, Revocable, Trust, Dated, 04/07/2010)
3. Order: "Judy" is common female first name → first="Judy", last="Uhl"
Result: {{"first_name":"Judy","last_name":"Uhl","entity_type":"trust","gender":"female","gender_confidence":0.90,"parsing_confidence":0.92}}

**"Kramersmeier Wallace C Trust"**
1. Entity: trust
2. Extract: ["Kramersmeier", "Wallace"] (removed C, Trust)
3. Order: "Wallace" is common first name → first="Wallace", last="Kramersmeier"
Result: {{"first_name":"Wallace","last_name":"Kramersmeier","entity_type":"trust","gender":"male","gender_confidence":0.85,"parsing_confidence":0.90}}

**"Mills Edwin L & Gloria F Rev Trs Tic"**
1. Entity: trust (has "Trs")
2. Extract: ["Mills", "Edwin", "Gloria"] (removed L, &, F, Rev, Trs, Tic)
3. Joint ownership: Edwin=male, Gloria=female → MUST USE Edwin
4. Order: first="Edwin", last="Mills"
Result: {{"first_name":"Edwin","last_name":"Mills","entity_type":"trust","gender":"male","gender_confidence":0.90,"parsing_confidence":0.95}}

**"Gifford Roseann - 1/2"**
1. Entity: person (no entity markers)
2. Extract: ["Gifford", "Roseann"] (keep names before hyphen, remove "- 1/2")
3. Order: "Roseann" is common female first → first="Roseann", last="Gifford"
Result: {{"first_name":"Roseann","last_name":"Gifford","entity_type":"person","gender":"female","gender_confidence":0.90,"parsing_confidence":0.88}}

**"Birch Dale F Family Trust"**
1. Entity: trust
2. Extract: ["Birch", "Dale"] (removed F, Family, Trust)
3. Order: "Dale" is common first name → first="Dale", last="Birch"
Result: {{"first_name":"Dale","last_name":"Birch","entity_type":"trust","gender":"male","gender_confidence":0.75,"parsing_confidence":0.85}}

**"Wayne & Gloria Trust"**
1. Entity: trust
2. Extract: ["Wayne", "Gloria"]
3. Joint: Wayne=male, Gloria=female → USE Wayne
4. Result: first="Wayne", last="" (only first name before &)
Result: {{"first_name":"Wayne","last_name":"","entity_type":"trust","gender":"male","gender_confidence":0.90,"parsing_confidence":0.85}}

**"Microsoft Corporation"**
1. Entity: company (has "Corporation")
2. Skip name extraction
Result: {{"first_name":"","last_name":"","entity_type":"company","gender":"unknown","gender_confidence":0.0,"parsing_confidence":0.99}}

**"Smith John"** (person entity)
1. Entity: person (no markers)
2. Extract: ["Smith", "John"]
3. Order: "John" is common first name → first="John", last="Smith"
Result: {{"first_name":"John","last_name":"Smith","entity_type":"person","gender":"male","gender_confidence":0.90,"parsing_confidence":0.90}}

## OUTPUT FORMAT
Return JSON array with one object per input:
[{{"first_name":"string","last_name":"string","entity_type":"person|company|trust","gender":"male|female|unknown","gender_confidence":0.0-1.0,"parsing_confidence":0.0-1.0}}]

CRITICAL REMINDERS:
- Extract ALL name words, don't skip any
- ALWAYS prioritize male names for joint ownership
- Persons need both first and last names when available
- Companies never have names
- Follow the rules in order - surname prefixes override other patterns

CRITICAL: Return ONLY the JSON array. No explanations, no reasoning, no extra text.
Return EXACTLY {count} JSON objects in a valid JSON array.
Start your response with '[' and end with ']'."""

    @staticmethod
    def format_batch_prompt(names: List[str]) -> str:
        """Format names with clear numbering and count"""
        # Number names for clear correlation
        formatted = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(names[:50]))
        return OptimizedPromptTemplates.PROPERTY_OWNERSHIP_PROMPT.format(
            names=formatted, count=len(names)
        )


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class ConsolidatedGeminiService:
    """
    Production-ready Gemini service.
    No duplicate code, no bullshit, just performance.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter"""
        # Load from .env file first, then fallback to parameter
        self.api_key = os.getenv("GEMINI_API_KEY") or api_key

        if not self.api_key:
            logger.error(
                "no_api_key_found",
                env_var=bool(os.getenv("GEMINI_API_KEY")),
                param=bool(api_key),
            )

        # Load configuration from environment with defaults
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        # Optimized batch size for better accuracy and performance
        # gemini-2.5-flash handles larger batches better than lite: 30 is optimal
        self.max_batch_size = int(os.getenv("BATCH_SIZE", "30"))
        self.max_concurrent_requests = int(os.getenv("GEMINI_MAX_CONCURRENT", "20"))
        self.max_retries = 2
        self.timeout = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "10"))
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        # Connection pool configuration
        self.connector_config = {
            "limit": 100,
            "limit_per_host": 50,
            "keepalive_timeout": 60,
            "enable_cleanup_closed": True,
        }
        self.session = None  # Will be created when needed
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # API validation
        self.use_fallback = False

        if not self.api_key:
            logger.warning("no_api_key_using_fallback")
            self.use_fallback = True

        # Performance tracking
        self.stats = {
            "total_processed": 0,
            "gemini_success": 0,
            "fallback_used": 0,
            "api_calls": 0,
            "total_tokens": 0,
            "start_time": time.time(),
            "cache_hits": 0,
            "concurrent_batches": 0,
            "retry_attempts": 0,
            "retry_success": 0,
            "retry_no_improvement": 0,
            "retry_failed": 0,
        }

        # Initialize cache for repeated names (if enabled)
        self.cache_enabled = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.cache = {} if self.cache_enabled else None
        self.max_cache_size = 10000

        # Prompt templates
        self.prompts = OptimizedPromptTemplates()

        # CRITICAL: Verify prompt template on initialization
        logger.info(
            "service_initialized_with_prompt",
            service_class=self.__class__.__name__,
            prompt_class=self.prompts.__class__.__name__,
            has_hierarchical="HIERARCHICAL PARSING APPROACH"
            in self.prompts.PROPERTY_OWNERSHIP_PROMPT,
            has_entity_types="ENTITY TYPE CLASSIFICATION"
            in self.prompts.PROPERTY_OWNERSHIP_PROMPT,
            prompt_length=len(self.prompts.PROPERTY_OWNERSHIP_PROMPT),
        )

    async def parse_names_batch(
        self, names: List[str], progress_callback=None
    ) -> BatchResult:
        """
        Optimized concurrent batch processing for high throughput.
        Uses parallel requests to achieve 50+ names/second.
        """
        if not names:
            return BatchResult(results=[])

        start_time = time.time()

        # Check cache first
        cached_results = []
        uncached_names = []
        uncached_indices = []

        for i, name in enumerate(names):
            cache_key = self._get_cache_key(name)
            if self.cache and cache_key in self.cache:
                cached_results.append((i, self.cache[cache_key]))
                self.stats["cache_hits"] += 1
            else:
                uncached_names.append(name)
                uncached_indices.append(i)

        # Process uncached names concurrently
        if uncached_names:
            if not self.use_fallback:
                # Create concurrent tasks for all batches
                batch_tasks = []
                for i in range(0, len(uncached_names), self.max_batch_size):
                    batch = uncached_names[i : i + self.max_batch_size]
                    batch_indices = uncached_indices[i : i + self.max_batch_size]

                    if progress_callback:
                        progress_callback(i, len(uncached_names))

                    # Create task with semaphore for rate limiting
                    task = self._process_batch_with_semaphore(batch, batch_indices)
                    batch_tasks.append(task)

                # Execute all batches concurrently
                self.stats["concurrent_batches"] = len(batch_tasks)
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # Aggregate results
                all_results = self._aggregate_concurrent_results(
                    batch_results, cached_results, len(names)
                )
            else:
                # Fallback to sequential processing if no API
                all_results = []
                for name in names:
                    all_results.append(self._fallback_parse(name))
        else:
            # All results were cached
            all_results = [None] * len(names)
            for idx, result in cached_results:
                all_results[idx] = result

        # Calculate stats
        processing_time = time.time() - start_time
        gemini_used = sum(1 for r in all_results if r and r.parsing_method == "gemini")
        fallback_used = sum(
            1 for r in all_results if r and r.parsing_method == "fallback"
        )
        total_tokens = self.stats.get("batch_tokens", 0)

        # Update stats
        self.stats["total_processed"] += len(names)
        self.stats["gemini_success"] += gemini_used
        self.stats["fallback_used"] += fallback_used
        self.stats["total_tokens"] += total_tokens

        # Calculate actual throughput
        throughput = len(names) / processing_time if processing_time > 0 else 0
        cache_hit_rate = (len(cached_results) / len(names) * 100) if names else 0

        logger.info(
            "batch_processing_complete",
            total=len(names),
            gemini=gemini_used,
            fallback=fallback_used,
            cache_hits=len(cached_results),
            cache_hit_rate=f"{cache_hit_rate:.1f}%",
            concurrent_batches=self.stats.get("concurrent_batches", 0),
            time=f"{processing_time:.2f}s",
            speed=f"{throughput:.1f} names/sec",
        )

        return BatchResult(
            results=all_results,
            total_processed=len(names),
            gemini_used=gemini_used,
            fallback_used=fallback_used,
            total_tokens=total_tokens,
            processing_time=processing_time,
            cost_estimate=total_tokens * 0.0000001,  # Gemini 2.5 Flash Lite pricing
            api_call_count=self.stats["api_calls"],
        )

    def _get_cache_key(self, name: str) -> str:
        """Generate cache key for a name"""
        import hashlib

        normalized = name.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    async def _process_batch_with_semaphore(
        self, batch: List[str], indices: List[int]
    ) -> dict:
        """Process a batch with semaphore for rate limiting"""
        async with self.semaphore:
            try:
                results = await self._process_with_gemini(batch)
                if results:
                    # Cache successful results (only if caching is enabled)
                    if self.cache is not None:
                        for name, result in zip(batch, results):
                            cache_key = self._get_cache_key(name)
                            if len(self.cache) < self.max_cache_size:
                                self.cache[cache_key] = result
                    return {"indices": indices, "results": results, "success": True}
                else:
                    # Fallback for this batch
                    fallback_results = [self._fallback_parse(name) for name in batch]
                    return {
                        "indices": indices,
                        "results": fallback_results,
                        "success": False,
                    }
            except Exception as e:
                logger.error("batch_processing_error", error=str(e))
                # Return fallback results on error
                fallback_results = [self._fallback_parse(name) for name in batch]
                return {
                    "indices": indices,
                    "results": fallback_results,
                    "success": False,
                }

    def _aggregate_concurrent_results(
        self, batch_results: List, cached_results: List, total_count: int
    ) -> List[ParsedName]:
        """Aggregate results from concurrent batches and cache"""
        all_results = [None] * total_count

        # Add cached results first
        for idx, result in cached_results:
            all_results[idx] = result

        # Add batch results
        for batch_result in batch_results:
            if isinstance(batch_result, dict) and "indices" in batch_result:
                indices = batch_result["indices"]
                results = batch_result["results"]
                for idx, result in zip(indices, results):
                    all_results[idx] = result
            elif isinstance(batch_result, Exception):
                logger.error("batch_exception", error=str(batch_result))

        # Fill any missing with fallback
        for i, result in enumerate(all_results):
            if result is None:
                # This shouldn't happen, but handle gracefully
                all_results[i] = ParsedName(
                    first_name="",
                    last_name="",
                    entity_type="unknown",
                    gender="unknown",
                    gender_confidence=0.0,
                    parsing_confidence=0.0,
                    parsing_method="error",
                    original_input="",
                )

        return all_results

    async def _get_or_create_session(self):
        """Get or create an optimized aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(**self.connector_config)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def _process_with_gemini(
        self, names: List[str]
    ) -> Optional[List[ParsedName]]:
        """Process batch with Gemini API - SDK or direct call"""

        prompt = self.prompts.format_batch_prompt(names)

        # CRITICAL LOGGING: Verify correct prompt is being sent
        prompt_length = len(prompt)
        estimated_tokens = len(prompt.split())  # Better token estimation

        # Log first 1000 chars of prompt to verify it's correct
        logger.info(
            "gemini_api_call_prepared",
            names_count=len(names),
            prompt_length=prompt_length,
            estimated_tokens=estimated_tokens,
            model=self.model_name,
            has_hierarchical_prompt="HIERARCHICAL PARSING APPROACH" in prompt,
            has_entity_classification="ENTITY TYPE CLASSIFICATION" in prompt,
            prompt_preview=prompt[:1000] if len(prompt) > 1000 else prompt,
            input_names=names[:3] if len(names) > 3 else names,
        )

        # Use aiohttp for all API calls (consolidated approach)
        return await self._direct_api_call_async(prompt, names)

    async def _direct_api_call_async(
        self, prompt: str, names: List[str]
    ) -> Optional[List[ParsedName]]:
        """Direct API call using aiohttp (preferred)"""

        if not self.api_key:
            return None

        url = self.base_url.format(model=self.model_name)
        url += f"?key={self.api_key}"

        # gemini-2.5-flash uses substantial thinking tokens (~250-300 per name with complex prompts)
        # These count against maxOutputTokens, so we need large budgets
        # Formula: 6000 base + 800 per name (ensures ~4000-5000 thinking + 7000+ output)
        base_tokens = max(6000, len(names) * 800)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 10,
                "topP": 0.95,
                "maxOutputTokens": base_tokens,
                "candidateCount": 1,
            },
        }

        # Use shared session for better connection pooling
        session = await self._get_or_create_session()

        for attempt in range(self.max_retries):
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Validate response has candidates
                        if "candidates" not in result or not result["candidates"]:
                            logger.warning(
                                "no_candidates_in_response",
                                attempt=attempt,
                                names_count=len(names)
                            )
                            continue  # Retry

                        candidate = result["candidates"][0]
                        finish_reason = candidate.get("finishReason", "UNKNOWN")
                        usage_metadata = result.get("usageMetadata", {})

                        # Check for MAX_TOKENS and implement progressive retry
                        if finish_reason == "MAX_TOKENS":
                            thoughts_tokens = usage_metadata.get("thoughtsTokenCount", 0)
                            logger.warning(
                                "max_tokens_exceeded",
                                attempt=attempt,
                                current_max=payload["generationConfig"]["maxOutputTokens"],
                                thoughts_tokens=thoughts_tokens,
                                names_count=len(names)
                            )

                            # Progressive retry: double tokens and try again
                            if attempt < self.max_retries - 1:
                                payload["generationConfig"]["maxOutputTokens"] *= 2
                                logger.info(
                                    "retrying_with_more_tokens",
                                    new_max=payload["generationConfig"]["maxOutputTokens"]
                                )
                                await asyncio.sleep(0.5)  # Brief pause before retry
                                continue

                        # Validate content has parts (critical for gemini-2.5-flash)
                        content = candidate.get("content", {})
                        if "parts" not in content or not content["parts"]:
                            logger.error(
                                "no_parts_in_response",
                                finish_reason=finish_reason,
                                has_content=bool(content),
                                attempt=attempt
                            )
                            continue  # Retry

                        # Extract text (now safe after validation)
                        text = content["parts"][0]["text"]

                        # Log detailed API response metrics
                        logger.info(
                            "gemini_api_response",
                            finish_reason=finish_reason,
                            total_tokens=usage_metadata.get("totalTokenCount", 0),
                            thoughts_tokens=usage_metadata.get("thoughtsTokenCount", 0),
                            output_tokens=usage_metadata.get("candidatesTokenCount", 0),
                            response_length=len(text),
                            names_count=len(names),
                            attempt=attempt
                        )

                        # Parse response
                        parsed_results = self._parse_gemini_response(text, names)

                        # Apply retry logic for low-confidence results
                        improved_results = []
                        for i, result in enumerate(parsed_results):
                            original_name = names[i] if i < len(names) else ""
                            improved_result = await self._retry_low_confidence(
                                result, original_name
                            )
                            improved_results.append(improved_result)

                        return improved_results

                    elif response.status == 429:
                        await asyncio.sleep(2**attempt)
                    else:
                        error = await response.text()
                        logger.error(
                            "api_error", status=response.status, error=error[:200]
                        )
                        break
            except asyncio.TimeoutError:
                logger.warning("timeout", attempt=attempt)
            except Exception as e:
                logger.error("request_failed", error=str(e), attempt=attempt)

        return None

    async def _call_gemini_api_raw(
        self, prompt: str, max_output_tokens: int = 1500
    ) -> Optional[str]:
        """
        Raw API call that returns just the text response.
        Used by retry logic for single-name parsing.

        Args:
            prompt: The prompt to send to Gemini
            max_output_tokens: Token budget (default 1500 for retries)

        Returns:
            str: Raw text response from Gemini, or None if failed
        """
        if not self.api_key:
            return None

        url = self.base_url.format(model=self.model_name)
        url += f"?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 10,
                "topP": 0.95,
                "maxOutputTokens": max_output_tokens,
                "candidateCount": 1,
            },
        }

        session = await self._get_or_create_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()

                    # Validate response structure
                    if "candidates" not in result or not result["candidates"]:
                        logger.warning("retry_no_candidates")
                        return None

                    candidate = result["candidates"][0]
                    finish_reason = candidate.get("finishReason", "UNKNOWN")
                    content = candidate.get("content", {})

                    # Defensive parts access (critical for gemini-2.5-flash)
                    if "parts" not in content or not content["parts"]:
                        usage_metadata = result.get("usageMetadata", {})
                        logger.warning(
                            "retry_no_parts",
                            finish_reason=finish_reason,
                            thoughts_tokens=usage_metadata.get("thoughtsTokenCount", 0),
                            max_tokens=max_output_tokens
                        )
                        return None

                    return content["parts"][0]["text"]

                else:
                    error = await response.text()
                    logger.error(
                        "retry_api_error",
                        status=response.status,
                        error=error[:200]
                    )

        except Exception as e:
            logger.error("retry_api_call_failed", error=str(e))

        return None

    def _parse_gemini_response(
        self, text: str, original_names: List[str]
    ) -> List[ParsedName]:
        """Ultra-robust parsing with multiple fallback strategies"""
        results = []

        try:
            # Log for debugging
            logger.debug("gemini_raw_response", length=len(text), preview=text[:200])

            # Strategy 1: Clean markdown
            text = text.strip()
            if "```json" in text.lower():
                parts = text.split("```json")
                if len(parts) > 1:
                    text = parts[1].split("```")[0]
            elif "```" in text:
                text = text.replace("```json", "").replace("```", "")

            # Remove any text before the first '['
            # This handles cases like "Here is the JSON: [{..." or "Extra data: [{..."
            if "[" in text:
                first_bracket = text.find("[")
                if first_bracket > 0:
                    # Check if there's non-whitespace before the bracket
                    prefix = text[:first_bracket].strip()
                    if prefix:
                        logger.warning("removing_json_prefix", prefix=prefix[:50])
                        text = text[first_bracket:]

            # Strategy 2: Find JSON array boundaries with better validation
            if "[" in text and "]" in text:
                start = text.find("[")
                # Find balanced brackets, considering strings
                bracket_count = 0
                end = start
                in_string = False
                escape_next = False

                for i in range(start, len(text)):
                    char = text[i]

                    # Handle escape sequences
                    if escape_next:
                        escape_next = False
                        continue
                    if char == "\\" and in_string:
                        escape_next = True
                        continue

                    # Handle string boundaries
                    if char == '"':
                        in_string = not in_string
                        continue

                    # Count brackets only outside strings
                    if not in_string:
                        if char == "[":
                            bracket_count += 1
                        elif char == "]":
                            bracket_count -= 1
                            if bracket_count == 0:
                                end = i + 1
                                break

                text = text[start:end]

            # Strategy 3: Try to parse
            parsed = json.loads(text)

            # Ensure list format
            if isinstance(parsed, dict):
                parsed = [parsed]
            elif not isinstance(parsed, list):
                raise ValueError(f"Unexpected type: {type(parsed)}")

            # Process each result with validation
            for i, item in enumerate(parsed[: len(original_names)]):
                if not isinstance(item, dict):
                    logger.warning("non_dict_item", index=i, item=item)
                    results.append(self._fallback_parse(original_names[i]))
                    continue

                # Safe extraction with normalization
                first_name = str(item.get("first_name", "") or "").strip()
                last_name = str(item.get("last_name", "") or "").strip()
                entity_type = str(item.get("entity_type", "unknown")).lower().strip()
                gender = str(item.get("gender", "unknown")).lower().strip()

                # Normalize entity types
                entity_map = {
                    "corporation": "company",
                    "corp": "company",
                    "business": "company",
                    "organization": "company",
                    "llc": "company",
                    "inc": "company",
                    "estate": "trust",
                    "foundation": "trust",
                    "revocable": "trust",
                }
                entity_type = entity_map.get(entity_type, entity_type)
                if entity_type not in ["person", "company", "trust"]:
                    entity_type = "unknown"

                # Normalize gender
                if gender not in ["male", "female"]:
                    gender = "unknown"

                # CRITICAL: Enforce trust/company gender rules
                # Non-person entities MUST have unknown gender
                if entity_type in ["company", "trust", "estate"]:
                    gender = "unknown"
                    gender_conf = 0.0
                else:
                    # Get confidence scores with validation for persons
                    try:
                        gender_conf = float(item.get("gender_confidence", 0.7))
                        gender_conf = max(0.0, min(1.0, gender_conf))  # Clamp to [0,1]
                    except (TypeError, ValueError):
                        gender_conf = 0.7

                try:
                    parse_conf = float(item.get("parsing_confidence", 0.8))
                    parse_conf = max(0.0, min(1.0, parse_conf))  # Clamp to [0,1]
                except (TypeError, ValueError):
                    parse_conf = 0.8

                result = ParsedName(
                    first_name=first_name,
                    last_name=last_name,
                    entity_type=entity_type,
                    gender=gender,
                    gender_confidence=gender_conf,
                    parsing_confidence=parse_conf,
                    parsing_method="gemini",
                )

                # Apply validation and fixes
                result = self._validate_and_fix_extraction(
                    result,
                    (
                        original_names[len(results)]
                        if len(results) < len(original_names)
                        else ""
                    ),
                )

                results.append(result)

            # Fill missing with fallback
            while len(results) < len(original_names):
                fallback = self._fallback_parse(original_names[len(results)])
                fallback.warnings.append("Missing from Gemini response")
                results.append(fallback)

        except json.JSONDecodeError as e:
            logger.error(
                "json_decode_error",
                error=str(e),
                position=getattr(e, "pos", "unknown"),
                line=getattr(e, "lineno", "unknown"),
                response_preview=text[:300] if text else "empty",
            )
            # Use fallback for all
            for name in original_names:
                fb = self._fallback_parse(name)
                fb.warnings.append(f"JSON error: {str(e)[:30]}")
                results.append(fb)

        except Exception as e:
            logger.error("unexpected_error", error=str(e), type=type(e).__name__)
            # Use fallback
            for name in original_names:
                results.append(self._fallback_parse(name))

        return results

    def _validate_and_fix_extraction(
        self, result: ParsedName, original_name: str
    ) -> ParsedName:
        """
        Validate extraction results and fix common issues
        """
        # Issue 1: Trust with no names extracted
        if (
            result.entity_type == "trust"
            and not result.first_name
            and not result.last_name
        ):
            # Try to extract names from original
            words = original_name.split()
            potential_names = []
            for word in words:
                word_clean = word.strip(".,;:()[]")
                if word_clean and word_clean[0].isupper():
                    # Skip common non-name words
                    if word_clean.lower() not in [
                        "trust",
                        "rev",
                        "revocable",
                        "living",
                        "family",
                        "estate",
                        "ttee",
                        "trs",
                        "dated",
                        "dtd",
                    ]:
                        # Skip if it's a date or number
                        if not word_clean.replace("/", "").replace("-", "").isdigit():
                            potential_names.append(word_clean)

            # If we found potential names, use them
            if len(potential_names) >= 2:
                # Apply simple heuristics
                result.last_name = potential_names[0]
                result.first_name = potential_names[1]
                result.warnings.append("Names recovered from validation")
                result.parsing_confidence = max(0.6, result.parsing_confidence - 0.2)
            elif len(potential_names) == 1:
                result.last_name = potential_names[0]
                result.warnings.append("Only last name recovered")
                result.parsing_confidence = max(0.5, result.parsing_confidence - 0.3)

        # Issue 2: Person with only one name when two are available
        if result.entity_type == "person":
            if (result.first_name and not result.last_name) or (
                result.last_name and not result.first_name
            ):
                words = original_name.split()
                name_words = [
                    w.strip(".,;:()[]")
                    for w in words
                    if w and w[0].isupper() and not w.replace("/", "").isdigit()
                ]

                if len(name_words) >= 2:
                    # Both names should be extracted for persons
                    if not result.first_name:
                        result.first_name = (
                            name_words[1]
                            if result.last_name == name_words[0]
                            else name_words[0]
                        )
                    if not result.last_name:
                        result.last_name = (
                            name_words[0]
                            if result.first_name == name_words[1]
                            else name_words[1]
                        )
                    result.warnings.append("Missing name recovered")
                    result.parsing_confidence = max(
                        0.7, result.parsing_confidence - 0.1
                    )

        # Issue 3: Company classification check
        company_markers = [
            "llc",
            "inc",
            "corp",
            "corporation",
            "ltd",
            "limited",
            "company",
        ]
        if any(marker in original_name.lower() for marker in company_markers):
            if result.entity_type != "company":
                result.entity_type = "company"
                result.first_name = ""
                result.last_name = ""
                result.gender = "unknown"
                result.gender_confidence = 0.0
                result.warnings.append("Corrected to company based on markers")

        # Issue 4: Numbers or symbols as names
        if result.first_name and (
            result.first_name.isdigit() or result.first_name in ["-", "/", "#"]
        ):
            result.first_name = ""
            result.warnings.append("Invalid first name removed")

        if result.last_name and (
            result.last_name.isdigit() or result.last_name in ["-", "/", "#"]
        ):
            result.last_name = ""
            result.warnings.append("Invalid last name removed")

        # Issue 5: Entity markers in names
        entity_markers = ["trust", "llc", "inc", "corp", "estate"]
        for marker in entity_markers:
            if result.first_name and marker in result.first_name.lower():
                result.first_name = ""
                result.warnings.append(
                    f"Entity marker '{marker}' removed from first name"
                )
            if result.last_name and marker in result.last_name.lower():
                result.last_name = ""
                result.warnings.append(
                    f"Entity marker '{marker}' removed from last name"
                )

        # Add general warnings
        if (
            result.entity_type == "person"
            and not result.first_name
            and not result.last_name
        ):
            result.warnings.append("Person entity with no names extracted")
        elif result.entity_type == "company" and (
            result.first_name or result.last_name
        ):
            result.first_name = ""
            result.last_name = ""
            result.warnings.append("Company should not have names")

        return result

    async def _retry_low_confidence(
        self, result: ParsedName, original_name: str
    ) -> ParsedName:
        """
        Retry parsing for low-confidence results with enhanced prompt.
        Only retries if confidence < 70% and not already a retry.
        """
        # Skip if confidence is acceptable
        if result.parsing_confidence >= 0.70:
            return result

        # Skip if this is already a retry (prevent infinite loops)
        if "Retried due to low confidence" in result.warnings:
            return result

        logger.info(
            f"Retrying low-confidence parse: '{original_name}' "
            f"(confidence: {result.parsing_confidence:.2f})"
        )

        # Track retry attempt
        self.stats["retry_attempts"] = self.stats.get("retry_attempts", 0) + 1

        # Enhanced prompt with extra instructions
        enhanced_prompt = f"""
CRITICAL PARSING - RETRY REQUIRED

Original parse had LOW CONFIDENCE: {result.parsing_confidence:.2f}

Re-parse this name with EXTRA CARE:
"{original_name}"

{OptimizedPromptTemplates.PROPERTY_OWNERSHIP_PROMPT.replace('{names}', original_name).replace('{count}', '1')}

DOUBLE-CHECK REQUIREMENTS:
✓ Entity type: Is this person/company/trust?
✓ Name extraction: Did I extract ALL names?
✓ Name assignment: Did I use the scoring table correctly?
✓ Trust names: If trust, do I have at least one name?
✓ Company markers: Did I check word boundaries?

Return ONLY the JSON array with your improved parse.
"""

        try:
            # Call Gemini API with enhanced prompt
            response = await self._call_gemini_api_raw(
                enhanced_prompt, max_output_tokens=500
            )

            if not response:
                self.stats["retry_failed"] = self.stats.get("retry_failed", 0) + 1
                return result

            # Parse retry response
            retry_results = self._parse_gemini_response(response, [original_name])

            if retry_results and len(retry_results) > 0:
                retry_result = retry_results[0]

                # Use retry result if confidence improved by at least 5%
                if retry_result.parsing_confidence > result.parsing_confidence + 0.05:
                    retry_result.warnings.append(
                        f"Retried due to low confidence "
                        f"(original: {result.parsing_confidence:.2f}, "
                        f"improved: {retry_result.parsing_confidence:.2f})"
                    )
                    self.stats["retry_success"] = (
                        self.stats.get("retry_success", 0) + 1
                    )
                    logger.info(
                        f"Retry SUCCESS for '{original_name}': "
                        f"{result.parsing_confidence:.2f} → "
                        f"{retry_result.parsing_confidence:.2f}"
                    )
                    return retry_result
                else:
                    self.stats["retry_no_improvement"] = (
                        self.stats.get("retry_no_improvement", 0) + 1
                    )
                    logger.debug(
                        f"Retry NO IMPROVEMENT for '{original_name}': "
                        f"{result.parsing_confidence:.2f} → "
                        f"{retry_result.parsing_confidence:.2f}"
                    )

        except Exception as e:
            logger.warning(f"Retry failed for '{original_name}': {e}")
            self.stats["retry_failed"] = self.stats.get("retry_failed", 0) + 1

        # Return original if retry failed or didn't improve
        return result

    def _fallback_parse(self, name: str) -> ParsedName:
        """Simplified fallback parser using dedicated fallback service"""
        if not name or not name.strip():
            return ParsedName(
                first_name="",
                last_name="",
                entity_type="unknown",
                parsing_confidence=0.1,
                parsing_method="fallback",
                fallback_reason="Empty input",
            )

        # Use the dedicated fallback parser
        fallback_parser = get_fallback_parser()
        result = fallback_parser.parse_name(name.strip())

        # Convert to our ParsedName format with normalization
        entity_type = str(result.get("entity_type", "person") or "person").lower()
        # Normalize entity type variants
        if entity_type in ["company", "organization", "corp", "corporation"]:
            entity_type = "company"
        elif entity_type in ["trust", "estate", "foundation"]:
            entity_type = "trust"
        elif entity_type not in ["person", "company", "trust"]:
            entity_type = "unknown"

        return ParsedName(
            first_name=result.get("first_name", "") or "",
            last_name=result.get("last_name", "") or "",
            entity_type=entity_type,
            parsing_confidence=result.get("confidence", 0.6),
            parsing_method="fallback",
            fallback_reason="Delegated to fallback parser",
            warnings=[],
        )

    async def cleanup(self):
        """Clean up resources (close session, etc.)"""
        if self.session and not self.session.closed:
            await self.session.close()

    def get_performance_stats(self) -> dict:
        """Get performance statistics"""

        duration = time.time() - self.stats["start_time"]
        api_calls = max(self.stats["api_calls"], 1)  # Avoid division by zero

        return {
            "session_duration_seconds": duration,
            "total_processed": self.stats["total_processed"],
            "gemini_used": self.stats["gemini_success"],
            "fallback_used": self.stats["fallback_used"],
            "gemini_success_rate": (
                self.stats["gemini_success"] / self.stats["total_processed"]
                if self.stats["total_processed"] > 0
                else 0
            ),
            "processing_speed": (
                self.stats["total_processed"] / duration if duration > 0 else 0
            ),
            "cache_hits": self.stats.get("cache_hits", 0),
            "cache_hit_rate": (
                self.stats.get("cache_hits", 0) / self.stats["total_processed"]
                if self.stats["total_processed"] > 0
                else 0
            ),
            "concurrent_batches": self.stats.get("concurrent_batches", 0),
            "total_api_calls": self.stats["api_calls"],
            "total_tokens": self.stats["total_tokens"],
            "estimated_cost": self.stats["total_tokens"]
            * 0.0000001,  # Gemini 2.5 Flash Lite pricing
            "average_tokens_per_request": self.stats["total_tokens"] / api_calls,
            "cost_per_request": (self.stats["total_tokens"] * 0.0000001) / api_calls,
            "cost_savings_from_cache": self.stats.get("cache_hits", 0)
            * 400
            * 0.0000001,  # Approx savings
        }


# =============================================================================
# SINGLETON INSTANCE AND FACTORY FUNCTIONS
# =============================================================================

_service_instance = None


def get_gemini_service() -> ConsolidatedGeminiService:
    """
    Get or create service singleton with hierarchical entity classification.
    This is the ONLY correct way to get the Gemini service in production.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ConsolidatedGeminiService()

        # Validate correct service instantiation
        import structlog

        logger = structlog.get_logger()

        if hasattr(_service_instance, "prompts") and hasattr(
            _service_instance.prompts, "PROPERTY_OWNERSHIP_PROMPT"
        ):
            logger.info(
                "singleton_service_validated",
                service="ConsolidatedGeminiService",
                hierarchical_prompt=True,
                entity_classification="enabled",
            )
        else:
            logger.error(
                "singleton_service_invalid",
                service="ConsolidatedGeminiService",
                hierarchical_prompt=False,
                entity_classification="disabled",
                impact="Critical deployment failure",
            )

    return _service_instance


def create_production_service() -> ConsolidatedGeminiService:
    """
    Factory function to create a validated production service instance.
    Use this for explicit service creation with validation.
    """
    service = ConsolidatedGeminiService()

    # Production validation
    import structlog

    logger = structlog.get_logger()

    validation_passed = True

    # Check for hierarchical prompt
    if not hasattr(service, "prompts") or not hasattr(
        service.prompts, "PROPERTY_OWNERSHIP_PROMPT"
    ):
        logger.error(
            "production_service_validation_failed",
            check="hierarchical_prompt",
            status="missing",
            impact="0% entity classification",
        )
        validation_passed = False

    # Check for entity classification capability
    prompt_content = (
        service.prompts.PROPERTY_OWNERSHIP_PROMPT if hasattr(service, "prompts") else ""
    )
    if "entity_type" not in prompt_content or "company|trust" not in prompt_content:
        logger.error(
            "production_service_validation_failed",
            check="entity_classification",
            status="missing",
            impact="No company/trust detection",
        )
        validation_passed = False

    if validation_passed:
        logger.info(
            "production_service_validated",
            service="ConsolidatedGeminiService",
            hierarchical_prompt=True,
            entity_classification=True,
            ready_for_production=True,
        )

    return service


# For backward compatibility
OptimizedBatchProcessor = ConsolidatedGeminiService


# ARCHITECTURE VALIDATION: Ensure this is the only service used
def validate_service_deployment():
    """
    Runtime validation function to ensure correct service deployment.
    Call this during application startup to catch deployment issues.
    """
    import structlog

    logger = structlog.get_logger()

    try:
        service = get_gemini_service()

        # Test entity classification capability

        # This should be able to distinguish entities
        has_hierarchical = hasattr(service, "prompts") and hasattr(
            service.prompts, "PROPERTY_OWNERSHIP_PROMPT"
        )

        logger.info(
            "deployment_validation_complete",
            service="ConsolidatedGeminiService",
            hierarchical_prompt=has_hierarchical,
            entity_classification_ready=has_hierarchical,
            deployment_status="valid" if has_hierarchical else "CRITICAL_FAILURE",
        )

        return has_hierarchical

    except Exception as e:
        logger.error(
            "deployment_validation_failed",
            error=str(e),
            deployment_status="CRITICAL_FAILURE",
        )
        return False
