"""
Initialize SQLite database with schema for P&ID Digital Assistant
"""
import sqlite3
import os
from pathlib import Path


def create_database():
    """Create SQLite database with schema from architecture specs"""

    # Ensure database directory exists
    db_dir = Path("database")
    db_dir.mkdir(exist_ok=True)

    db_path = db_dir / "assets.db"

    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Creating database at: {db_path}")

    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            document_number TEXT,
            document_title TEXT,
            revision TEXT,
            total_pages INTEGER,
            facility TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'documents' table")

    # Create document_pages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_pages (
            page_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            page_type TEXT,
            page_title TEXT,
            sheet_number TEXT,
            image_path TEXT NOT NULL,
            text_content TEXT,
            has_equipment BOOLEAN DEFAULT 0,
            FOREIGN KEY (document_id) REFERENCES documents(document_id)
        )
    """)
    print("✓ Created 'document_pages' table")

    # Create mock_tickets table (optional - can use hardcoded dict instead)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_or_equipment TEXT NOT NULL,
            issue_description TEXT,
            reported_date DATE,
            resolution TEXT,
            resolved_date DATE,
            status TEXT DEFAULT 'Closed',
            priority TEXT
        )
    """)
    print("✓ Created 'mock_tickets' table")

    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pages_document
        ON document_pages(document_id)
    """)
    print("✓ Created index on document_id")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pages_equipment
        ON document_pages(has_equipment)
    """)
    print("✓ Created index on has_equipment")

    # Insert mock ticket data
    mock_tickets = [
        ('PSV-101', 'Safety valve actuator slow response', '2025-09-15',
         'Actuator replaced and calibrated per manufacturer specs', '2025-09-16',
         'Closed', 'High'),
        ('FT-103A', 'Flow transmitter reading erratic', '2025-10-01',
         'Transmitter recalibrated, impulse lines cleared', '2025-10-02',
         'Closed', 'Medium'),
        ('V-102', 'Separator pressure relief valve set point verification', '2025-10-10',
         'PSV-102 tested and verified at 75 PSIG set pressure', '2025-10-10',
         'Closed', 'Low'),
        ('V-101', 'High-level alarm testing and calibration', '2025-09-20',
         'LSHH-101B tested and calibrated, alarm set at 85% level', '2025-09-21',
         'Closed', 'Medium'),
        ('C-104', 'Vibration sensor alarm during startup', '2025-09-28',
         'False alarm, sensor recalibrated, no mechanical issues found', '2025-09-29',
         'Closed', 'High'),
    ]

    cursor.executemany("""
        INSERT INTO mock_tickets
        (tag_or_equipment, issue_description, reported_date, resolution, resolved_date, status, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, mock_tickets)
    print(f"✓ Inserted {len(mock_tickets)} mock tickets")

    # Commit changes
    conn.commit()
    print(f"\n✓ Database created successfully at: {db_path}")
    print(f"  - 3 tables created")
    print(f"  - 2 indexes created")
    print(f"  - {len(mock_tickets)} mock tickets inserted")

    # Close connection
    conn.close()


if __name__ == "__main__":
    create_database()
