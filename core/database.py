"""Модуль работы с SQLite базой данных"""
import sqlite3
from datetime import datetime
import pytz

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
            
            # Таблицы для системы мероприятий
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
            
            # Таблицы для авто-рекламы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_ad (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT NOT NULL,
                    image_url TEXT,
                    channel_id TEXT NOT NULL,
                    interval_minutes INTEGER DEFAULT 65,
                    sleep_start TEXT DEFAULT '02:00',
                    sleep_end TEXT DEFAULT '06:30',
                    last_sent TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_ad_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN,
                    error TEXT
                )
            ''')
            
            # Таблицы для системы регистрации на CAPT
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capt_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    user_name TEXT NOT NULL,
                    list_type TEXT NOT NULL CHECK(list_type IN ('main', 'reserve')),
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS capt_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    is_active BOOLEAN DEFAULT 0,
                    started_by TEXT,
                    started_at TIMESTAMP,
                    ended_by TEXT,
                    ended_at TIMESTAMP,
                    main_message_id TEXT,
                    reserve_message_id TEXT,
                    main_channel_id TEXT,
                    reserve_channel_id TEXT
                )
            ''')

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ЗАЯВОК =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    static TEXT NOT NULL,
                    previous_families TEXT,
                    prime_time TEXT NOT NULL,
                    hours_per_day TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',  -- pending, accepted, rejected, interviewing
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    reject_reason TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Добавляем настройки по умолчанию для системы заявок
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('applications_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('applications_log_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('applications_recruit_role', 'null'))
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('applications_member_role', 'null'))
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('applications_settings_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO application_settings (key, value) VALUES (?, ?)', 
                        ('submit_channel', 'null'))

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
    
    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ОПОВЕЩЕНИЙ =====
    
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
        """Удалить мероприятие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if soft:
                cursor.execute('UPDATE events SET enabled = 0 WHERE id = ?', (event_id,))
            else:
                cursor.execute('DELETE FROM event_takes WHERE event_id = ?', (event_id,))
                cursor.execute('DELETE FROM event_logs WHERE event_id = ?', (event_id,))
                cursor.execute('DELETE FROM event_schedule WHERE event_id = ?', (event_id,))
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
    
    def get_top_organizers(self, limit: int = 10, days: int = 30):
        """Топ организаторов МП за последние N дней"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, COUNT(*) as count
                FROM event_takes
                WHERE is_cancelled = 0 
                AND event_date >= date('now', ?)
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT ?
            ''', (f'-{days} days', limit))
            
            result = cursor.fetchall()
            
            if not result:
                cursor.execute('''
                    SELECT user_id, user_name, COUNT(*) as count
                    FROM event_takes
                    WHERE is_cancelled = 0
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT ?
                ''', (limit,))
                result = cursor.fetchall()
            
            return result

    def get_event_stats_summary(self):
        """Получить сводную статистику по мероприятиям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM events')
            total_events = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM events WHERE enabled = 1')
            active_events = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM event_takes WHERE is_cancelled = 0')
            total_takes = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM event_takes 
                WHERE is_cancelled = 0 
                AND event_date >= date('now', '-30 days')
            ''')
            takes_30d = cursor.fetchone()[0]
            
            msk_tz = pytz.timezone('Europe/Moscow')
            today = datetime.now(msk_tz).date().isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM event_takes 
                WHERE is_cancelled = 0 AND event_date = ?
            ''', (today,))
            takes_today = cursor.fetchone()[0]
            
            return {
                'total_events': total_events,
                'active_events': active_events,
                'total_takes': total_takes,
                'takes_30d': takes_30d,
                'takes_today': takes_today
            }
    
    # ----- РАСПИСАНИЕ -----
    def generate_schedule(self, days_ahead: int = 14):
        """Сгенерировать расписание на ближайшие дни"""
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)  # aware datetime
        today = now.date()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            events = self.get_events(enabled_only=True)
            
            for event in events:
                for day_offset in range(days_ahead):
                    check_date = today + timedelta(days=day_offset)
                    if check_date.weekday() == event['weekday']:
                        # Создаем aware datetime для времени мероприятия
                        event_time = datetime.strptime(event['event_time'], "%H:%M").time()
                        event_datetime = msk_tz.localize(datetime.combine(check_date, event_time))
                        
                        # Пропускаем, если время уже прошло сегодня
                        if day_offset == 0 and event_datetime < now:
                            continue
                        
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
        today = datetime.now(msk_tz).date()  # aware -> date
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
    
    # ===== АВТО-РЕКЛАМА =====
    def save_ad_settings(self, message_text: str, image_url: str, channel_id: str, 
                        interval: int = 65, sleep_start: str = "02:00", 
                        sleep_end: str = "06:30", updated_by: str = None) -> bool:
        """Сохранить настройки авто-рекламы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE auto_ad SET is_active = 0')
            cursor.execute('''
                INSERT INTO auto_ad 
                (message_text, image_url, channel_id, interval_minutes, 
                sleep_start, sleep_end, created_by, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (message_text, image_url, channel_id, interval, 
                sleep_start, sleep_end, updated_by))
            conn.commit()
            return cursor.rowcount > 0

    def get_active_ad(self):
        """Получить активные настройки авто-рекламы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auto_ad WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def update_last_sent(self, ad_id: int):
        """Обновить время последней отправки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE auto_ad SET last_sent = CURRENT_TIMESTAMP WHERE id = ?', (ad_id,))
            conn.commit()

    def log_ad_sent(self, success: bool, error: str = None):
        """Записать в лог отправку рекламы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auto_ad_logs (success, error)
                VALUES (?, ?)
            ''', (1 if success else 0, error))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ЗАЯВОК =====
    def get_application_setting(self, key: str) -> str:
        """Получить настройку системы заявок"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM application_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set_application_setting(self, key: str, value: str, updated_by: str = None):
        """Установить настройку системы заявок"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO application_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            # Проверяем, что updated_by не None перед логированием
            if updated_by:
                self.log_action(updated_by, f"SET_APP_SETTING", f"{key}={value}")

    def create_application(self, user_id: str, user_name: str, nickname: str, 
                      static: str, previous_families: str, prime_time: str, 
                      hours_per_day: str) -> tuple:
        """Создать новую заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже активной заявки (pending или interviewing)
            cursor.execute('''
                SELECT id FROM applications 
                WHERE user_id = ? AND status IN ('pending', 'interviewing')
            ''', (user_id,))
            
            if cursor.fetchone():
                return None, "❌ У вас уже есть активная заявка"
            
            # Проверяем, была ли уже принятая заявка (опционально)
            cursor.execute('''
                SELECT id FROM applications 
                WHERE user_id = ? AND status = 'accepted'
            ''', (user_id,))
            
            if cursor.fetchone():
                return None, "❌ Вы уже приняты в семью"
            
            cursor.execute('''
                INSERT INTO applications 
                (user_id, user_name, nickname, static, previous_families, prime_time, hours_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, user_name, nickname, static, previous_families, prime_time, hours_per_day))
            
            conn.commit()
            return cursor.lastrowid, None

    def get_pending_applications(self):
        """Получить все ожидающие заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, user_name, nickname, static, previous_families, 
                    prime_time, hours_per_day, created_at
                FROM applications 
                WHERE status = 'pending'
                ORDER BY created_at
            ''')
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]

    def get_application(self, app_id: int):
        """Получить заявку по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            return dict(zip(columns, row)) if row else None

    def accept_application(self, app_id: int, reviewer_id: str):
        """Принять заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE applications 
                SET status = 'accepted', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reject_reason = ?
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, reason, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def set_interviewing(self, app_id: int, reviewer_id: str):
        """Назначить обзвон"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE applications 
                SET status = 'interviewing', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def load_application_settings(self):
        """Загрузить все настройки системы заявок в CONFIG"""
        from core.config import CONFIG  # ← импорт внутри метода
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM application_settings')
            settings = dict(cursor.fetchall())
        
        for key, value in settings.items():
            if value and value.lower() != 'null':
                CONFIG[key] = value

db = Database()