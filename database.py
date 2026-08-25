import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jeeva_setu.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            village TEXT,
            registered_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            parameter_name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            synced INTEGER DEFAULT 1,
            device_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            note TEXT NOT NULL,
            added_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            otp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            verified INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized at", DB_PATH)


if __name__ == "__main__":
    init_db()
