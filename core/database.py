"""Модуль работы с SQLite базой данных"""
import sqlite3
from datetime import datetime
import pytz

class Database:
    def __init__(self):
        self.db_path = 'bot_data.db'
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path, timeout=15)
    
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

            try:
                cursor.execute('ALTER TABLE applications ADD COLUMN answers TEXT')
                print("✅ Колонка answers добавлена в таблицу applications")
            except sqlite3.OperationalError:
                pass  # колонка уже существует

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

            # ===== ТАБЛИЦА ДЛЯ ХРАНЕНИЯ СООБЩЕНИЙ С ЗАЯВКАМИ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
                    UNIQUE(application_id)
                )
            ''')

            # ===== ТАБЛИЦА ДЛЯ НАСТРОЙКИ ПОЛЕЙ ЗАЯВКИ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_name TEXT NOT NULL,
                    field_description TEXT,
                    placeholder TEXT,
                    required BOOLEAN DEFAULT 1,
                    field_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

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
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                reject_reason TEXT,
                answers TEXT
            )
        ''')

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ AFK =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS afk_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    user_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    hours INTEGER NOT NULL,
                    until_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS afk_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Добавляем настройки по умолчанию
            cursor.execute('INSERT OR IGNORE INTO afk_settings (key, value) VALUES (?, ?)', 
                        ('afk_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO afk_settings (key, value) VALUES (?, ?)', 
                        ('afk_max_hours', '24'))
            cursor.execute('INSERT OR IGNORE INTO afk_settings (key, value) VALUES (?, ?)', 
                        ('afk_settings_channel', 'null'))

            conn.commit()

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ TIR =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tier_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    arena_link TEXT NOT NULL,
                    screenshots TEXT NOT NULL,
                    additional TEXT,
                    target_tier TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    reject_reason TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tier_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tier_requirements (
                    tier TEXT PRIMARY KEY,
                    requirements TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tier_application_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    FOREIGN KEY (application_id) REFERENCES tier_applications (id) ON DELETE CASCADE,
                    UNIQUE(application_id)
                )
            ''')

            # Таблица для ролей, выдаваемых при принятии заявки
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_reward_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_id TEXT NOT NULL,
                    added_by TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Добавляем настройки по умолчанию
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier_submit_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier_applications_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier_log_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier_info_channel', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier_checker_role', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier3_role', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier2_role', 'null'))
            cursor.execute('INSERT OR IGNORE INTO tier_settings (key, value) VALUES (?, ?)', 
                        ('tier1_role', 'null'))

            # Настройки по умолчанию
            cursor.execute('INSERT OR IGNORE INTO tier_requirements (tier, requirements) VALUES (?, ?)', 
                        ('tier3', '1. Активность в семье\n2. Участие в мероприятиях\n3. Положительная репутация'))
            cursor.execute('INSERT OR IGNORE INTO tier_requirements (tier, requirements) VALUES (?, ?)', 
                        ('tier2', '1. Выполнение требований Tier 3\n2. Регулярные отчёты\n3. Помощь новичкам'))
            cursor.execute('INSERT OR IGNORE INTO tier_requirements (tier, requirements) VALUES (?, ?)', 
                        ('tier1', '1. Выполнение требований Tier 2\n2. Лидерские качества\n3. Вклад в развитие семьи'))

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ СТАТИСТИКИ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    new_members INTEGER DEFAULT 0,
                    left_members INTEGER DEFAULT 0,
                    new_applications INTEGER DEFAULT 0,
                    accepted_applications INTEGER DEFAULT 0,
                    max_voice_online INTEGER DEFAULT 0,
                    capt_registrations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Добавляем настройки по умолчанию
            cursor.execute('INSERT OR IGNORE INTO stats_settings (key, value) VALUES (?, ?)', 
                        ('stats_backup_enabled', 'true'))
            cursor.execute('INSERT OR IGNORE INTO stats_settings (key, value) VALUES (?, ?)', 
                        ('stats_channel', 'null'))

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ОТПУСКОВ =====

            # Таблица заявок на отпуск
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vacation_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    saved_roles TEXT,
                    guild_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    until_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    reject_reason TEXT
                )
            ''')

            # Таблица настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vacation_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Таблица активных отпусков (куда переносятся одобренные заявки)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vacation_active (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    until_date DATE NOT NULL,
                    saved_roles TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для хранения ID сообщений (для восстановления кнопок)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vacation_application_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    FOREIGN KEY (application_id) REFERENCES vacation_applications (id) ON DELETE CASCADE,
                    UNIQUE(application_id)
                )
            ''')

            # Настройки по умолчанию
            cursor.execute('INSERT OR IGNORE INTO vacation_settings (key, value) VALUES (?, ?)', 
                        ('vacation_max_days', '30'))

            # ========== ВЫЗОВ ТАБЛИЦ СИСТЕМ ИГР ========== 
            # self.init_games_tables()
            # print("⚠️ Таблицы игр временно отключены")

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ДНЕЙ РОЖДЕНИЯ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    birthday_date TEXT NOT NULL,  -- формат DD.MM
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ MCL =====

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mcl_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    user_name TEXT NOT NULL,
                    list_type TEXT NOT NULL CHECK(list_type IN ('main', 'reserve')),
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mcl_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    is_active BOOLEAN DEFAULT 0,
                    started_by TEXT,
                    started_at TIMESTAMP,
                    ended_by TEXT,
                    ended_at TIMESTAMP,
                    main_message_id TEXT,
                    reserve_message_id TEXT,
                    main_channel_id TEXT,
                    reserve_channel_id TEXT,
                    event_name TEXT,
                    event_time TEXT,
                    additional_info TEXT
                )
            ''')

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
        """Принять заявку (из любого активного статуса)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли заявка
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Заявка {app_id} не найдена")
                return False
            
            current_status = result[0]
            print(f"📊 Текущий статус заявки {app_id}: {current_status}")
            
            # Разрешаем принимать заявки в статусах 'pending' и 'interviewing'
            if current_status not in ['pending', 'interviewing']:
                print(f"❌ Заявка {app_id} в статусе {current_status}, нельзя принять")
                return False
            
            cursor.execute('''
                UPDATE applications 
                SET status = 'accepted', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status IN ('pending', 'interviewing')
            ''', (reviewer_id, app_id))
            
            conn.commit()
            success = cursor.rowcount > 0
            print(f"✅ Результат принятия: {success}")
            return success

    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверим, существует ли заявка
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            print(f"📊 Текущий статус заявки {app_id}: {result}")
            
            if not result:
                print(f"❌ Заявка {app_id} не найдена")
                return False
            
            current_status = result[0]
            
            # Разрешаем отклонять заявки в любом статусе, кроме 'accepted'
            if current_status == 'accepted':
                print(f"❌ Заявка {app_id} уже принята, нельзя отклонить")
                return False
            
            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reject_reason = ?
                WHERE id = ?
            ''', (reviewer_id, reason, app_id))
            
            conn.commit()
            success = cursor.rowcount > 0
            print(f"✅ Результат отклонения: {success}, затронуто строк: {cursor.rowcount}")
            return success

    def set_interviewing(self, app_id: int, reviewer_id: str):
        """Назначить обзвон"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, что заявка в статусе 'pending'
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            
            if not result or result[0] != 'pending':
                print(f"❌ Нельзя назначить обзвон: заявка {app_id} в статусе {result[0] if result else 'not found'}")
                return False
            
            cursor.execute('''
                UPDATE applications 
                SET status = 'interviewing', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, app_id))
            
            conn.commit()
            success = cursor.rowcount > 0
            print(f"✅ Обзвон назначен: {success}")
            return success

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

    # ===== МЕТОДЫ ДЛЯ ГИБКИХ ПОЛЕЙ ЗАЯВКИ =====

    def get_application_fields(self):
        """Получить все активные поля заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, field_name, field_description, placeholder, required, field_order
                FROM application_fields 
                WHERE is_active = 1 
                ORDER BY field_order
            ''')
            rows = cursor.fetchall()
            return [{'id': row[0], 'name': row[1], 'description': row[2], 
                    'placeholder': row[3], 'required': row[4], 'order': row[5]} for row in rows]

    def add_application_field(self, field_name: str, field_description: str, placeholder: str, required: bool, order: int, added_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO application_fields (field_name, field_description, placeholder, required, field_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (field_name, field_description, placeholder, 1 if required else 0, order))
            conn.commit()
            self.log_action(added_by, "ADD_APP_FIELD", f"{field_name}")

    def remove_application_field(self, field_id: int, removed_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE application_fields SET is_active = 0 WHERE id = ?', (field_id,))
            conn.commit()
            self.log_action(removed_by, "REMOVE_APP_FIELD", f"ID {field_id}")

    def update_field_order(self, field_id: int, new_order: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE application_fields SET field_order = ? WHERE id = ?', (new_order, field_id))
            conn.commit()

    def create_application_dynamic(self, user_id: str, user_name: str, answers_json: str) -> tuple:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем активную заявку
            cursor.execute('SELECT id FROM applications WHERE user_id = ? AND status IN ("pending", "interviewing")', (user_id,))
            if cursor.fetchone():
                return None, "❌ У вас уже есть активная заявка"
            
            cursor.execute('''
                INSERT INTO applications (user_id, user_name, answers, status)
                VALUES (?, ?, ?, 'pending')
            ''', (user_id, user_name, answers_json))
            
            conn.commit()
            return cursor.lastrowid, None

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ЗАЯВОК (сообщения) =====
    
    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения с заявкой"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO application_messages (application_id, channel_id, message_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (application_id, channel_id, message_id, user_id))
            conn.commit()
            self.log_action(user_id, "SAVE_APP_MESSAGE", f"App {application_id}, Msg {message_id}")
    
    def get_all_application_messages(self):
        """Получить все сохранённые сообщения с заявками"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT am.application_id, am.channel_id, am.message_id, am.user_id,
                       a.status, a.user_id as applicant_id, a.nickname
                FROM application_messages am
                JOIN applications a ON am.application_id = a.id
                WHERE a.status IN ('pending', 'interviewing')
            ''')
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def delete_application_message(self, application_id: int):
        """Удалить запись о сообщении после обработки заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM application_messages WHERE application_id = ?', (application_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_application_by_message(self, message_id: str):
        """Получить заявку по ID сообщения"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.* FROM applications a
                JOIN application_messages am ON a.id = am.application_id
                WHERE am.message_id = ?
            ''', (message_id,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            return dict(zip(columns, row)) if row else None

    def reset_user_applications(self, user_id: str, reset_by: str = None):
        """Сбросить все заявки пользователя (для возможности подать новую)"""
        print(f"🔍 database.py: Сброс пользователя {user_id} от {reset_by}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Сначала проверим, есть ли заявки у пользователя
            cursor.execute('SELECT COUNT(*) FROM applications WHERE user_id = ?', (user_id,))
            count = cursor.fetchone()[0]
            print(f"📊 Найдено заявок: {count}")
            
            if count == 0:
                return False, f"❌ У пользователя {user_id} нет заявок"
            
            # Удаляем записи о сообщениях (если есть)
            cursor.execute('''
                DELETE FROM application_messages 
                WHERE application_id IN (SELECT id FROM applications WHERE user_id = ?)
            ''', (user_id,))
            deleted_messages = cursor.rowcount
            print(f"✅ Удалено записей о сообщениях: {deleted_messages}")
            
            # Удаляем все заявки пользователя
            cursor.execute('''
                DELETE FROM applications 
                WHERE user_id = ?
            ''', (user_id,))
            
            deleted_count = cursor.rowcount
            print(f"✅ Удалено заявок: {deleted_count}")
            
            conn.commit()
            
            if deleted_count > 0 and reset_by:
                self.log_action(reset_by, "RESET_USER_APPLICATIONS", f"User {user_id}, deleted {deleted_count} applications")
            
            return True, f"✅ Удалено {deleted_count} заявок пользователя <@{user_id}>"

    def close_user_applications(self, user_id: str):
        """Закрыть все активные заявки пользователя при выходе с сервера"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем активные заявки
            cursor.execute('''
                SELECT id FROM applications 
                WHERE user_id = ? AND status IN ('pending', 'interviewing')
            ''', (user_id,))
            apps = cursor.fetchall()
            
            if not apps:
                return 0
            
            # Закрываем все заявки
            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reject_reason = ?
                WHERE user_id = ? AND status IN ('pending', 'interviewing')
            ''', ('system', 'Пользователь покинул сервер', user_id))
            
            # Удаляем записи о сообщениях
            for app in apps:
                cursor.execute('DELETE FROM application_messages WHERE application_id = ?', (app[0],))
            
            conn.commit()
            return len(apps)

    def get_active_application_id(self, user_id: str):
        """Получить ID активной заявки пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM applications 
                WHERE user_id = ? AND status IN ('pending', 'interviewing')
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_interview_channels_for_user(self, user_id: str):
        """Получить все каналы обзвона, связанные с пользователем"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Получаем ID активной заявки
            app_id = self.get_active_application_id(user_id)
            
            if app_id:
                # Ищем по ID заявки (хранится в application_messages)
                cursor.execute('''
                    SELECT channel_id, message_id FROM application_messages 
                    WHERE application_id = ?
                ''', (app_id,))
                result = cursor.fetchone()
                if result:
                    return [{'channel_id': result[0], 'message_id': result[1], 'type': 'by_application'}]
            
            return []

    def create_application_dynamic(self, user_id: str, user_name: str, answers_json: str) -> tuple:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем активную заявку
            cursor.execute('SELECT id FROM applications WHERE user_id = ? AND status IN ("pending", "interviewing")', (user_id,))
            if cursor.fetchone():
                return None, "❌ У вас уже есть активная заявка"
            
            cursor.execute('''
                INSERT INTO applications (user_id, user_name, answers, status)
                VALUES (?, ?, ?, 'pending')
            ''', (user_id, user_name, answers_json))
            
            conn.commit()
            return cursor.lastrowid, None

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ AFK =====
    
    def get_afk_setting(self, key: str) -> str:
        """Получить настройку AFK"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM afk_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_afk_setting(self, key: str, value: str, updated_by: str = None):
        """Установить настройку AFK"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO afk_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_AFK_SETTING", f"{key}={value}")
    
    def add_afk_user(self, user_id: str, user_name: str, reason: str, hours: int) -> tuple:
        """Добавить пользователя в AFK"""
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        until_time = datetime.now(msk_tz) + timedelta(hours=hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, не в AFK ли уже
            cursor.execute('SELECT id FROM afk_users WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return False, "❌ Вы уже в AFK"
            
            cursor.execute('''
                INSERT INTO afk_users (user_id, user_name, reason, hours, until_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, user_name, reason, hours, until_time.isoformat()))
            
            conn.commit()
            self.log_action(user_id, "AFK_GO", f"Reason: {reason}, Hours: {hours}")
            
            return True, f"✅ Вы ушли в AFK до {until_time.strftime('%d.%m.%Y %H:%M')} МСК"
    
    def remove_afk_user(self, user_id: str) -> tuple:
        """Удалить пользователя из AFK"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM afk_users WHERE user_id = ?', (user_id,))
            removed = cursor.rowcount > 0
            conn.commit()
            
            if removed:
                self.log_action(user_id, "AFK_BACK", "User returned from AFK")
                return True, "✅ Добро пожаловать обратно!"
            return False, "❌ Вы не были в AFK"
    
    def get_all_afk_users(self):
        """Получить всех AFK пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, reason, until_time
                FROM afk_users
                ORDER BY until_time
            ''')
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def get_afk_user(self, user_id: str):
        """Получить AFK пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, reason, until_time
                FROM afk_users WHERE user_id = ?
            ''', (user_id,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            return dict(zip(columns, row)) if row else None
    
    def check_expired_afk_users(self):
        """Проверить и вернуть просроченных AFK пользователей"""
        from datetime import datetime
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name FROM afk_users
                WHERE until_time < ?
            ''', (now.isoformat(),))
            
            expired = cursor.fetchall()
            
            # Удаляем просроченных
            cursor.execute('DELETE FROM afk_users WHERE until_time < ?', (now.isoformat(),))
            conn.commit()
            
            return expired

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ TIR =====
    
    def get_tier_setting(self, key: str) -> str:
        """Получить настройку TIR"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM tier_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_tier_setting(self, key: str, value: str, updated_by: str = None):
        """Установить настройку TIR"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tier_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_TIER_SETTING", f"{key}={value}")
    
    def set_tier_requirements(self, tier: str, requirements: str, updated_by: str = None):
        """Сохранить требования для тира"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tier_requirements (tier, requirements)
                VALUES (?, ?)
            ''', (tier, requirements))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_TIER_REQUIREMENTS", f"{tier}={requirements[:50]}...")
    
    def get_tier_requirements(self, tier: str) -> str:
        """Получить требования для тира"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT requirements FROM tier_requirements WHERE tier = ?', (tier,))
            result = cursor.fetchone()
            return result[0] if result else "Не установлены"
    
    def create_tier_application(self, user_id: str, user_name: str, nickname: str,
                                arena_link: str, screenshots: str, additional: str,
                                target_tier: str) -> tuple:
        """Создать заявку на повышение"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже активной заявки
            cursor.execute('''
                SELECT id FROM tier_applications 
                WHERE user_id = ? AND status = 'pending'
            ''', (user_id,))
            
            if cursor.fetchone():
                return None, "❌ У вас уже есть активная заявка"
            
            cursor.execute('''
                INSERT INTO tier_applications 
                (user_id, user_name, nickname, arena_link, screenshots, additional, target_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, user_name, nickname, arena_link, screenshots, additional, target_tier))
            
            conn.commit()
            return cursor.lastrowid, None
    
    def get_pending_tier_applications(self, target_tier: str = None):
        """Получить ожидающие заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if target_tier:
                cursor.execute('''
                    SELECT id, user_id, user_name, nickname, arena_link, screenshots,
                           additional, target_tier, created_at
                    FROM tier_applications 
                    WHERE status = 'pending' AND target_tier = ?
                    ORDER BY created_at
                ''', (target_tier,))
            else:
                cursor.execute('''
                    SELECT id, user_id, user_name, nickname, arena_link, screenshots,
                           additional, target_tier, created_at
                    FROM tier_applications 
                    WHERE status = 'pending'
                    ORDER BY created_at
                ''')
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def get_tier_application(self, app_id: int):
        """Получить заявку по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tier_applications WHERE id = ?', (app_id,))
            
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            return dict(zip(columns, row)) if row else None
    
    def approve_tier_application(self, app_id: int, reviewer_id: str, target_tier: str) -> bool:
        """Одобрить заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tier_applications 
                SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, app_id))
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                self.log_action(reviewer_id, "TIER_APPROVED", f"App {app_id}, Tier {target_tier}")
            
            return success
    
    def reject_tier_application(self, app_id: int, reviewer_id: str, reason: str) -> bool:
        """Отклонить заявку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tier_applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reject_reason = ?
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, reason, app_id))
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                self.log_action(reviewer_id, "TIER_REJECTED", f"App {app_id}, Reason: {reason[:50]}")
            
            return success

    def load_tier_settings(self):
        """Загрузить все настройки системы TIER в CONFIG"""
        from core.config import CONFIG
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM tier_settings')
            settings = dict(cursor.fetchall())
        
        for key, value in settings.items():
            if value and value.lower() != 'null':
                CONFIG[key] = value

    def save_tier_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения с заявкой TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tier_application_messages (application_id, channel_id, message_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (application_id, channel_id, message_id, user_id))
            conn.commit()
            self.log_action(user_id, "SAVE_TIER_APP_MESSAGE", f"App {application_id}, Msg {message_id}")

    def get_all_tier_application_messages(self):
        """Получить все сохранённые сообщения с заявками TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tam.application_id, tam.channel_id, tam.message_id, tam.user_id,
                    ta.status, ta.user_id as applicant_id, ta.nickname, ta.target_tier
                FROM tier_application_messages tam
                JOIN tier_applications ta ON tam.application_id = ta.id
                WHERE ta.status = 'pending'
            ''')
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]

    def delete_tier_application_message(self, application_id: int):
        """Удалить запись о сообщении TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tier_application_messages WHERE application_id = ?', (application_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def reset_stuck_tier_applications(self):
        """Сбросить все зависшие заявки TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Находим заявки без записей в application_messages
            cursor.execute('''
                SELECT ta.id FROM tier_applications ta
                LEFT JOIN tier_application_messages tam ON ta.id = tam.application_id
                WHERE ta.status = 'pending' AND tam.id IS NULL
            ''')
            stuck_apps = cursor.fetchall()
            
            if not stuck_apps:
                return 0
            
            # Удаляем зависшие заявки
            for app in stuck_apps:
                cursor.execute('DELETE FROM tier_applications WHERE id = ?', (app[0],))
            
            conn.commit()
            return len(stuck_apps)

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ СТАТИСТИКИ =====

    def load_stats_settings(self):
        """Загрузить все настройки системы статистики в CONFIG"""
        from core.config import CONFIG
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM stats_settings')
            settings = dict(cursor.fetchall())
        
        for key, value in settings.items():
            if value and value.lower() != 'null':
                CONFIG[key] = value
    
    def get_stats_setting(self, key: str) -> str:
        """Получить настройку статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM stats_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_stats_setting(self, key: str, value: str, updated_by: str = None):
        """Установить настройку статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO stats_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_STATS_SETTING", f"{key}={value}")
    
    def save_daily_stats(self, stats_data: dict):
        """Сохранить дневную статистику"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats 
                (date, new_members, left_members, new_applications, accepted_applications, max_voice_online, capt_registrations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats_data['date'],
                stats_data.get('new_members', 0),
                stats_data.get('left_members', 0),
                stats_data.get('new_applications', 0),
                stats_data.get('accepted_applications', 0),
                stats_data.get('max_voice_online', 0),
                stats_data.get('capt_registrations', 0)
            ))
            conn.commit()
    
    def get_stats_for_date(self, date_str: str):
        """Получить статистику за конкретную дату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (date_str,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_today_stats(self):
        """Получить статистику за сегодня"""
        from datetime import datetime
        import pytz
        msk_tz = pytz.timezone('Europe/Moscow')
        today = datetime.now(msk_tz).date().isoformat()
        return self.get_stats_for_date(today)

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ОТПУСКОВ =====
    
    def get_vacation_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM vacation_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_vacation_setting(self, key: str, value: str, updated_by: str = None):
        """Установить настройку отпусков"""
        # Если value — это список, преобразуем в JSON строку
        if isinstance(value, list):
            import json
            value = json.dumps(value)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO vacation_settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_VACATION_SETTING", f"{key}={value}")
    
    def create_vacation_application(self, user_id: str, user_name: str, days: int, reason: str, roles: list, guild_id: str) -> tuple:
        from datetime import datetime, timedelta
        import pytz
        msk_tz = pytz.timezone('Europe/Moscow')
        until_date = (datetime.now(msk_tz) + timedelta(days=days)).date().isoformat()
        
        roles_str = ','.join(roles) if roles else ''
        print(f"💾 Сохраняем роли в БД для сервера {guild_id}: {roles_str}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO vacation_applications (user_id, user_name, days, reason, saved_roles, guild_id, until_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, user_name, days, reason, roles_str, guild_id, until_date))
                conn.commit()
                return cursor.lastrowid, None
            except Exception as e:
                print(f"❌ Ошибка БД: {e}")
                return None, f"Ошибка БД: {e}"
    
    def get_pending_vacation_applications(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM vacation_applications WHERE status = "pending" ORDER BY created_at')
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def get_vacation_application(self, app_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM vacation_applications WHERE id = ?', (app_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
    
    def approve_vacation_application(self, app_id: int, reviewer_id: str) -> bool:
        from datetime import datetime
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, reason, until_date, saved_roles, guild_id FROM vacation_applications WHERE id = ? AND status = "pending"', (app_id,))
            app = cursor.fetchone()
            if not app:
                print(f"❌ Заявка {app_id} не найдена или уже обработана")
                return False
            
            user_id, user_name, reason, until_date, saved_roles, guild_id = app
            print(f"💾 Переносим в vacation_active: user={user_id}, guild={guild_id}, roles={saved_roles}")
            
            cursor.execute('''
                INSERT OR REPLACE INTO vacation_active (user_id, user_name, reason, until_date, saved_roles, guild_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, user_name, reason, until_date, saved_roles, guild_id))
            
            cursor.execute('''
                UPDATE vacation_applications 
                SET status = "approved", reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (reviewer_id, app_id))
            conn.commit()
            print(f"✅ Заявка {app_id} одобрена")
            return True
    
    def reject_vacation_application(self, app_id: int, reviewer_id: str, reason: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE vacation_applications 
                SET status = "rejected", reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = ?
                WHERE id = ?
            ''', (reviewer_id, reason, app_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_vacation(self, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM vacation_active WHERE user_id = ?', (user_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
    
    def get_all_vacations(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, reason, until_date, saved_roles, guild_id FROM vacation_active ORDER BY until_date')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def return_from_vacation(self, user_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def check_expired_vacations(self):
        from datetime import datetime
        import pytz
        msk_tz = pytz.timezone('Europe/Moscow')
        today = datetime.now(msk_tz).date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name FROM vacation_active WHERE until_date < ?', (today,))
            expired = cursor.fetchall()
            
            for user_id, user_name in expired:
                cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            
            conn.commit()
            return expired
    
    def save_vacation_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO vacation_application_messages (application_id, channel_id, message_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (application_id, channel_id, message_id, user_id))
            conn.commit()
    
    def get_all_vacation_application_messages(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT vm.application_id, vm.channel_id, vm.message_id, vm.user_id,
                       va.status, va.user_id as applicant_id, va.user_name
                FROM vacation_application_messages vm
                JOIN vacation_applications va ON vm.application_id = va.id
                WHERE va.status = 'pending'
            ''')
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def delete_vacation_application_message(self, application_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_application_messages WHERE application_id = ?', (application_id,))
            conn.commit()
            return cursor.rowcount > 0

    def load_vacation_settings(self):
        """Загрузить все настройки системы отпусков в CONFIG"""
        from core.config import CONFIG
        import json
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM vacation_settings')
            settings = dict(cursor.fetchall())
        
        for key, value in settings.items():
            if value and value.lower() != 'null':
                # Пробуем распарсить JSON для списков
                if key == 'vacation_approve_roles':
                    try:
                        CONFIG[key] = json.loads(value)
                    except:
                        CONFIG[key] = value.split(',') if value else []
                else:
                    CONFIG[key] = value

    def add_reward_role(self, role_id: str, added_by: str):
        """Добавить роль для автоматической выдачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO application_reward_roles (role_id, added_by) VALUES (?, ?)', 
                        (role_id, added_by))
            conn.commit()

    def remove_reward_role(self, role_id: str):
        """Удалить роль из списка"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM application_reward_roles WHERE role_id = ?', (role_id,))
            conn.commit()

    def get_reward_roles(self):
        """Получить все роли для выдачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role_id FROM application_reward_roles')
            return [row[0] for row in cursor.fetchall()]

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ОТПУСКОВ (ДОПОЛНИТЕЛЬНЫЕ) =====
    
    def get_expired_vacations(self):
        """Получить все просроченные отпуска (где дата окончания <= сегодня)"""
        from datetime import datetime
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, saved_roles, guild_id, reason, until_date FROM vacation_active')
            all_vacations = cursor.fetchall()
        
        today = datetime.now().date()
        expired = []
        
        for row in all_vacations:
            user_id, user_name, saved_roles, guild_id, reason, until_date = row
            try:
                until = datetime.strptime(until_date, '%Y-%m-%d').date()
                if until <= today:
                    expired.append(row)
            except Exception as e:
                print(f"❌ Ошибка парсинга даты {until_date}: {e}")
        
        return expired
    
    def delete_expired_vacations(self):
        """Удалить все просроченные отпуска из БД"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE until_date < date("now")')
            conn.commit()
            return cursor.rowcount
    
    def get_all_vacation_active(self):
        """Получить ВСЕХ активных в отпуске (для проверки при запуске)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, saved_roles, guild_id, reason, until_date FROM vacation_active')
            return cursor.fetchall()
    
    def delete_vacation_user(self, user_id: str):
        """Удалить пользователя из отпуска"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_role_ids_from_vacation(self, user_id: str):
        """Получить сохранённые роли пользователя в отпуске"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT saved_roles FROM vacation_active WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                return result[0].split(',')
            return []

    def remove_user_from_vacation(self, user_id: str) -> bool:
        """Удалить пользователя из отпуска (при выходе с сервера)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ИГР =====

    def init_games_tables(self):
        """Создать таблицы для игр с повторными попытками"""
        import time
        
        for attempt in range(5):  # 5 попыток
            try:
                with sqlite3.connect(self.db_path, timeout=15) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS active_games (
                            game_id TEXT PRIMARY KEY,
                            game_type TEXT NOT NULL,
                            channel_id TEXT NOT NULL,
                            player1_id TEXT NOT NULL,
                            player2_id TEXT NOT NULL,
                            game_data TEXT NOT NULL,
                            current_turn TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS game_stats (
                            user_id TEXT PRIMARY KEY,
                            user_name TEXT NOT NULL,
                            wins INTEGER DEFAULT 0,
                            losses INTEGER DEFAULT 0,
                            games_played INTEGER DEFAULT 0
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS game_settings (
                            game_type TEXT PRIMARY KEY,
                            enabled INTEGER DEFAULT 1
                        )
                    ''')
                    
                    conn.commit()
                    print("✅ Таблицы игр успешно созданы")
                    return True
                    
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < 4:
                    print(f"⚠️ БД заблокирована, повторная попытка через 1 секунду... ({attempt + 1}/5)")
                    time.sleep(1)
                else:
                    print(f"❌ Ошибка создания таблиц игр: {e}")
                    raise
        
        return False

    def get_active_game(self, game_id: str):
        """Получить активную игру по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM active_games WHERE game_id = ?', (game_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'game_id': row[0],
                    'game_type': row[1],
                    'channel_id': row[2],
                    'player1_id': row[3],
                    'player2_id': row[4],
                    'game_data': row[5],
                    'current_turn': row[6],
                    'created_at': row[7]
                }
            return None

    def get_all_active_games(self):
        """Получить все активные игры"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM active_games')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'game_id': row[0],
                    'game_type': row[1],
                    'channel_id': row[2],
                    'player1_id': row[3],
                    'player2_id': row[4],
                    'game_data': row[5],
                    'current_turn': row[6],
                    'created_at': row[7]
                })
            return result

    def save_active_game(self, game_id: str, game_type: str, channel_id: str, 
                        player1_id: str, player2_id: str, game_data: str, current_turn: str):
        """Сохранить активную игру"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO active_games 
                (game_id, game_type, channel_id, player1_id, player2_id, game_data, current_turn)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (game_id, game_type, channel_id, player1_id, player2_id, game_data, current_turn))
            conn.commit()

    def delete_active_game(self, game_id: str):
        """Удалить активную игру"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM active_games WHERE game_id = ?', (game_id,))
            conn.commit()

    def get_game_stats(self, user_id: str):
        """Получить статистику игрока"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT wins, losses, games_played FROM game_stats WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return {'wins': row[0], 'losses': row[1], 'games_played': row[2]}
            return {'wins': 0, 'losses': 0, 'games_played': 0}

    def update_game_stats(self, user_id: str, user_name: str, won: bool):
        """Обновить статистику игрока"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if won:
                cursor.execute('''
                    INSERT INTO game_stats (user_id, user_name, wins, losses, games_played)
                    VALUES (?, ?, 1, 0, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        wins = wins + 1,
                        games_played = games_played + 1,
                        user_name = excluded.user_name
                ''', (user_id, user_name))
            else:
                cursor.execute('''
                    INSERT INTO game_stats (user_id, user_name, wins, losses, games_played)
                    VALUES (?, ?, 0, 1, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        losses = losses + 1,
                        games_played = games_played + 1,
                        user_name = excluded.user_name
                ''', (user_id, user_name))
            conn.commit()

    def get_top_players(self, limit: int = 3):
        """Получить топ игроков по победам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_name, wins, losses, games_played 
                FROM game_stats 
                ORDER BY wins DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_game_enabled(self, game_type: str) -> bool:
        """Проверить, включена ли игра"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT enabled FROM game_settings WHERE game_type = ?', (game_type,))
            row = cursor.fetchone()
            if row:
                return row[0] == 1
            return True

    def set_game_enabled(self, game_type: str, enabled: bool):
        """Включить/выключить игру"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO game_settings (game_type, enabled)
                VALUES (?, ?)
            ''', (game_type, 1 if enabled else 0))
            conn.commit()

    def create_games_tables_if_not_exist(self):
        """Создать таблицы игр вне транзакции init_db"""
        import time
        
        for attempt in range(5):
            try:
                with sqlite3.connect(self.db_path, timeout=15) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS active_games (
                            game_id TEXT PRIMARY KEY,
                            game_type TEXT NOT NULL,
                            channel_id TEXT NOT NULL,
                            player1_id TEXT NOT NULL,
                            player2_id TEXT NOT NULL,
                            game_data TEXT NOT NULL,
                            current_turn TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS game_stats (
                            user_id TEXT PRIMARY KEY,
                            user_name TEXT NOT NULL,
                            wins INTEGER DEFAULT 0,
                            losses INTEGER DEFAULT 0,
                            games_played INTEGER DEFAULT 0
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS game_settings (
                            game_type TEXT PRIMARY KEY,
                            enabled INTEGER DEFAULT 1
                        )
                    ''')
                    
                    conn.commit()
                    print("✅ Таблицы игр созданы")
                    return True
                    
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < 4:
                    print(f"⚠️ БД заблокирована, попытка {attempt + 1}/5...")
                    time.sleep(1)
                else:
                    print(f"❌ Ошибка: {e}")
                    return False
        return False

        # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ДНЕЙ РОЖДЕНИЯ =====

    def set_birthday(self, user_id: str, user_name: str, birthday_date: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO birthdays (user_id, user_name, birthday_date)
                VALUES (?, ?, ?)
            ''', (user_id, user_name, birthday_date))
            conn.commit()
            return cursor.rowcount > 0

    def get_birthday(self, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, birthday_date FROM birthdays WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return {'user_id': row[0], 'user_name': row[1], 'birthday_date': row[2]}
            return None

    def get_all_birthdays(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, birthday_date FROM birthdays ORDER BY birthday_date')
            rows = cursor.fetchall()
            return [{'user_id': row[0], 'user_name': row[1], 'birthday_date': row[2]} for row in rows]

    def get_birthdays_by_month(self, month: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, birthday_date 
                FROM birthdays 
                WHERE substr(birthday_date, 4, 2) = ?
                ORDER BY substr(birthday_date, 1, 2)
            ''', (month,))
            rows = cursor.fetchall()
            return [{'user_id': row[0], 'user_name': row[1], 'birthday_date': row[2]} for row in rows]

    def get_today_birthdays(self):
        from datetime import datetime
        today = datetime.now().strftime("%d.%m")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, birthday_date FROM birthdays WHERE birthday_date = ?', (today,))
            rows = cursor.fetchall()
            return [{'user_id': row[0], 'user_name': row[1], 'birthday_date': row[2]} for row in rows]

    def remove_birthday(self, user_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM birthdays WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_birthdays(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM birthdays')
            conn.commit()
            return cursor.rowcount

    def get_birthday_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM birthdays')
            return cursor.fetchone()[0]

        # ===== МЕТОДЫ ДЛЯ MCL СИСТЕМЫ =====

    def mcl_add_registration(self, user_id: str, user_name: str, list_type: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO mcl_registrations (user_id, user_name, list_type, is_active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, user_name, list_type))
            conn.commit()
            return cursor.rowcount > 0

    def mcl_remove_registration(self, user_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM mcl_registrations WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mcl_get_registrations(self, list_type: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if list_type:
                cursor.execute('''
                    SELECT id, user_id, user_name FROM mcl_registrations 
                    WHERE is_active = 1 AND list_type = ? ORDER BY registered_at
                ''', (list_type,))
            else:
                cursor.execute('''
                    SELECT id, user_id, user_name, list_type FROM mcl_registrations 
                    WHERE is_active = 1 ORDER BY list_type, registered_at
                ''')
            return cursor.fetchall()

    def mcl_clear_all(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM mcl_registrations')
            conn.commit()

    def mcl_create_session(self, started_by: str, main_channel_id: str, reserve_channel_id: str, 
                           event_name: str, event_time: str, additional_info: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mcl_sessions (is_active, started_by, started_at, main_channel_id, reserve_channel_id, event_name, event_time, additional_info)
                VALUES (1, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            ''', (started_by, main_channel_id, reserve_channel_id, event_name, event_time, additional_info))
            conn.commit()
            return cursor.lastrowid

    def mcl_end_session(self, session_id: int, ended_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mcl_sessions SET is_active = 0, ended_by = ?, ended_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (ended_by, session_id))
            conn.commit()

    def mcl_get_active_session(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mcl_sessions WHERE is_active = 1 ORDER BY started_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def mcl_update_session_messages(self, session_id: int, main_message_id: str, reserve_message_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mcl_sessions SET main_message_id = ?, reserve_message_id = ?
                WHERE id = ?
            ''', (main_message_id, reserve_message_id, session_id))
            conn.commit()

    def mcl_move_to_main(self, reg_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mcl_registrations SET list_type = 'main', registered_at = CURRENT_TIMESTAMP
                WHERE id = ? AND list_type = 'reserve'
            ''', (reg_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mcl_move_to_reserve(self, reg_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mcl_registrations SET list_type = 'reserve', registered_at = CURRENT_TIMESTAMP
                WHERE id = ? AND list_type = 'main'
            ''', (reg_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mcl_move_all_to_main(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mcl_registrations SET list_type = 'main', registered_at = CURRENT_TIMESTAMP
                WHERE list_type = 'reserve'
            ''')
            conn.commit()
            return cursor.rowcount

db = Database()
db.create_games_tables_if_not_exist()