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
            
            # Существующие таблицы
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
            
            # ===== НОВЫЕ ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ОПОВЕЩЕНИЙ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    weekday INTEGER NOT NULL,
                    event_time TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, weekday, event_time)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_takes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    group_code TEXT NOT NULL,
                    meeting_place TEXT NOT NULL,
                    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_date DATE NOT NULL,
                    is_cancelled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    user_id TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    scheduled_date DATE NOT NULL,
                    reminder_sent BOOLEAN DEFAULT 0,
                    taken_by TEXT,
                    group_code TEXT,
                    meeting_place TEXT,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    UNIQUE(event_id, scheduled_date)
                )
            ''')
            
            conn.commit()
    
    # ===== СУЩЕСТВУЮЩИЕ МЕТОДЫ =====
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
    
    def save_dual_colors(self, color1: str, color2: str, updated_by: str = None):
        self.set_setting('mcl_color_1', color1, updated_by)
        self.set_setting('mcl_color_2', color2, updated_by)
    
    def get_dual_colors(self):
        color1 = self.get_setting('mcl_color_1') or 'Pink'
        color2 = self.get_setting('mcl_color_2') or 'Blue'
        return color1, color2
    
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
    
    def log_command(self, command: str, user_id: str, success: bool, recipients: int = None, details: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO command_stats (command, user_id, success, recipients, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (command, user_id, 1 if success else 0, recipients, details))
            conn.commit()
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ СИСТЕМЫ ОПОВЕЩЕНИЙ =====
    
    # ----- МЕРОПРИЯТИЯ -----
    def add_event(self, name: str, weekday: int, event_time: str, created_by: str) -> int:
        """Добавить новое мероприятие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO events (name, weekday, event_time, created_by)
                VALUES (?, ?, ?, ?)
            ''', (name, weekday, event_time, created_by))
            conn.commit()
            return cursor.lastrowid
    
    def update_event(self, event_id: int, **kwargs) -> bool:
        """Обновить мероприятие"""
        allowed = {'name', 'weekday', 'event_time', 'enabled'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        
        sets = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [event_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE events 
                SET {sets}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_events(self, enabled_only: bool = True, weekday: int = None):
        """Получить список мероприятий"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM events WHERE 1=1'
            params = []
            
            if enabled_only:
                query += ' AND enabled = 1'
            if weekday is not None:
                query += ' AND weekday = ?'
                params.append(weekday)
            
            query += ' ORDER BY weekday, event_time'
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    
    def get_event(self, event_id: int):
        """Получить мероприятие по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
    
    def delete_event(self, event_id: int, soft: bool = False) -> bool:
        """Удалить мероприятие
        
        Args:
            event_id: ID мероприятия
            soft: если True - только отключить (enabled=0), если False - полностью удалить
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if soft:
                # Мягкое удаление - только отключаем
                cursor.execute('UPDATE events SET enabled = 0 WHERE id = ?', (event_id,))
            else:
                # Полное удаление
                # Сначала удаляем связанные записи
                cursor.execute('DELETE FROM event_takes WHERE event_id = ?', (event_id,))
                cursor.execute('DELETE FROM event_logs WHERE event_id = ?', (event_id,))
                cursor.execute('DELETE FROM event_schedule WHERE event_id = ?', (event_id,))
                # Затем само мероприятие
                cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ----- ВЗЯТИЕ МЕРОПРИЯТИЙ -----
    def take_event(self, event_id: int, user_id: str, user_name: str, 
                   group_code: str, meeting_place: str, event_date: str) -> int:
        """Записать взятие МП"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO event_takes 
                (event_id, user_id, user_name, group_code, meeting_place, event_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_id, user_id, user_name, group_code, meeting_place, event_date))
            conn.commit()
            
            cursor.execute('''
                UPDATE event_schedule 
                SET taken_by = ?, group_code = ?, meeting_place = ?
                WHERE event_id = ? AND scheduled_date = ?
            ''', (user_id, group_code, meeting_place, event_id, event_date))
            conn.commit()
            
            return cursor.lastrowid
    
    def get_event_takes(self, user_id: str = None, days: int = 30):
        """Получить статистику взятий"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT et.*, e.name as event_name
                FROM event_takes et
                JOIN events e ON et.event_id = e.id
                WHERE et.event_date >= date('now', ?) AND et.is_cancelled = 0
            '''
            params = [f'-{days} days']
            
            if user_id:
                query += ' AND et.user_id = ?'
                params.append(user_id)
            
            query += ' ORDER BY et.event_date DESC'
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    
    def get_top_organizers(self, limit: int = 10):
        """Топ организаторов МП"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, COUNT(*) as count
                FROM event_takes
                WHERE is_cancelled = 0
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    # ----- РАСПИСАНИЕ -----
    def generate_schedule(self, days_ahead: int = 14):
        """Сгенерировать расписание на ближайшие дни"""
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        today = datetime.now(msk_tz).date()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            events = self.get_events(enabled_only=True)
            
            for event in events:
                for day_offset in range(days_ahead):
                    check_date = today + timedelta(days=day_offset)
                    if check_date.weekday() == event['weekday']:
                        cursor.execute('''
                            INSERT OR IGNORE INTO event_schedule 
                            (event_id, scheduled_date)
                            VALUES (?, ?)
                        ''', (event['id'], check_date.isoformat()))
            
            conn.commit()
            return cursor.rowcount
    
    def get_today_events(self):
        """Мероприятия на сегодня"""
        from datetime import datetime
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        today = datetime.now(msk_tz).date()
        weekday = today.weekday()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, s.id as schedule_id, s.reminder_sent, s.taken_by,
                       s.group_code, s.meeting_place
                FROM events e
                LEFT JOIN event_schedule s ON e.id = s.event_id AND s.scheduled_date = ?
                WHERE e.weekday = ? AND e.enabled = 1
                ORDER BY e.event_time
            ''', (today.isoformat(), weekday))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    
    def mark_reminder_sent(self, event_id: int, event_date: str):
        """Отметить что напоминание отправлено"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE event_schedule 
                SET reminder_sent = 1 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (event_id, event_date))
            conn.commit()
    
    # ----- ЛОГИРОВАНИЕ СОБЫТИЙ -----
    def log_event_action(self, event_id: int, action: str, user_id: str = None, details: str = None):
        """Логирование действий с мероприятиями"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO event_logs (event_id, action, user_id, details)
                VALUES (?, ?, ?, ?)
            ''', (event_id, action, user_id, details))
            conn.commit()

db = Database()