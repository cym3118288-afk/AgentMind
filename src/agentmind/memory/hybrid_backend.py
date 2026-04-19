"""Hybrid memory backend with Chroma + SQLite.

This module provides:
- Built-in Chroma vector store for semantic search
- SQLite for structured data
- Long-term memory with compression
- Cross-session memory
- Knowledge graph support
"""

from typing import Any, Dict, List, Optional, Tuple
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

from ..core.types import Message, MemoryEntry
from .backend import MemoryBackend


class HybridMemoryBackend(MemoryBackend):
    """Hybrid memory backend combining vector and relational storage."""

    def __init__(
        self,
        db_path: str = ".agentmind_memory/hybrid.db",
        enable_vector: bool = True,
        enable_compression: bool = True,
    ):
        """Initialize hybrid memory backend.

        Args:
            db_path: Path to SQLite database
            enable_vector: Enable vector storage (requires chromadb)
            enable_compression: Enable memory compression
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_vector = enable_vector
        self.enable_compression = enable_compression

        # Initialize SQLite
        self._init_sqlite()

        # Initialize vector store if enabled
        self.vector_store = None
        if enable_vector:
            try:
                self._init_vector_store()
            except ImportError:
                print("[!] chromadb not installed, vector search disabled")
                self.enable_vector = False

    def _init_sqlite(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Main memory table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                role TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                metadata TEXT,
                embedding_id TEXT,
                compressed BOOLEAN DEFAULT 0,
                session_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Knowledge graph table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source_memory_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_memory_id) REFERENCES memories(id)
            )
        """
        )

        # Session table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                metadata TEXT
            )
        """
        )

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON memories(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_subject ON knowledge_graph(subject)")

        conn.commit()
        conn.close()

    def _init_vector_store(self) -> None:
        """Initialize Chroma vector store."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Create persistent client
            chroma_path = self.db_path.parent / "chroma"
            chroma_path.mkdir(exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False),
            )

            # Get or create collection
            self.vector_store = self.chroma_client.get_or_create_collection(
                name="agentmind_memories",
                metadata={"description": "AgentMind memory embeddings"},
            )

            print("[Hybrid Memory] Vector store initialized")

        except ImportError:
            raise

    async def add(self, entry: MemoryEntry) -> None:
        """Add memory entry.

        Args:
            entry: Memory entry to add
        """
        # Generate key from content hash
        key = self._generate_key(entry.message.content)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Store in SQLite
        cursor.execute(
            """
            INSERT OR REPLACE INTO memories
            (key, content, sender, role, timestamp, importance, metadata, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                key,
                entry.message.content,
                entry.message.sender,
                entry.message.role.value,
                entry.message.timestamp.isoformat(),
                entry.importance,
                json.dumps(entry.message.metadata),
                entry.message.metadata.get("session_id"),
            ),
        )

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Store in vector store if enabled
        if self.enable_vector and entry.embedding:
            self._add_to_vector_store(key, entry.message.content, entry.embedding)

    def _generate_key(self, content: str) -> str:
        """Generate unique key from content.

        Args:
            content: Content to hash

        Returns:
            Unique key
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _add_to_vector_store(self, key: str, content: str, embedding: List[float]) -> None:
        """Add to vector store.

        Args:
            key: Memory key
            content: Content text
            embedding: Vector embedding
        """
        if not self.vector_store:
            return

        try:
            self.vector_store.add(
                ids=[key],
                embeddings=[embedding],
                documents=[content],
            )
        except Exception as e:
            print(f"[!] Vector store error: {e}")

    async def get_recent(self, limit: int) -> List[MemoryEntry]:
        """Get recent memories.

        Args:
            limit: Maximum number of entries

        Returns:
            List of memory entries
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content, sender, role, timestamp, metadata, importance
            FROM memories
            ORDER BY id DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        entries = []
        for row in reversed(rows):
            entries.append(self._row_to_entry(row))

        return entries

    async def get_all(self) -> List[MemoryEntry]:
        """Get all memories.

        Returns:
            List of all memory entries
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content, sender, role, timestamp, metadata, importance
            FROM memories
            ORDER BY id ASC
        """
        )

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_entry(row) for row in rows]

    async def search_by_importance(
        self,
        min_importance: float,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Search by importance.

        Args:
            min_importance: Minimum importance score
            limit: Maximum results

        Returns:
            List of memory entries
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content, sender, role, timestamp, metadata, importance
            FROM memories
            WHERE importance >= ?
            ORDER BY importance DESC
            LIMIT ?
        """,
            (min_importance, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_entry(row) for row in rows]

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Tuple[MemoryEntry, float]]:
        """Semantic search using vector similarity.

        Args:
            query: Search query
            limit: Maximum results
            query_embedding: Pre-computed query embedding

        Returns:
            List of (entry, similarity_score) tuples
        """
        if not self.enable_vector or not self.vector_store:
            print("[!] Vector search not available")
            return []

        try:
            # Query vector store
            if query_embedding:
                results = self.vector_store.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                )
            else:
                results = self.vector_store.query(
                    query_texts=[query],
                    n_results=limit,
                )

            # Convert to memory entries
            entries_with_scores = []
            if results and results["ids"]:
                for i, key in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1.0 - distance  # Convert distance to similarity

                    # Fetch full entry from SQLite
                    entry = await self._get_by_key(key)
                    if entry:
                        entries_with_scores.append((entry, similarity))

            return entries_with_scores

        except Exception as e:
            print(f"[!] Semantic search error: {e}")
            return []

    async def _get_by_key(self, key: str) -> Optional[MemoryEntry]:
        """Get memory by key.

        Args:
            key: Memory key

        Returns:
            Memory entry or None
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content, sender, role, timestamp, metadata, importance
            FROM memories
            WHERE key = ?
        """,
            (key,),
        )

        row = cursor.fetchone()
        conn.close()

        return self._row_to_entry(row) if row else None

    async def add_knowledge_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
        source_key: Optional[str] = None,
    ) -> None:
        """Add knowledge graph triple.

        Args:
            subject: Subject entity
            predicate: Relationship
            obj: Object entity
            confidence: Confidence score
            source_key: Source memory key
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get source memory ID if provided
        source_id = None
        if source_key:
            cursor.execute("SELECT id FROM memories WHERE key = ?", (source_key,))
            result = cursor.fetchone()
            if result:
                source_id = result[0]

        cursor.execute(
            """
            INSERT INTO knowledge_graph
            (subject, predicate, object, confidence, source_memory_id)
            VALUES (?, ?, ?, ?, ?)
        """,
            (subject, predicate, obj, confidence, source_id),
        )

        conn.commit()
        conn.close()

    async def query_knowledge_graph(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query knowledge graph.

        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            obj: Filter by object

        Returns:
            List of matching triples
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT subject, predicate, object, confidence FROM knowledge_graph WHERE 1=1"
        params = []

        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if obj:
            query += " AND object = ?"
            params.append(obj)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "subject": row[0],
                "predicate": row[1],
                "object": row[2],
                "confidence": row[3],
            }
            for row in rows
        ]

    async def compress_old_memories(self, days_old: int = 30) -> int:
        """Compress old memories to save space.

        Args:
            days_old: Compress memories older than this many days

        Returns:
            Number of memories compressed
        """
        if not self.enable_compression:
            return 0

        # Simple compression: summarize old memories
        # In production, would use LLM to generate summaries
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE memories
            SET compressed = 1,
                content = '[Compressed] ' || substr(content, 1, 100) || '...'
            WHERE compressed = 0
            AND datetime(timestamp) < datetime('now', '-' || ? || ' days')
        """,
            (days_old,),
        )

        count = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"[Compression] Compressed {count} old memories")
        return count

    async def clear(self) -> None:
        """Clear all memories."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        cursor.execute("DELETE FROM knowledge_graph")
        conn.commit()
        conn.close()

        if self.vector_store:
            try:
                self.chroma_client.delete_collection("agentmind_memories")
                self.vector_store = self.chroma_client.create_collection("agentmind_memories")
            except Exception as e:
                print(f"[!] Error clearing vector store: {e}")

    async def count(self) -> int:
        """Get total memory count.

        Returns:
            Number of memories
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        """Convert database row to MemoryEntry.

        Args:
            row: Database row

        Returns:
            Memory entry
        """
        content, sender, role, timestamp, metadata, importance = row

        return MemoryEntry(
            message=Message(
                content=content,
                sender=sender,
                role=role,
                timestamp=datetime.fromisoformat(timestamp),
                metadata=json.loads(metadata) if metadata else {},
            ),
            importance=importance,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.

        Returns:
            Statistics dict
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM memories WHERE compressed = 1")
        compressed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM knowledge_graph")
        kg_triples = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT session_id) FROM memories WHERE session_id IS NOT NULL"
        )
        sessions = cursor.fetchone()[0]

        conn.close()

        return {
            "total_memories": total_memories,
            "compressed_memories": compressed,
            "knowledge_triples": kg_triples,
            "sessions": sessions,
            "vector_enabled": self.enable_vector,
            "compression_enabled": self.enable_compression,
        }
