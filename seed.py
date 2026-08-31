import json
import os
from database import get_db_connection, init_db
from config import Config

def seed_database():
    """Populates challenges from JSON and inserts default competition teams."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Load and insert challenges from JSON
    challenges_file = os.path.join(Config.DATA_DIR, 'challenges.json')
    if os.path.exists(challenges_file):
        with open(challenges_file, 'r', encoding='utf-8') as f:
            challenges = json.load(f)
            
        for ch in challenges:
            ch_data = ch.get('data', {})
            if 'problem_statement' in ch:
                ch_data['problem_statement'] = ch['problem_statement']
            if 'sample_cases' in ch:
                ch_data['sample_cases'] = ch['sample_cases']

            cursor.execute("""
                INSERT INTO challenges (id, title, type, points, description, code, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    type=excluded.type,
                    points=excluded.points,
                    description=excluded.description,
                    code=excluded.code,
                    data_json=excluded.data_json
            """, (
                ch['id'],
                ch['title'],
                ch['type'],
                ch['points'],
                ch.get('description', ''),
                ch.get('code', '\n'.join(ch.get('lines', []))),
                json.dumps(ch_data)
            ))
        print(f"Loaded {len(challenges)} challenges into database.")

    # 2. Insert default competition teams
    default_teams = [
        ('CYBER WOLVES', 'CW2026'),
        ('BLOCK MASTERS', 'BM2026'),
        ('HACK TITANS', 'HT2026'),
        ('BYTE FORCE', 'BF2026'),
        ('CODE NINJAS', 'CN2026')
    ]
    
    for team_name, team_code in default_teams:
        cursor.execute("""
            INSERT OR IGNORE INTO teams (team_code, team_name, current_challenge, total_score, status)
            VALUES (?, ?, 1, 0, 'WAITING')
        """, (team_code, team_name))
        
    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
