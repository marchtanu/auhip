import logging
import asyncio
from typing import Dict, List, Any
import os
import glob

from auhip.core.agents.memory import memory_agent

logger = logging.getLogger(__name__)

class UniversalSearchAPI:
    """
    Unifies querying across the semantic Vector DB, conversation memory, 
    and the local filesystem into a single ranked result set.
    """
    
    @staticmethod
    async def search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        logger.info(f"Performing universal search for: {query}")
        results = []
        
        # 1. Search Semantic Memory (Vector DB)
        try:
            mem_results = await memory_agent.search_memory(query, limit=limit//2)
            for m in mem_results:
                results.append({
                    "source": "memory",
                    "score": m.get("distance", 0.0), # LanceDB uses distance
                    "content": m.get("text", ""),
                    "metadata": m.get("metadata", "{}")
                })
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            
        # 2. Search Session Memory (Working Memory)
        session_context = memory_agent.get_session_context()
        if query.lower() in session_context.lower():
            results.append({
                "source": "session",
                "score": 0.0, # Exact match in session is high relevance
                "content": "Recent conversation mentions: " + query,
                "metadata": "{}"
            })
            
        # 3. Quick Filesystem Search (Fallback naive search)
        # In a real implementation this would use something like `ripgrep`
        # or the indexed Vector DB (which is handled above).
        # We just add a fast path for exact filename matches.
        loop = asyncio.get_running_loop()
        def _fs_search():
            matches = []
            for filepath in glob.glob(f"**/*{query}*", recursive=True):
                if os.path.isfile(filepath):
                    matches.append(filepath)
                if len(matches) > 3:
                    break
            return matches
            
        try:
            files = await loop.run_in_executor(None, _fs_search)
            for f in files:
                results.append({
                    "source": "filesystem",
                    "score": 0.1,
                    "content": f"Found file matching name: {f}",
                    "metadata": "{}"
                })
        except Exception as e:
            logger.error(f"FS search failed: {e}")
            
        # Sort results (lower distance/score is better for LanceDB usually, 
        # but we mock it here)
        results.sort(key=lambda x: x["score"])
        
        return results[:limit]

universal_search = UniversalSearchAPI()
