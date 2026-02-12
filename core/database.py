"""Модуль работы с SQLite базой данных"""
import sqlite3

class Database:
    def __init__(self):
        self.db_path = 'unit_bot.db'
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    username TEXT,
                    added_by TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    note TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    discord_id TEXT PRIMARY KEY,
                    added_by TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_super BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    success BOOLEAN,
                    recipients INTEGER,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    def add_user(self, discord_id: str, added_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (discord_id, username, added_by, is_active)
                VALUES (?, ?, ?, 1)
            ''', (discord_id, discord_id, added_by))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_user(self, discord_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE discord_id = ?', (discord_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT discord_id FROM users WHERE is_active = 1 ORDER BY added_at DESC')
            return [row[0] for row in cursor.fetchall()]
    
    def get_users_with_details(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.discord_id, u.username, u.added_by, u.added_at, u.last_used,
                       CASE WHEN a.discord_id IS NOT NULL THEN 1 ELSE 0 END as is_admin,
                       CASE WHEN a.is_super = 1 THEN 1 ELSE 0 END as is_super
                FROM users u
                LEFT JOIN admins a ON u.discord_id = a.discord_id
                WHERE u.is_active = 1
                ORDER BY 
                    CASE WHEN a.is_super = 1 THEN 0
                         WHEN a.discord_id IS NOT NULL THEN 1
                         ELSE 2 END,
                    u.added_at DESC
            ''')
            return cursor.fetchall()
    
    def user_exists(self, discord_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE discord_id = ? AND is_active = 1', (discord_id,))
            return cursor.fetchone() is not None
    
    def update_last_used(self, discord_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_used = CURRENT_TIMESTAMP WHERE discord_id = ?', (discord_id,))
            conn.commit()
    
    # ===== АДМИНИСТРАТОРЫ =====
    def add_admin(self, discord_id: str, added_by: str, is_super: bool = False):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (discord_id, username, added_by) VALUES (?, ?, ?)',
                         (discord_id, discord_id, added_by))
            cursor.execute('''
                INSERT OR REPLACE INTO admins (discord_id, added_by, is_super)
                VALUES (?, ?, ?)
            ''', (discord_id, added_by, 1 if is_super else 0))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_admin(self, discord_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM admins WHERE discord_id = ?', (discord_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_admin(self, discord_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM admins WHERE discord_id = ?', (discord_id,))
            return cursor.fetchone() is not None
    
    def is_super_admin(self, discord_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_super FROM admins WHERE discord_id = ?', (discord_id,))
            result = cursor.fetchone()
            return result and result[0] == 1
    
    def get_admins(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.discord_id, a.added_by, a.added_at, a.is_super, u.username
                FROM admins a
                LEFT JOIN users u ON a.discord_id = u.discord_id
                ORDER BY a.is_super DESC, a.added_at ASC
            ''')
            return cursor.fetchall()
    
    # ===== НАСТРОЙКИ =====
    def set_setting(self, key: str, value: str, updated_by: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_by, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value, updated_by))
            conn.commit()
    
    def get_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_all_settings(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            return dict(cursor.fetchall())
    
    # ===== DUAL MCL ЦВЕТА =====
    def save_dual_colors(self, color1: str, color2: str, updated_by: str = None):
        self.set_setting('mcl_color_1', color1, updated_by)
        self.set_setting('mcl_color_2', color2, updated_by)
    
    def get_dual_colors(self):
        color1 = self.get_setting('mcl_color_1') or 'Pink'
        color2 = self.get_setting('mcl_color_2') or 'Blue'
        return color1, color2
    
    # ===== ЛОГИРОВАНИЕ =====
    def log_action(self, user_id: str, action: str, details: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_log (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            conn.commit()
    
    def get_recent_logs(self, limit: int = 20):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, user_id, action, details
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    # ===== СТАТИСТИКА =====
    def log_command(self, command: str, user_id: str, success: bool, recipients: int = None, details: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO command_stats (command, user_id, success, recipients, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (command, user_id, 1 if success else 0, recipients, details))
            conn.commit()

db = Database()