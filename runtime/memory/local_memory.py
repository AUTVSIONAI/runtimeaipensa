"""
Local Memory Module Implementation

Provides in-memory and persisted storage with search capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from collections import defaultdict

import aiofiles

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    MemoryModule,
    MemoryEntry,
    SearchResult,
)

logger = logging.getLogger(__name__)


@dataclass
class _MemoryStore:
    """Internal memory store for a specific memory type."""
    entries: Dict[str, MemoryEntry] = field(default_factory=dict)
    index: Dict[str, set] = field(default_factory=lambda: defaultdict(set))


class LocalMemoryModule(MemoryModule):
    """
    Local memory implementation with in-memory storage and optional
    file-based persistence.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory",
            version="1.0.0",
            description="Local memory storage with search",
            author="AIPENSA",
            dependencies=[],
            provides=["memory_store", "memory_retrieve", "memory_search", "memory_delete"],
            tags={"local", "memory", "storage"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._stores: Dict[str, _MemoryStore] = {}
        self._persist_path = self._config.get("persist_path")
        self._max_entries = self._config.get("max_entries", 10000)
        self._default_ttl = self._config.get("default_ttl_seconds")

        if self._persist_path:
            os.makedirs(self._persist_path, exist_ok=True)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._persist_path = self._config.get("persist_path", self._persist_path)
        self._max_entries = self._config.get("max_entries", self._max_entries)

        if self._persist_path:
            await self._load_from_disk()

        self.state = ModuleState.INITIALIZED
        logger.info("LocalMemoryModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalMemoryModule started")

    async def stop(self) -> None:
        if self._persist_path:
            await self._save_to_disk()
        self.state = ModuleState.STOPPED
        logger.info("LocalMemoryModule stopped")

    async def cleanup(self) -> None:
        self._stores.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalMemoryModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        total_entries = sum(len(store.entries) for store in self._stores.values())
        return {
            "module": "memory",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "memory_types": len(self._stores),
            "total_entries": total_entries,
        }

    def _get_store(self, memory_type: str) -> _MemoryStore:
        """Get or create store for memory type."""
        if memory_type not in self._stores:
            self._stores[memory_type] = _MemoryStore()
        return self._stores[memory_type]

    def _build_search_text(self, entry: MemoryEntry) -> str:
        """Build searchable text from entry."""
        parts = [entry.key]
        if isinstance(entry.value, str):
            parts.append(entry.value)
        elif isinstance(entry.value, dict):
            parts.append(json.dumps(entry.value))
        parts.extend(entry.tags)
        for k, v in entry.metadata.items():
            parts.append(f"{k}:{v}")
        return " ".join(parts)

    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "default",
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store a value in memory."""
        store = self._get_store(memory_type)

        # Check max entries
        if len(store.entries) >= self._max_entries:
            # Remove oldest expired entries first
            await self._cleanup_expired(memory_type)
            if len(store.entries) >= self._max_entries:
                # Remove oldest entry
                oldest_key = min(store.entries.keys(), key=lambda k: store.entries[k].created_at)
                del store.entries[oldest_key]

        now = datetime.utcnow()
        expires_at = None
        if ttl_seconds or self._default_ttl:
            expires_at = now + timedelta(seconds=ttl_seconds or self._default_ttl)

        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=memory_type,
            tags=tags or [],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            size_bytes=len(json.dumps(value, default=str).encode()),
        )

        store.entries[key] = entry

        # Update index
        search_text = self._build_search_text(entry).lower()
        for word in search_text.split():
            if len(word) > 2:
                store.index[word].add(key)

        if self._persist_path:
            await self._save_to_disk()

        return entry

    async def retrieve(
        self,
        key: str,
        memory_type: str = "default"
    ) -> Optional[MemoryEntry]:
        """Retrieve a value from memory."""
        store = self._get_store(memory_type)

        if key not in store.entries:
            return None

        entry = store.entries[key]

        # Check expiration
        if entry.expires_at and entry.expires_at < datetime.utcnow():
            await self.delete(key, memory_type)
            return None

        return entry

    async def delete(self, key: str, memory_type: str = "default") -> bool:
        """Delete a value from memory."""
        store = self._get_store(memory_type)

        if key not in store.entries:
            return False

        entry = store.entries[key]

        # Remove from index
        search_text = self._build_search_text(entry).lower()
        for word in search_text.split():
            if word in store.index:
                store.index[word].discard(key)
                if not store.index[word]:
                    del store.index[word]

        del store.entries[key]

        if self._persist_path:
            await self._save_to_disk()

        return True

    async def search(
        self,
        query: str,
        memory_type: str = "default",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search memory."""
        store = self._get_store(memory_type)
        query_lower = query.lower()
        query_words = query_lower.split()

        # Score entries
        scores: Dict[str, float] = {}

        for word in query_words:
            if word in store.index:
                for key in store.index[word]:
                    scores[key] = scores.get(key, 0) + 1

        # Also check exact matches and partial matches in values
        for key, entry in store.entries.items():
            if query_lower in key.lower():
                scores[key] = scores.get(key, 0) + 10
            if entry.value and query_lower in str(entry.value).lower():
                scores[key] = scores.get(key, 0) + 5
            for tag in entry.tags:
                if query_lower in tag.lower():
                    scores[key] = scores.get(key, 0) + 3

        # Sort by score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        results = []
        for key in sorted_keys[:limit]:
            entry = store.entries[key]

            # Check filters
            if filters:
                match = True
                for k, v in filters.items():
                    if k == "tags":
                        if not all(t in entry.tags for t in v):
                            match = False
                            break
                    elif k == "metadata":
                        if not all(entry.metadata.get(fk) == fv for fk, fv in v.items()):
                            match = False
                            break
                if not match:
                    continue

            # Check expiration
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                continue

            # Build snippet
            snippet = str(entry.value)[:200] if entry.value else ""
            if len(snippet) == 200:
                snippet += "..."

            results.append(SearchResult(
                entry=entry,
                score=scores[key],
                snippet=snippet,
            ))

        return results

    async def clear(self, memory_type: Optional[str] = None) -> int:
        """Clear memory (optionally by type)."""
        count = 0

        if memory_type:
            if memory_type in self._stores:
                count = len(self._stores[memory_type].entries)
                self._stores[memory_type].entries.clear()
                self._stores[memory_type].index.clear()
        else:
            for store in self._stores.values():
                count += len(store.entries)
                store.entries.clear()
                store.index.clear()

        if self._persist_path:
            await self._save_to_disk()

        return count

    async def list_keys(
        self,
        memory_type: str = "default",
        pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """List memory keys."""
        store = self._get_store(memory_type)
        keys = list(store.entries.keys())

        if pattern:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]

        return keys[:limit]

    async def get_stats(self, memory_type: Optional[str] = None) -> Dict[str, Any]:
        """Get memory statistics."""
        if memory_type:
            if memory_type not in self._stores:
                return {"total_entries": 0, "total_size_bytes": 0}
            store = self._stores[memory_type]
            total_size = sum(e.size_bytes for e in store.entries.values())
            return {
                "memory_type": memory_type,
                "total_entries": len(store.entries),
                "total_size_bytes": total_size,
                "indexed_terms": len(store.index),
            }

        total_entries = sum(len(s.entries) for s in self._stores.values())
        total_size = sum(
            sum(e.size_bytes for e in s.entries.values())
            for s in self._stores.values()
        )
        total_index = sum(len(s.index) for s in self._stores.values())

        return {
            "memory_types": len(self._stores),
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_indexed_terms": total_index,
            "by_type": {
                mt: {
                    "entries": len(s.entries),
                    "size_bytes": sum(e.size_bytes for e in s.entries.values()),
                    "indexed_terms": len(s.index),
                }
                for mt, s in self._stores.items()
            }
        }

    async def _cleanup_expired(self, memory_type: str) -> int:
        """Remove expired entries."""
        store = self._get_store(memory_type)
        now = datetime.utcnow()
        removed = []

        for key, entry in store.entries.items():
            if entry.expires_at and entry.expires_at < now:
                removed.append(key)

        for key in removed:
            await self.delete(key, memory_type)

        return len(removed)

    async def _save_to_disk(self) -> None:
        """Persist memory to disk."""
        if not self._persist_path:
            return

        try:
            data = {}
            for mt, store in self._stores.items():
                data[mt] = {}
                for key, entry in store.entries.items():
                    data[mt][key] = {
                        "key": entry.key,
                        "value": entry.value,
                        "memory_type": entry.memory_type,
                        "tags": entry.tags,
                        "metadata": entry.metadata,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                        "size_bytes": entry.size_bytes,
                    }

            file_path = os.path.join(self._persist_path, "memory.json")
            async with asyncio.Lock():
                async with aiofiles.open(file_path, "w") as f:
                    await f.write(json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to persist memory: {e}")

    async def _load_from_disk(self) -> None:
        """Load memory from disk."""
        if not self._persist_path:
            return

        file_path = os.path.join(self._persist_path, "memory.json")
        if not os.path.exists(file_path):
            return

        try:
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
                data = json.loads(content)

            for mt, entries in data.items():
                store = self._get_store(mt)
                for key, entry_data in entries.items():
                    entry = MemoryEntry(
                        key=entry_data["key"],
                        value=entry_data["value"],
                        memory_type=entry_data["memory_type"],
                        tags=entry_data["tags"],
                        metadata=entry_data["metadata"],
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                        expires_at=datetime.fromisoformat(entry_data["expires_at"]) if entry_data["expires_at"] else None,
                        size_bytes=entry_data["size_bytes"],
                    )
                    store.entries[key] = entry

                    # Rebuild index
                    search_text = self._build_search_text(entry).lower()
                    for word in search_text.split():
                        if len(word) > 2:
                            store.index[word].add(key)

            logger.info(f"Loaded memory from {file_path}")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")


# Import aiofiles for local memory module
import aiofiles