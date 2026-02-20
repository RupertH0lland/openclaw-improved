"""Memory store - vector store + SQLite for facts, preferences, context."""
import sqlite3
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


class MemoryStore:
    """Vector store (Chroma) + SQLite for structured facts and preferences."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.collection = None
        if HAS_CHROMA:
            chroma_path = self.data_dir / "chroma"
            self.chroma = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.chroma.get_or_create_collection("facts", metadata={"hnsw:space": "cosine"})
        self.db_path = self.data_dir / "memory.db"
        self._init_sql()

    def _init_sql(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_fact(self, text: str, metadata: dict | None = None) -> str:
        """Add a fact to the vector store. Returns doc id."""
        import uuid
        doc_id = f"fact_{uuid.uuid4().hex[:12]}"
        if self.collection:
            meta = metadata or {}
            self.collection.add(ids=[doc_id], documents=[text], metadatas=[meta])
        return doc_id

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Search for relevant facts."""
        if not self.collection:
            return []
        results = self.collection.query(query_texts=[query], n_results=n_results)
        out = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                dist = results["distances"][0][i] if results.get("distances") else 0
                out.append({"id": doc_id, "content": doc, "distance": dist})
        return out

    def get_preference(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_preference(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                (key, value),
            )
