"""
High-Performance Cache Manager for Name Parsing Operations

Provides intelligent caching with duplicate detection, TTL management,
and production-ready performance optimization.
"""

import hashlib
import json
import sqlite3
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class CachedResult:
    """Cached parsing result with metadata"""

    first_name: str
    last_name: str
    entity_type: str
    gender: str
    gender_confidence: float
    parsing_confidence: float
    is_agricultural: bool
    warnings: List[str]
    cached_at: float
    access_count: int = 0
    last_accessed: float = 0.0


class NameCacheManager:
    """High-performance cache manager optimized for name parsing operations"""

    def __init__(self, max_memory_cache: int = 5000, ttl_hours: int = 24):
        self.max_memory_cache = max_memory_cache
        self.ttl_seconds = ttl_hours * 3600

        # In-memory cache with LRU eviction
        self._memory_cache: OrderedDict[str, CachedResult] = OrderedDict()
        self._cache_lock = threading.RLock()

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "duplicate_detections": 0,
            "memory_cache_size": 0,
            "disk_cache_size": 0,
        }

        # Duplicate detection system
        self._similarity_index = defaultdict(
            set
        )  # normalized_name -> set of cache_keys
        self._exact_duplicates = {}  # cache_key -> original_cache_key

        # Initialize persistent storage
        self._init_persistent_cache()

        # Performance optimization
        self._batch_updates = []  # For batching disk writes
        self._batch_lock = threading.Lock()
        self._last_batch_flush = time.time()

    def _init_persistent_cache(self):
        """Initialize SQLite database for persistent caching"""
        cache_dir = Path("/tmp/tidyframe_cache")
        cache_dir.mkdir(exist_ok=True)

        self.db_path = cache_dir / "name_parsing_cache.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS name_cache (
                    cache_key TEXT PRIMARY KEY,
                    original_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    UNIQUE(cache_key)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_normalized_text
                ON name_cache(normalized_text)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON name_cache(created_at)
            """
            )

    def _generate_cache_key(self, name_text: str) -> str:
        """Generate consistent cache key for name text"""
        # Normalize name for consistent caching
        normalized = self._normalize_name(name_text)
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def _normalize_name(self, name_text: str) -> str:
        """Normalize name text for consistent matching"""
        if not name_text:
            return ""

        # Convert to lowercase, remove extra whitespace, normalize punctuation
        normalized = name_text.lower().strip()
        normalized = " ".join(normalized.split())  # Normalize whitespace
        normalized = normalized.replace(".", "").replace(",", "").replace("-", " ")
        return normalized

    def _detect_duplicates(self, name_text: str, cache_key: str) -> Optional[str]:
        """Detect if this name is a duplicate/variant of an existing cached name"""
        normalized = self._normalize_name(name_text)

        # Check for exact normalized match
        if normalized in self._similarity_index:
            existing_keys = self._similarity_index[normalized]
            if existing_keys:
                # Return the first existing key as the canonical one
                canonical_key = next(iter(existing_keys))
                self._exact_duplicates[cache_key] = canonical_key
                self.stats["duplicate_detections"] += 1
                return canonical_key

        # Add this normalized name to the index
        self._similarity_index[normalized].add(cache_key)
        return None

    def get(self, name_text: str) -> Optional[CachedResult]:
        """Get cached result for name text"""
        if not name_text or not name_text.strip():
            return None

        cache_key = self._generate_cache_key(name_text)

        with self._cache_lock:
            # Check if this is a known duplicate
            if cache_key in self._exact_duplicates:
                canonical_key = self._exact_duplicates[cache_key]
                cache_key = canonical_key

            # Try memory cache first
            if cache_key in self._memory_cache:
                result = self._memory_cache[cache_key]

                # Check if expired
                if time.time() - result.cached_at > self.ttl_seconds:
                    del self._memory_cache[cache_key]
                    self._cleanup_similarity_index(cache_key)
                else:
                    # Update access info and move to end (LRU)
                    result.access_count += 1
                    result.last_accessed = time.time()
                    self._memory_cache.move_to_end(cache_key)

                    self.stats["hits"] += 1
                    return result

        # Try disk cache
        disk_result = self._get_from_disk(cache_key)
        if disk_result:
            # Add to memory cache
            with self._cache_lock:
                self._add_to_memory_cache(cache_key, disk_result)

            self.stats["hits"] += 1
            return disk_result

        self.stats["misses"] += 1
        return None

    def put(self, name_text: str, result: Dict[str, Any]) -> None:
        """Cache parsing result for name text"""
        if not name_text or not name_text.strip():
            return

        cache_key = self._generate_cache_key(name_text)

        # Check for duplicates
        duplicate_key = self._detect_duplicates(name_text, cache_key)
        if duplicate_key:
            # This is a duplicate, don't cache separately
            return

        # Create cached result
        cached_result = CachedResult(
            first_name=result.get("first_name", ""),
            last_name=result.get("last_name", ""),
            entity_type=result.get("entity_type", "unknown"),
            gender=result.get("gender", "unknown"),
            gender_confidence=result.get("gender_confidence", 0.0),
            parsing_confidence=result.get("parsing_confidence", 0.0),
            is_agricultural=result.get("is_agricultural", False),
            warnings=result.get("warnings", []),
            cached_at=time.time(),
            access_count=1,
            last_accessed=time.time(),
        )

        with self._cache_lock:
            # Add to memory cache
            self._add_to_memory_cache(cache_key, cached_result)

        # Schedule disk write
        self._schedule_disk_write(cache_key, name_text, cached_result)

    def _add_to_memory_cache(self, cache_key: str, result: CachedResult) -> None:
        """Add result to memory cache with LRU eviction"""
        self._memory_cache[cache_key] = result
        self._memory_cache.move_to_end(cache_key)

        # Enforce size limit
        while len(self._memory_cache) > self.max_memory_cache:
            oldest_key, oldest_result = self._memory_cache.popitem(last=False)
            self._cleanup_similarity_index(oldest_key)
            self.stats["evictions"] += 1

        self.stats["memory_cache_size"] = len(self._memory_cache)

    def _cleanup_similarity_index(self, cache_key: str) -> None:
        """Clean up similarity index when removing cache entry"""
        # Remove from similarity index
        for normalized_name, key_set in self._similarity_index.items():
            if cache_key in key_set:
                key_set.discard(cache_key)
                if not key_set:  # If set becomes empty, remove the entry
                    del self._similarity_index[normalized_name]
                break

        # Clean up duplicate mapping
        self._exact_duplicates = {
            k: v
            for k, v in self._exact_duplicates.items()
            if v != cache_key and k != cache_key
        }

    def _get_from_disk(self, cache_key: str) -> Optional[CachedResult]:
        """Retrieve result from disk cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """SELECT result_json, created_at, access_count
                       FROM name_cache
                       WHERE cache_key = ? AND created_at > ?""",
                    (cache_key, time.time() - self.ttl_seconds),
                )

                row = cursor.fetchone()
                if row:
                    result_json, created_at, access_count = row
                    result_data = json.loads(result_json)

                    # Update access count
                    conn.execute(
                        "UPDATE name_cache SET access_count = access_count + 1, last_accessed = ? WHERE cache_key = ?",
                        (time.time(), cache_key),
                    )

                    return CachedResult(**result_data)

        except Exception as e:
            logger.warning("disk_cache_read_error", error=str(e))

        return None

    def _schedule_disk_write(
        self, cache_key: str, name_text: str, result: CachedResult
    ) -> None:
        """Schedule disk write for batch processing"""
        with self._batch_lock:
            self._batch_updates.append((cache_key, name_text, result))

            # Flush if batch is full or enough time has passed
            if (
                len(self._batch_updates) >= 50
                or time.time() - self._last_batch_flush > 30
            ):
                self._flush_batch_updates()

    def _flush_batch_updates(self) -> None:
        """Flush pending updates to disk"""
        if not self._batch_updates:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                for cache_key, name_text, result in self._batch_updates:
                    result_json = json.dumps(asdict(result))
                    normalized_name = self._normalize_name(name_text)

                    conn.execute(
                        """INSERT OR REPLACE INTO name_cache
                           (cache_key, original_text, normalized_text, result_json,
                            created_at, last_accessed, access_count)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            cache_key,
                            name_text,
                            normalized_name,
                            result_json,
                            result.cached_at,
                            result.last_accessed,
                            result.access_count,
                        ),
                    )

            self.stats["disk_cache_size"] += len(self._batch_updates)
            self._batch_updates.clear()
            self._last_batch_flush = time.time()

        except Exception as e:
            logger.error("disk_cache_write_error", error=str(e))

    def batch_get(self, name_texts: List[str]) -> Dict[str, Optional[CachedResult]]:
        """Get multiple cached results efficiently"""
        results = {}

        for name_text in name_texts:
            results[name_text] = self.get(name_text)

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "hit_rate": hit_rate,
            "total_hits": self.stats["hits"],
            "total_misses": self.stats["misses"],
            "memory_cache_size": len(self._memory_cache),
            "max_memory_cache": self.max_memory_cache,
            "evictions": self.stats["evictions"],
            "duplicate_detections": self.stats["duplicate_detections"],
            "similarity_index_size": len(self._similarity_index),
            "exact_duplicates_count": len(self._exact_duplicates),
            "pending_disk_writes": len(self._batch_updates),
        }

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        expired_count = 0
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        # Clean memory cache
        with self._cache_lock:
            expired_keys = []
            for key, result in self._memory_cache.items():
                if result.cached_at < cutoff_time:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._memory_cache[key]
                self._cleanup_similarity_index(key)
                expired_count += 1

        # Clean disk cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM name_cache WHERE created_at < ?", (cutoff_time,)
                )
                expired_count += cursor.rowcount

        except Exception as e:
            logger.error("cache_cleanup_error", error=str(e))

        return expired_count

    def force_flush(self) -> None:
        """Force flush all pending updates"""
        with self._batch_lock:
            self._flush_batch_updates()

    def clear_all(self) -> None:
        """Clear all cache data"""
        with self._cache_lock:
            self._memory_cache.clear()
            self._similarity_index.clear()
            self._exact_duplicates.clear()

            # Reset stats
            for key in self.stats:
                if key not in ["hits", "misses"]:
                    self.stats[key] = 0

        # Clear disk cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM name_cache")
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
