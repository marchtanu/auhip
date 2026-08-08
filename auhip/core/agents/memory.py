import logging
import asyncio
import os
import json
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
    logger.info("LanceDB not installed — long-term vector memory disabled.")


class MemoryAgent:
    """
    Manages Working Memory, Session Memory, and Long-Term Semantic Memory (Vector DB).
    Optimized to eliminate PyTorch runtime footprint.
    """
    def __init__(self, db_path: str = "data/memory.lancedb"):
        self.db_path = db_path
        self._db = None
        self._table = None
        self.session_memory: List[Dict[str, str]] = []
        self.working_memory: Dict[str, Any] = {}
        logger.info("MemoryAgent initialized (lightweight mode).")

    def _get_table(self):
        if not _HAS_LANCEDB:
            return None
        if self._table is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._db = lancedb.connect(self.db_path)
            table_name = "long_term_memory"
            if table_name not in self._db.table_names():
                self._table = self._db.create_table(table_name, schema=MemoryRecord)
            else:
                self._table = self._db.open_table(table_name)
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
            with urllib.request.urlopen(req, timeout=1.5) as resp:
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
        """Add a persistent semantic memory to the Vector DB."""
        import time
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, self._get_embedding, text)
        meta_str = json.dumps(metadata) if metadata else "{}"

        record = {
            "vector": vector,
            "text": text,
            "metadata": meta_str,
            "importance": importance,
            "timestamp": time.time()
        }

        table = self._get_table()
        if table:
            await loop.run_in_executor(None, table.add, [record])
            logger.info(f"Added to long-term memory: {text[:30]}...")

    async def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the semantic Vector DB for relevant context."""
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, self._get_embedding, query)

        def _search():
            table = self._get_table()
            if table:
                return table.search(vector).limit(limit).to_list()
            return []

        try:
            results = await loop.run_in_executor(None, _search)
            return results
        except Exception as e:
            logger.error(f"Search memory failed: {e}")
            return []


    def add_session_message(self, role: str, content: str):
        """Add a message to the current short-term session window."""
        self.session_memory.append({"role": role, "content": content})
        if len(self.session_memory) > 50:
            self.session_memory = self.session_memory[-50:]

    def get_session_context(self) -> str:
        """Returns the recent conversation context as a string."""
        context = ""
        for msg in self.session_memory[-10:]:
            context += f"{msg['role'].capitalize()}: {msg['content']}\n"
        return context

    async def summarize_session(self):
        """Periodically compress session memory into dense long-term memory."""
        pass


memory_agent = MemoryAgent()

