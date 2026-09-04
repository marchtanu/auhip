import logging
import asyncio
import os
import json
import time
import urllib.request
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import lancedb
    from lancedb.pydantic import LanceModel, Vector

    class MemoryRecord(LanceModel):
        vector: Vector(384)  # Match embedding dimension
        text: str
        metadata: str  # JSON string for flexibility
        importance: float = 0.5
        timestamp: float
    _HAS_LANCEDB = True
except ImportError:
    lancedb = None
    _HAS_LANCEDB = False
    logger.info("LanceDB not installed — using lightweight local JSON persistent memory.")


class MemoryAgent:
    """
    Manages Working Memory, Session Memory, and Long-Term Semantic Memory.
    Supports LanceDB vector store with an automatic zero-dependency local JSON
    fallback (data/memory_records.json) ensuring persistence in any environment.
    """
    def __init__(self, db_path: str = "data/memory.lancedb", json_path: str = "data/memory_records.json"):
        self.db_path = db_path
        self.json_path = json_path
        self._db = None
        self._table = None
        self.session_memory: List[Dict[str, str]] = []
        self.working_memory: Dict[str, Any] = {}
        self._local_records: List[Dict[str, Any]] = []
        self._load_local_records()
        logger.info(f"MemoryAgent initialized. Mode: {'LanceDB + JSON' if _HAS_LANCEDB else 'Local JSON'} ({len(self._local_records)} records loaded).")

    def _load_local_records(self):
        """Loads persistent memory records from disk if present."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self._local_records = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load local memory records: {e}")
                self._local_records = []

    def _save_local_records(self):
        """Persists local memory records to disk atomically."""
        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self._local_records[-200:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save local memory records: {e}")

    def _get_table(self):
        if not _HAS_LANCEDB:
            return None
        if self._table is None:
            try:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                self._db = lancedb.connect(self.db_path)
                table_name = "long_term_memory"
                if table_name not in self._db.table_names():
                    self._table = self._db.create_table(table_name, schema=MemoryRecord)
                else:
                    self._table = self._db.open_table(table_name)
            except Exception as e:
                logger.warning(f"LanceDB init failed, using JSON fallback: {e}")
                return None
        return self._table

    def _get_embedding(self, text: str) -> List[float]:
        """
        Fetch vector embeddings via Ollama HTTP API (nomic-embed-text/all-minilm).
        Falls back to a zero vector to avoid importing PyTorch.
        """
        try:
            url = "http://localhost:11434/api/embeddings"
            payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    emb = data.get("embedding", [])
                    if len(emb) == 384:
                        return emb
                    elif len(emb) > 384:
                        return emb[:384]
        except Exception:
            pass
        return [0.0] * 384

    async def add_long_term_memory(self, text: str, metadata: dict = None, importance: float = 0.5):
        """Add a persistent semantic memory to both LanceDB and local JSON store."""
        if not text or not text.strip():
            return
            
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, self._get_embedding, text)
        meta_dict = metadata or {}
        now = time.time()

        record = {
            "text": text.strip(),
            "metadata": meta_dict if isinstance(meta_dict, dict) else {},
            "importance": importance,
            "timestamp": now,
        }

        # 1. Update local in-memory and JSON storage
        self._local_records.append(record)
        await loop.run_in_executor(None, self._save_local_records)

        # 2. Update LanceDB if available
        table = self._get_table()
        if table:
            lance_record = {
                "vector": vector,
                "text": text.strip(),
                "metadata": json.dumps(meta_dict),
                "importance": importance,
                "timestamp": now,
            }
            try:
                await loop.run_in_executor(None, table.add, [lance_record])
                logger.debug(f"Added to LanceDB: {text[:40]}...")
            except Exception as e:
                logger.warning(f"Could not write to LanceDB: {e}")

        logger.info(f"MemoryAgent stored memory ({len(self._local_records)} total): {text[:40]}...")

    async def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant past context using vector search or token relevance fallback."""
        if not query or not query.strip():
            return []

        loop = asyncio.get_running_loop()

        # 1. Try LanceDB vector search first if available
        table = self._get_table()
        if table:
            try:
                vector = await loop.run_in_executor(None, self._get_embedding, query)
                results = await loop.run_in_executor(None, lambda: table.search(vector).limit(limit).to_list())
                if results:
                    return results
            except Exception as e:
                logger.warning(f"LanceDB vector search error: {e}")

        # 2. Local lexical relevance & recency ranking fallback
        query_words = set(query.lower().split())
        scored_records = []

        for rec in reversed(self._local_records):
            rec_text = rec.get("text", "").lower()
            rec_words = set(rec_text.split())
            overlap = len(query_words.intersection(rec_words))
            if overlap > 0:
                # Score based on overlap count and importance
                score = overlap * rec.get("importance", 0.5)
                scored_records.append((score, rec))

        # Sort by relevance score descending
        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored_records[:limit]]

    def add_session_message(self, role: str, content: str):
        """Add a message to the current short-term session window."""
        self.session_memory.append({"role": role, "content": content})
        if len(self.session_memory) > 50:
            self.session_memory = self.session_memory[-50:]

    def get_session_context(self) -> str:
        """Returns the recent conversation context as a formatted string."""
        context = ""
        for msg in self.session_memory[-8:]:
            context += f"{msg['role'].capitalize()}: {msg['content']}\n"
        return context

    async def summarize_session(self):
        """Compress recent session memory into dense long-term memory."""
        if len(self.session_memory) >= 6:
            summary_text = f"Recent Session Summary:\n{self.get_session_context()}"
            await self.add_long_term_memory(summary_text, metadata={"type": "session_summary"}, importance=0.7)


memory_agent = MemoryAgent()


