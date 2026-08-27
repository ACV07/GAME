import sqlite3
import os
from config import Config

def get_db_connection():
    """Establishes and returns a SQLite database connection with row dictionary access."""
    if not os.path.exists(Config.DATA_DIR):
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_code TEXT UNIQUE NOT NULL,
            team_name TEXT NOT NULL,
            current_challenge INTEGER DEFAULT 1,
            total_score INTEGER DEFAULT 0,
            start_time TIMESTAMP,
            completion_time TIMESTAMP,
            total_time_seconds INTEGER DEFAULT 0,
            status TEXT DEFAULT 'WAITING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            device_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
        );
    ''')
    
    # Challenges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            points INTEGER NOT NULL,
            description TEXT,
            code TEXT,
            data_json TEXT NOT NULL
        );
    ''')
    
    # Submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            submitted_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            points_earned INTEGER NOT NULL,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
            FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
        );
    ''')
    
    # Event Config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')
    
    # Insert default event status if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO event_config (key, value)
        VALUES ('round_status', 'NOT_STARTED');
    ''')
    
    # Persist in-progress player work so pause/stop can resume on the same challenge
    team_cols = [row[1] for row in cursor.execute("PRAGMA table_info(teams)").fetchall()]
    if 'draft_json' not in team_cols:
        cursor.execute("ALTER TABLE teams ADD COLUMN draft_json TEXT DEFAULT ''")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
