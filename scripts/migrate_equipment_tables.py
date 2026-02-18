"""
Migration script to add equipment-related tables to existing database.

Run this script to upgrade an existing database with the new tables
for vision-based extraction without losing existing data.
"""
import sqlite3
from pathlib import Path


def migrate_database():
    """Add new equipment tables to existing database"""

    db_path = Path("database/assets.db")

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Run scripts/init_database.py first to create a new database.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating database: {db_path}")
    print("=" * 50)

    # Check which tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    # Equipment table
    if 'equipment' not in existing_tables:
        cursor.execute("""
            CREATE TABLE equipment (
                equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_id INTEGER,
                tag TEXT NOT NULL,
                equipment_type TEXT,
                name TEXT,
                service TEXT,
                design_pressure TEXT,
                design_temperature TEXT,
                operating_pressure TEXT,
                operating_temperature TEXT,
                capacity TEXT,
                size TEXT,
                material TEXT,
                specs_json TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(document_id),
                FOREIGN KEY (page_id) REFERENCES document_pages(page_id)
            )
        """)
        print("✓ Created 'equipment' table")
    else:
        print("- 'equipment' table already exists")

    # Instruments table
    if 'instruments' not in existing_tables:
        cursor.execute("""
            CREATE TABLE instruments (
                instrument_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_id INTEGER,
                tag TEXT NOT NULL,
                instrument_type TEXT,
                function TEXT,
                setpoint TEXT,
                range_min TEXT,
                range_max TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(document_id),
                FOREIGN KEY (page_id) REFERENCES document_pages(page_id)
            )
        """)
        print("✓ Created 'instruments' table")
    else:
        print("- 'instruments' table already exists")

    # Equipment-Instruments relationship table
    if 'equipment_instruments' not in existing_tables:
        cursor.execute("""
            CREATE TABLE equipment_instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL,
                instrument_id INTEGER NOT NULL,
                relationship_type TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id),
                FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id)
            )
        """)
        print("✓ Created 'equipment_instruments' table")
    else:
        print("- 'equipment_instruments' table already exists")

    # Connections table
    if 'connections' not in existing_tables:
        cursor.execute("""
            CREATE TABLE connections (
                connection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                source_tag TEXT NOT NULL,
                destination_tag TEXT NOT NULL,
                line_number TEXT,
                pipe_size TEXT,
                pipe_class TEXT,
                service TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(document_id)
            )
        """)
        print("✓ Created 'connections' table")
    else:
        print("- 'connections' table already exists")

    # Create indexes (IF NOT EXISTS handles duplicates)
    indexes = [
        ("idx_equipment_tag", "equipment(tag)"),
        ("idx_equipment_document", "equipment(document_id)"),
        ("idx_instruments_tag", "instruments(tag)"),
        ("idx_connections_source", "connections(source_tag)"),
        ("idx_connections_dest", "connections(destination_tag)"),
    ]

    for idx_name, idx_def in indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
    print(f"✓ Created/verified {len(indexes)} indexes")

    # Commit changes
    conn.commit()
    conn.close()

    print("=" * 50)
    print("✓ Migration complete!")


if __name__ == "__main__":
    migrate_database()
