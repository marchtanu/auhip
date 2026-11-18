"""Local, typed memory with a JSON source of truth and optional vector ranking."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.request
import uuid
from typing import Any

from auhip.core.llm.config import llm_config

logger = logging.getLogger(__name__)

_DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
try:
    _EMBEDDING_DIMENSION = max(1, int(os.getenv("AUHIP_EMBEDDING_DIMENSION", "768")))
except ValueError:
    _EMBEDDING_DIMENSION = 768
_MEMORY_TYPES = {"fact", "preference", "decision", "project"}
_AUTO_RECALL_TYPES = _MEMORY_TYPES
_WORD_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "did", "do", "does",
    "for", "from", "had", "has", "have", "how", "i", "in", "into", "is", "it", "its",
    "me", "my", "of", "on", "or", "our", "please", "tell", "that", "the", "their",
    "them", "then", "this", "to", "was", "we", "what", "when", "where", "which", "who",
    "why", "with", "you", "your",
}

try:
    import lancedb
    from lancedb.pydantic import LanceModel, Vector

    class MemoryRecord(LanceModel):
        memory_id: str
        vector: Vector(_EMBEDDING_DIMENSION)
        text: str
        memory_type: str
        source: str
        confidence: float
        importance: float
        timestamp: float

    _HAS_LANCEDB = True
except ImportError:
    lancedb = None
    _HAS_LANCEDB = False
    logger.info("LanceDB is unavailable; memory will use local JSON and lexical search.")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value.copy()
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_word(word: str) -> str:
    word = word.lower().strip("'-_")
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    return [
        token for raw in _WORD_PATTERN.findall(text.lower())
        if (token := _normalize_word(raw)) and token not in _STOP_WORDS and len(token) > 1
    ]


class MemoryAgent:
    """Store curated memories separately from interactions and indexed documents."""

    def __init__(self, db_path: str | None = None, json_path: str | None = None):
        project_root = Path(__file__).resolve().parents[2]
        self.db_path = str(Path(db_path).expanduser().resolve()) if db_path else str(project_root / "data" / "memory.lancedb")
        self.json_path = str(Path(json_path).expanduser().resolve()) if json_path else str(project_root / "data" / "memory_records.json")
        personal_path = Path(self.json_path)
        self.history_path = str(personal_path.with_name("conversation_history.json"))
        self.knowledge_path = str(personal_path.with_name("knowledge_index.json"))
        self.embedding_model = os.getenv("AUHIP_EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL).strip() or _DEFAULT_EMBEDDING_MODEL
        self._db = None
        self._tables: dict[str, Any] = {}
        self._embedding_retry_after = 0.0
        self._storage_load_failed = False
        self._local_records: list[dict[str, Any]] = []
        self._history_records: list[dict[str, Any]] = []
        self._knowledge_records: list[dict[str, Any]] = []
        self.session_memory: list[dict[str, str]] = []
        self.working_memory: dict[str, Any] = {}
        self._load_local_records()
        logger.info(
            "MemoryAgent ready: %s (%s records).",
            "LanceDB + local JSON" if _HAS_LANCEDB else "local JSON + lexical search",
            len(self._local_records),
        )

    def _normalize_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        metadata = _metadata_dict(raw.get("metadata"))
        legacy_type = metadata.get("type")
        timestamp = raw.get("timestamp", time.time())
        try:
            timestamp_value = float(timestamp)
        except (TypeError, ValueError):
            timestamp_value = time.time()
        created_at = raw.get("created_at") or metadata.get("created_at")
        if not created_at:
            created_at = datetime.fromtimestamp(timestamp_value, timezone.utc).isoformat()
        memory_type = str(raw.get("memory_type") or legacy_type or "interaction")
        source = str(raw.get("source") or metadata.get("source") or "legacy conversation")
        confidence = raw.get("confidence", metadata.get("confidence", 0.5))
        try:
            confidence = min(1.0, max(0.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.5
        importance = raw.get("importance", 0.5)
        try:
            importance = min(1.0, max(0.0, float(importance)))
        except (TypeError, ValueError):
            importance = 0.5
        return {
            "memory_id": str(raw.get("memory_id") or uuid.uuid4().hex),
            "text": str(raw.get("text", "")).strip(),
            "memory_type": memory_type,
            "source": source,
            "confidence": confidence,
            "importance": importance,
            "created_at": str(created_at),
            "updated_at": str(raw.get("updated_at") or created_at),
            "timestamp": timestamp_value,
            "metadata": metadata,
        }

    @staticmethod
    def _read_records(path: str) -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as memory_file:
            data = json.load(memory_file)
        if not isinstance(data, list):
            raise ValueError(f"Memory store root must be a JSON array: {path}")
        return [row for row in data if isinstance(row, dict)]

    @staticmethod
    def _bucket_for_type(memory_type: str) -> str:
        if memory_type in _MEMORY_TYPES:
            return "personal"
        if memory_type in {"file_chunk", "knowledge_chunk"}:
            return "knowledge"
        return "history"

    def _load_local_records(self) -> None:
        try:
            sources = {
                "personal": self._read_records(self.json_path),
                "history": self._read_records(self.history_path),
                "knowledge": self._read_records(self.knowledge_path),
            }
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self._storage_load_failed = True
            logger.error("Could not safely load local memory stores: %s", error)
            return

        buckets: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in sources}
        migrated = False
        for source_name, raw_records in sources.items():
            for raw_record in raw_records:
                record = self._normalize_record(raw_record)
                target_name = self._bucket_for_type(record["memory_type"])
                if source_name != target_name:
                    migrated = True
                buckets[target_name][record["memory_id"]] = record

        self._local_records = list(buckets["personal"].values())
        self._history_records = list(buckets["history"].values())
        self._knowledge_records = list(buckets["knowledge"].values())

        if migrated:
            try:
                self._write_records(self.history_path, self._history_records)
                self._write_records(self.knowledge_path, self._knowledge_records)
                self._write_records(self.json_path, self._local_records)
                logger.info("Separated legacy memories into personal, conversation-history, and knowledge stores.")
            except OSError:
                self._storage_load_failed = True
                logger.exception("Could not finish separating legacy memory stores; preserving the source data.")

    def _write_records(self, path: str, records: list[dict[str, Any]]) -> None:
        if self._storage_load_failed:
            raise OSError("A memory store could not be read safely; refusing to overwrite local memory data.")
        directory = Path(path).parent
        directory.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_path = tempfile.mkstemp(prefix=".memory-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as memory_file:
                json.dump(records, memory_file, ensure_ascii=False, indent=2)
                memory_file.write("\n")
            os.replace(temporary_path, path)
        finally:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass

    def _records_for_type(self, memory_type: str) -> tuple[str, list[dict[str, Any]]]:
        bucket = self._bucket_for_type(memory_type)
        if bucket == "personal":
            return self.json_path, self._local_records
        if bucket == "knowledge":
            return self.knowledge_path, self._knowledge_records
        return self.history_path, self._history_records

    def _table_lane(self, memory_type: str) -> str | None:
        if memory_type in _MEMORY_TYPES:
            return "personal"
        if memory_type in {"file_chunk", "knowledge_chunk"}:
            return "knowledge"
        return None

    def _table_name(self, lane: str) -> str:
        model_slug = re.sub(r"[^a-z0-9]+", "_", self.embedding_model.lower()).strip("_")[:32]
        return f"memories_v2_{lane}_{model_slug}_{_EMBEDDING_DIMENSION}d"

    def _get_table(self, lane: str):
        if not _HAS_LANCEDB:
            return None
        if lane in self._tables:
            return self._tables[lane]
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(self.db_path)
            table_name = self._table_name(lane)
            if table_name not in self._db.table_names():
                self._tables[lane] = self._db.create_table(table_name, schema=MemoryRecord)
            else:
                self._tables[lane] = self._db.open_table(table_name)
        except Exception:
            logger.exception("LanceDB is unavailable; continuing with JSON memory search.")
            self._tables[lane] = None
        return self._tables[lane]

    def _get_embedding(self, text: str) -> list[float] | None:
        """Request a real local embedding; never manufacture a zero-vector match."""
        if time.monotonic() < self._embedding_retry_after:
            return None
        try:
            url = f"{llm_config.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
            payload = json.dumps({"model": self.embedding_model, "prompt": text}).encode("utf-8")
            request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=4.0) as response:
                data = json.loads(response.read().decode("utf-8"))
            embedding = data.get("embedding")
            if not isinstance(embedding, list) or len(embedding) != _EMBEDDING_DIMENSION:
                actual_dimension = len(embedding) if isinstance(embedding, list) else 0
                logger.warning(
                    "Embedding model %s returned %s dimensions; expected %s. Using lexical search.",
                    self.embedding_model, actual_dimension, _EMBEDDING_DIMENSION,
                )
                return None
            return [float(value) for value in embedding]
        except Exception as error:
            logger.debug("Local embedding unavailable: %s", error)
            self._embedding_retry_after = time.monotonic() + 30.0
            return None

    async def _embed(self, text: str) -> list[float] | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_embedding, text)

    def _vector_payload(self, record: dict[str, Any], vector: list[float]) -> dict[str, Any]:
        return {
            "memory_id": record["memory_id"],
            "vector": vector,
            "text": record["text"],
            "memory_type": record["memory_type"],
            "source": record["source"],
            "confidence": record["confidence"],
            "importance": record["importance"],
            "timestamp": record["timestamp"],
        }

    async def _sync_vector_record(self, record: dict[str, Any], vector: list[float] | None) -> None:
        lane = self._table_lane(record["memory_type"])
        if lane is None:
            return
        table = self._get_table(lane)
        if table is None:
            return
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: table.delete(f"memory_id = '{record['memory_id']}'"))
            if vector is not None:
                payload = self._vector_payload(record, vector)
                await loop.run_in_executor(None, lambda: table.add([payload]))
        except Exception:
            logger.exception("Could not synchronize memory %s with the vector index.", record["memory_id"])

    async def add_long_term_memory(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        memory_type: str | None = None,
        source: str | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any] | None:
        """Store one typed record; unknown callers are kept as non-recalled interactions."""
        if not isinstance(text, str) or not text.strip():
            return None
        text = text.strip()
        if len(text) > 5000:
            raise ValueError("Memory text must be 5,000 characters or fewer.")
        details = metadata.copy() if isinstance(metadata, dict) else {}
        resolved_type = memory_type or details.get("type") or "interaction"
        resolved_source = source or details.get("source") or "unspecified"
        resolved_confidence = details.get("confidence", 0.5) if confidence is None else confidence
        now = time.time()
        record = self._normalize_record({
            "memory_id": uuid.uuid4().hex,
            "text": text.strip(),
            "memory_type": resolved_type,
            "source": resolved_source,
            "confidence": resolved_confidence,
            "importance": importance,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "timestamp": now,
            "metadata": details,
        })
        store_path, records = self._records_for_type(record["memory_type"])
        records.append(record)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_records, store_path, [row.copy() for row in records])
        if _HAS_LANCEDB and self._table_lane(record["memory_type"]):
            vector = await self._embed(record["text"])
            await self._sync_vector_record(record, vector)
        logger.info("Stored %s memory %s from %s.", record["memory_type"], record["memory_id"], record["source"])
        return record.copy()

    async def remember(
        self,
        text: str,
        memory_type: str = "fact",
        source: str = "user",
        confidence: float = 1.0,
        importance: float = 0.9,
    ) -> dict[str, Any]:
        if memory_type not in _MEMORY_TYPES:
            raise ValueError(f"Memory type must be one of: {', '.join(sorted(_MEMORY_TYPES))}.")
        record = await self.add_long_term_memory(
            text, memory_type=memory_type, source=source, confidence=confidence, importance=importance
        )
        if record is None:
            raise ValueError("Memory text cannot be empty.")
        return record

    async def correct(self, memory_id: str, text: str, memory_type: str | None = None) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Corrected memory text cannot be empty.")
        if len(text.strip()) > 5000:
            raise ValueError("Corrected memory text must be 5,000 characters or fewer.")
        record = self._find_record(memory_id)
        if record is None:
            raise KeyError("That memory ID was not found.")
        if memory_type and memory_type not in _MEMORY_TYPES:
            raise ValueError(f"Memory type must be one of: {', '.join(sorted(_MEMORY_TYPES))}.")
        record["text"] = text.strip()
        record["memory_type"] = memory_type or record["memory_type"]
        record["updated_at"] = _now_iso()
        record["timestamp"] = time.time()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_records, self.json_path, [row.copy() for row in self._local_records])
        vector = await self._embed(record["text"]) if _HAS_LANCEDB else None
        await self._sync_vector_record(record, vector)
        return record.copy()

    async def forget(self, memory_id: str) -> bool:
        record = self._find_record(memory_id)
        if record is None:
            return False
        self._local_records = [row for row in self._local_records if row["memory_id"] != memory_id]
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_records, self.json_path, [row.copy() for row in self._local_records])
        await self._sync_vector_record(record, None)
        return True

    def _find_record(self, memory_id: str) -> dict[str, Any] | None:
        return next((record for record in self._local_records if record["memory_id"] == memory_id), None)

    def list_memories(self, memory_type: str = "", limit: int = 30) -> list[dict[str, Any]]:
        if memory_type and memory_type not in _MEMORY_TYPES:
            raise ValueError(f"Memory type must be one of: {', '.join(sorted(_MEMORY_TYPES))}.")
        rows = [
            record for record in self._local_records
            if record["memory_type"] in _MEMORY_TYPES and (not memory_type or record["memory_type"] == memory_type)
        ]
        rows.sort(key=lambda record: record["updated_at"], reverse=True)
        return [record.copy() for record in rows[:max(1, min(limit, 100))]]

    def _lexical_results(
        self,
        query: str,
        records: list[dict[str, Any]],
        memory_types: set[str],
        limit: int,
    ) -> list[tuple[dict[str, Any], float]]:
        query_terms = set(_tokens(query))
        if not query_terms:
            return []
        candidates = [
            record for record in records
            if record["memory_type"] in memory_types and record["confidence"] >= 0.45 and _tokens(record["text"])
        ]
        document_frequency: Counter[str] = Counter()
        tokenized: dict[str, list[str]] = {}
        for record in candidates:
            words = _tokens(record["text"])
            tokenized[record["memory_id"]] = words
            document_frequency.update(set(words))

        average_length = sum(len(words) for words in tokenized.values()) / max(len(tokenized), 1)
        scored: list[tuple[dict[str, Any], float]] = []
        for record in candidates:
            words = tokenized[record["memory_id"]]
            frequencies = Counter(words)
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log(1 + (len(candidates) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
                normalization = frequency + 1.2 * (0.25 + 0.75 * len(words) / max(average_length, 1.0))
                score += inverse_frequency * frequency * 2.2 / normalization
            if query.strip().lower() in record["text"].lower():
                score += 1.0
            if score <= 0.05:
                continue
            score *= 0.7 + 0.3 * record["importance"]
            scored.append((record, score))
        scored.sort(key=lambda item: (item[1], item[0]["timestamp"]), reverse=True)
        return scored[:limit]

    async def search_memory(
        self,
        query: str,
        limit: int = 5,
        memory_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid semantic and BM25 retrieval with strict type and confidence filters."""
        if not query or not query.strip():
            return []
        query = query[:2000]
        selected_types = memory_types if memory_types is not None else _AUTO_RECALL_TYPES
        if not selected_types:
            return []
        max_results = max(1, min(limit, 20))
        records_by_id = {
            record["memory_id"]: record for record in self._local_records
            if record["memory_type"] in selected_types and record["confidence"] >= 0.45
        }
        fused: dict[str, float] = {}

        if not records_by_id:
            return []
        vector = await self._embed(query) if _HAS_LANCEDB else None
        lane = "personal" if selected_types <= _AUTO_RECALL_TYPES else None
        table = self._get_table(lane) if vector is not None and lane else None
        if table is not None:
            try:
                search_request = table.search(vector)
                metric = getattr(search_request, "metric", None)
                if callable(metric):
                    search_request = metric("cosine")
                loop = asyncio.get_running_loop()
                semantic_rows = await loop.run_in_executor(
                    None, lambda: search_request.limit(max(20, max_results * 4)).to_list()
                )
                semantic_rank = 0
                for row in semantic_rows:
                    memory_id = row.get("memory_id")
                    current = records_by_id.get(memory_id)
                    if current is None or row.get("_distance", row.get("distance")) is None:
                        continue
                    distance = float(row.get("_distance", row.get("distance")))
                    if distance > 0.72:
                        continue
                    semantic_rank += 1
                    fused[memory_id] = fused.get(memory_id, 0.0) + 1.0 / (60 + semantic_rank)
            except Exception:
                logger.exception("Semantic memory search failed; using lexical results only.")

        lexical_results = self._lexical_results(query, list(records_by_id.values()), selected_types, max_results * 4)
        for rank, (record, _) in enumerate(lexical_results, start=1):
            memory_id = record["memory_id"]
            fused[memory_id] = fused.get(memory_id, 0.0) + 1.0 / (60 + rank)

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        results = []
        for memory_id, relevance in ranked[:max_results]:
            result = records_by_id[memory_id].copy()
            result["relevance"] = round(relevance, 5)
            results.append(result)
        return results

    async def search_history(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search archived interactions separately; history is never automatic prompt context."""
        if not query or not query.strip():
            return []
        return [
            {**record, "relevance": round(score, 5)}
            for record, score in self._lexical_results(
                query[:2000], self._history_records, {"interaction", "session_summary"}, max(1, min(limit, 20))
            )
        ]

    def add_session_message(self, role: str, content: str) -> None:
        self.session_memory.append({"role": role, "content": content})
        if len(self.session_memory) > 50:
            self.session_memory = self.session_memory[-50:]

    def get_session_context(self) -> str:
        return "".join(f"{item['role'].capitalize()}: {item['content']}\n" for item in self.session_memory[-8:])

    async def summarize_session(self) -> None:
        """Retain legacy summarization as a history record, outside curated recall."""
        if len(self.session_memory) >= 6:
            summary = f"Recent Session Summary:\n{self.get_session_context()}"
            await self.add_long_term_memory(
                summary,
                memory_type="session_summary",
                source="session summarizer",
                confidence=0.5,
                importance=0.7,
            )


memory_agent = MemoryAgent()
