import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'round2-arena-cyber-secret-2026-key'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DATABASE_PATH = os.path.join(DATA_DIR, 'arena.db')
    
    # Session heartbeat timeout (in seconds)
    # If no heartbeat is received from team active device for 25 seconds, session is marked inactive
    HEARTBEAT_TIMEOUT = 25
    
    # Admin Credentials for organizer portal
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin2026'
