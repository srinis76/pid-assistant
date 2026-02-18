"""
Restore V1 Databases

Copies V1 backup databases back to overwrite V2 data.
Use this if V2 ingestion causes issues before demo.

Usage:
    python scripts/restore_v1.py
"""

import shutil
from pathlib import Path

BACKUP_DIR = Path("database/backups")
DB_DIR = Path("database")


def restore():
    v1_sqlite = BACKUP_DIR / "assets_v1.db"
    v1_vector = BACKUP_DIR / "vector_store_v1"

    if not v1_sqlite.exists():
        print(f"Error: V1 SQLite backup not found at {v1_sqlite}")
        return False

    if not v1_vector.exists():
        print(f"Error: V1 vector store backup not found at {v1_vector}")
        return False

    print("Restoring V1 databases...")

    # Restore SQLite
    shutil.copy2(v1_sqlite, DB_DIR / "assets.db")
    print(f"  Restored: assets.db")

    # Restore ChromaDB vector store
    target_vector = DB_DIR / "vector_store"
    if target_vector.exists():
        shutil.rmtree(target_vector)
    shutil.copytree(v1_vector, target_vector)
    print(f"  Restored: vector_store/")

    print("\nV1 databases restored. Restart Streamlit to pick up changes.")
    return True


if __name__ == "__main__":
    restore()
