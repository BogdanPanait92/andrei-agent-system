"""Persistent memory with Supabase (pgvector) or Pinecone."""

import hashlib
from datetime import datetime
from typing import Any

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryStore:
    """Unified memory interface for agent context persistence."""

    def __init__(self) -> None:
        self.provider = settings.memory_provider
        self._client: Any = None
        self._initialized = False

    def _init_supabase(self) -> None:
        from supabase import create_client

        settings.validate_required("supabase_url", "supabase_key")
        key = settings.supabase_service_key or settings.supabase_key
        self._client = create_client(settings.supabase_url, key)
        self._initialized = True

    def _init_pinecone(self) -> None:
        from pinecone import Pinecone

        settings.validate_required("pinecone_api_key")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self._client = pc.Index(settings.pinecone_index_name)
        self._initialized = True

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            if self.provider == "supabase":
                self._init_supabase()
            else:
                self._init_pinecone()
            logger.info("memory_initialized", provider=self.provider)
        except Exception as e:
            logger.warning("memory_init_failed", error=str(e), provider=self.provider)

    def store(
        self,
        content: str,
        metadata: dict | None = None,
        agent: str = "system",
        category: str = "general",
    ) -> bool:
        self.initialize()
        if not self._initialized:
            return False

        meta = metadata or {}
        meta.update({
            "agent": agent,
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
        })

        try:
            if self.provider == "supabase":
                self._client.table("agent_memories").insert({
                    "content": content,
                    "metadata": meta,
                    "agent": agent,
                    "category": category,
                }).execute()
            else:
                vec_id = hashlib.md5(content.encode()).hexdigest()
                self._client.upsert(vectors=[{
                    "id": vec_id,
                    "values": self._simple_embedding(content),
                    "metadata": {**meta, "content": content[:1000]},
                }])
            return True
        except Exception as e:
            logger.error("memory_store_failed", error=str(e))
            return False

    def recall(self, query: str, limit: int = 10, agent: str | None = None) -> list[dict]:
        self.initialize()
        if not self._initialized:
            return []

        try:
            if self.provider == "supabase":
                q = self._client.table("agent_memories").select("*").order(
                    "created_at", desc=True
                ).limit(limit)
                if agent:
                    q = q.eq("agent", agent)
                result = q.execute()
                return result.data or []
            else:
                results = self._client.query(
                    vector=self._simple_embedding(query),
                    top_k=limit,
                    include_metadata=True,
                )
                return [
                    {"content": m.get("metadata", {}).get("content", ""), "metadata": m.get("metadata", {})}
                    for m in results.get("matches", [])
                ]
        except Exception as e:
            logger.error("memory_recall_failed", error=str(e))
            return []

    def get_context_for_agents(self, query: str, limit: int = 5) -> str:
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""
        lines = ["--- Context din memorie ---"]
        for mem in memories:
            content = mem.get("content", "")
            agent = mem.get("metadata", {}).get("agent", mem.get("agent", ""))
            lines.append(f"[{agent}] {content[:300]}")
        return "\n".join(lines)

    @staticmethod
    def _simple_embedding(text: str, dim: int = 384) -> list[float]:
        """Deterministic pseudo-embedding for Pinecone fallback without embedding API."""
        h = hashlib.sha256(text.encode()).digest()
        return [(h[i % len(h)] / 255.0) for i in range(dim)]