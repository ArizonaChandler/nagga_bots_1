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

            # Таблица для хранения состояния модулей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS module_settings (
                    module_key TEXT PRIMARY KEY,
                    enabled TEXT DEFAULT '0'
                )
            ''')

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

            # Миграция: добавляем колонки для event_name, event_time, additional_info
            try:
                cursor.execute('ALTER TABLE capt_sessions ADD COLUMN event_name TEXT')
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute('ALTER TABLE capt_sessions ADD COLUMN event_time TEXT')
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute('ALTER TABLE capt_sessions ADD COLUMN additional_info TEXT')
            except sqlite3.OperationalError:
                pass

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ЗАЯВОК =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    reject_reason TEXT,
                    answers TEXT
                )
            ''')

            # ===== МИГРАЦИЯ: УДАЛЕНИЕ СТАРЫХ КОЛОНОК ИЗ applications =====
            try:
                # Проверяем, есть ли старые колонки
                cursor.execute("PRAGMA table_info(applications)")
                columns = [col[1] for col in cursor.fetchall()]
                
                old_columns = ['nickname', 'static', 'previous_families', 'prime_time', 'hours_per_day']
                existing_old = [col for col in old_columns if col in columns]
                
                if existing_old:
                    print(f"🔧 Миграция: удаляю старые колонки {existing_old} из таблицы applications...")
                    
                    # Создаём новую таблицу без старых колонок
                    cursor.execute('''
                        CREATE TABLE applications_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT NOT NULL,
                            user_name TEXT NOT NULL,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            reviewed_by TEXT,
                            reviewed_at TIMESTAMP,
                            reject_reason TEXT,
                            answers TEXT
                        )
                    ''')
                    
                    # Копируем данные
                    cursor.execute('''
                        INSERT INTO applications_new (id, user_id, user_name, status, created_at, reviewed_by, reviewed_at, reject_reason, answers)
                        SELECT id, user_id, user_name, status, created_at, reviewed_by, reviewed_at, reject_reason, answers
                        FROM applications
                    ''')
                    
                    # Удаляем старую таблицу
                    cursor.execute('DROP TABLE applications')
                    
                    # Переименовываем новую
                    cursor.execute('ALTER TABLE applications_new RENAME TO applications')
                    
                    conn.commit()
                    print("✅ Таблица applications успешно обновлена (старые колонки удалены)")
            except Exception as e:
                print(f"⚠️ Ошибка миграции: {e}")

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
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                        ('applications_create_profiles', 'true'))

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

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ TIER =====
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
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                        ('tier_delete_profile', 'false'))
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                        ('tier_create_profile', 'false'))

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

            # ===== Почасовая статистика =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    messages INTEGER DEFAULT 0,
                    voice_users INTEGER DEFAULT 0,
                    UNIQUE(date, hour)
                );
            ''')

            # ===== Статистика пользователей =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    messages INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    UNIQUE(user_id, date)
                );
            ''')

            # ===== Бекапы сервера =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    backup_data TEXT NOT NULL,
                    backup_size INTEGER DEFAULT 0,
                    created_by TEXT
                );
            ''')

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

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ДНЕЙ РОЖДЕНИЯ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    birthday_date TEXT NOT NULL,
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

            # ===== ТАБЛИЦЫ ДЛЯ СИСТЕМЫ ИГР =====
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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_balance (
                    user_id TEXT PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TIMESTAMP
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS economy_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    reason TEXT,
                    action TEXT CHECK(action IN ('earn', 'spend')),
                    operator TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shop_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    emoji TEXT DEFAULT '🛒',
                    limited_quantity INTEGER DEFAULT 0,
                    sold_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES shop_items(id)
                );
            ''')

            conn.commit()

        # ===== АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ СТАНДАРТНЫХ ПОЛЕЙ ЗАЯВКИ =====
        self.init_application_fields()

    def init_application_fields(self):
        """Автоматическое создание стандартных полей заявки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM application_fields')
                count = cursor.fetchone()[0]
                
                if count == 0:
                    print("📝 Добавляем стандартные поля для заявок...")
                    fields = [
                        ('nickname', '🎮 Игровой ник', 'Ваш ник в игре', 1, 1),
                        ('static', '🎯 Статик на сервере', 'Например: #15542', 1, 2),
                        ('previous_families', '🏠 Где и в каких семьях играли ранее', 'Названия семей, если были', 0, 3),
                        ('prime_time', '⏰ Прайм-тайм игры', 'Например: 19:00-23:00 МСК', 1, 4),
                        ('hours_per_day', '📊 Количество часов в игре в день', 'Например: 4-6 часов', 1, 5),
                    ]
                    
                    for field in fields:
                        cursor.execute('''
                            INSERT INTO application_fields (field_name, field_description, placeholder, required, field_order, is_active)
                            VALUES (?, ?, ?, ?, ?, 1)
                        ''', field)
                    
                    conn.commit()
                    print(f"✅ Добавлено {len(fields)} стандартных полей")
        except Exception as e:
            print(f"⚠️ Ошибка добавления полей: {e}")

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
    
    def add_event(self, name: str, weekday: int, event_time: str, created_by: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO events (name, weekday, event_time, created_by)
                VALUES (?, ?, ?, ?)
            ''', (name, weekday, event_time, created_by))
            conn.commit()
            return cursor.lastrowid
    
    def update_event(self, event_id: int, **kwargs) -> bool:
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
            return [dict(zip(columns, row)) for row in rows]
    
    def get_event(self, event_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
    
    def delete_event(self, event_id: int, soft: bool = False) -> bool:
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
    
    def take_event(self, event_id: int, user_id: str, user_name: str, group_code: str, meeting_place: str, event_date: str) -> int:
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
            return [dict(zip(columns, row)) for row in rows]
    
    def get_top_organizers(self, limit: int = 10, days: int = 30):
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
    
    def generate_schedule(self, days_ahead: int = 14):
        from datetime import datetime, timedelta
        import pytz
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        today = now.date()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            events = self.get_events(enabled_only=True)
            for event in events:
                for day_offset in range(days_ahead):
                    check_date = today + timedelta(days=day_offset)
                    if check_date.weekday() == event['weekday']:
                        event_time = datetime.strptime(event['event_time'], "%H:%M").time()
                        event_datetime = msk_tz.localize(datetime.combine(check_date, event_time))
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
            return [dict(zip(columns, row)) for row in rows]
    
    def mark_reminder_sent(self, event_id: int, event_date: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE event_schedule 
                SET reminder_sent = 1 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (event_id, event_date))
            conn.commit()
    
    def log_event_action(self, event_id: int, action: str, user_id: str = None, details: str = None):
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auto_ad WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def update_last_sent(self, ad_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE auto_ad SET last_sent = CURRENT_TIMESTAMP WHERE id = ?', (ad_id,))
            conn.commit()

    def log_ad_sent(self, success: bool, error: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auto_ad_logs (success, error)
                VALUES (?, ?)
            ''', (1 if success else 0, error))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ЗАЯВОК =====
    def get_application_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM application_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set_application_setting(self, key: str, value: str, updated_by: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO application_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            if updated_by:
                self.log_action(updated_by, f"SET_APP_SETTING", f"{key}={value}")

    def get_pending_applications(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, user_name, created_at, answers
                FROM applications 
                WHERE status = 'pending'
                ORDER BY created_at
            ''')
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                app = dict(zip(columns, row))
                # Извлекаем nickname из answers для отображения
                try:
                    import json
                    answers = json.loads(app.get('answers', '{}'))
                    app['nickname'] = answers.get('nickname', app['user_name'])
                except:
                    app['nickname'] = app['user_name']
                result.append(app)
            return result

    def get_application(self, app_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    def accept_application(self, app_id: int, reviewer_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            if not result:
                return False
            current_status = result[0]
            if current_status not in ['pending', 'interviewing']:
                return False
            cursor.execute('''
                UPDATE applications 
                SET status = 'accepted', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status IN ('pending', 'interviewing')
            ''', (reviewer_id, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            if not result:
                return False
            current_status = result[0]
            if current_status == 'accepted':
                return False
            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reject_reason = ?
                WHERE id = ?
            ''', (reviewer_id, reason, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def set_interviewing(self, app_id: int, reviewer_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM applications WHERE id = ?', (app_id,))
            result = cursor.fetchone()
            if not result or result[0] != 'pending':
                return False
            cursor.execute('''
                UPDATE applications 
                SET status = 'interviewing', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            ''', (reviewer_id, app_id))
            conn.commit()
            return cursor.rowcount > 0

    def load_application_settings(self):
        from core.config import CONFIG
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM application_settings')
            settings = dict(cursor.fetchall())
        for key, value in settings.items():
            if value and value.lower() != 'null':
                CONFIG[key] = value

    def get_application_fields(self):
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

    def create_application_dynamic(self, user_id: str, user_name: str, answers_json: str) -> tuple:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM applications WHERE user_id = ? AND status IN ("pending", "interviewing")', (user_id,))
                if cursor.fetchone():
                    return None, "❌ У вас уже есть активная заявка"
                cursor.execute('''
                    INSERT INTO applications (user_id, user_name, answers, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (user_id, user_name, answers_json))
                conn.commit()
                return cursor.lastrowid, None
        except Exception as e:
            print(f"❌ Ошибка create_application_dynamic: {e}")
            return None, f"❌ Ошибка: {e}"

    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO application_messages (application_id, channel_id, message_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (application_id, channel_id, message_id, user_id))
            conn.commit()
            self.log_action(user_id, "SAVE_APP_MESSAGE", f"App {application_id}, Msg {message_id}")
    
    def get_all_application_messages(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT am.application_id, am.channel_id, am.message_id, am.user_id,
                       a.status, a.user_id as applicant_id
                FROM application_messages am
                JOIN applications a ON am.application_id = a.id
                WHERE a.status IN ('pending', 'interviewing')
            ''')
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def delete_application_message(self, application_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM application_messages WHERE application_id = ?', (application_id,))
            conn.commit()
            return cursor.rowcount > 0

    def reset_user_applications(self, user_id: str, reset_by: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM applications WHERE user_id = ?', (user_id,))
            count = cursor.fetchone()[0]
            if count == 0:
                return False, f"❌ У пользователя {user_id} нет заявок"
            cursor.execute('''
                DELETE FROM application_messages 
                WHERE application_id IN (SELECT id FROM applications WHERE user_id = ?)
            ''', (user_id,))
            cursor.execute('''
                DELETE FROM applications 
                WHERE user_id = ?
            ''', (user_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0 and reset_by:
                self.log_action(reset_by, "RESET_USER_APPLICATIONS", f"User {user_id}, deleted {deleted_count} applications")
            return True, f"✅ Удалено {deleted_count} заявок пользователя <@{user_id}>"

    def add_reward_role(self, role_id: str, added_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO application_reward_roles (role_id, added_by) VALUES (?, ?)', 
                        (role_id, added_by))
            conn.commit()

    def remove_reward_role(self, role_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM application_reward_roles WHERE role_id = ?', (role_id,))
            conn.commit()

    def get_reward_roles(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role_id FROM application_reward_roles')
            return [row[0] for row in cursor.fetchall()]

    def update_application_field(self, field_id: int, field_name: str, field_description: str, placeholder: str, required: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE application_fields 
                SET field_name = ?, field_description = ?, placeholder = ?, required = ?
                WHERE id = ?
            ''', (field_name, field_description, placeholder, 1 if required else 0, field_id))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ ЗАКРЫТИЯ ЗАЯВОК ПРИ ВЫХОДЕ =====

    def get_active_application_id(self, user_id: str):
        """Получить ID активной заявки пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM applications WHERE user_id = ? AND status IN ("pending", "interviewing")', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def close_application_on_leave(self, application_id: int):
        """Закрыть заявку при выходе пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reject_reason = ?
                WHERE id = ?
            ''', ('system', 'Пользователь покинул сервер', application_id))
            conn.commit()

    def remove_birthday_on_leave(self, user_id: str):
        """Удалить день рождения при выходе пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM birthdays WHERE user_id = ?', (user_id,))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ AFK =====
    
    def get_afk_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM afk_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_afk_setting(self, key: str, value: str, updated_by: str = None):
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
        from datetime import datetime, timedelta
        import pytz
        msk_tz = pytz.timezone('Europe/Moscow')
        until_time = datetime.now(msk_tz) + timedelta(hours=hours)
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
            cursor.execute('DELETE FROM afk_users WHERE until_time < ?', (now.isoformat(),))
            conn.commit()
            return expired

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ TIER =====
    
    def get_tier_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM tier_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_tier_setting(self, key: str, value: str, updated_by: str = None):
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT requirements FROM tier_requirements WHERE tier = ?', (tier,))
            result = cursor.fetchone()
            return result[0] if result else "Не установлены"
    
    def create_tier_application(self, user_id: str, user_name: str, nickname: str,
                                arena_link: str, screenshots: str, additional: str,
                                target_tier: str) -> tuple:
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tier_applications WHERE id = ?', (app_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
    
    def approve_tier_application(self, app_id: int, reviewer_id: str, target_tier: str) -> bool:
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
        from core.config import CONFIG
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM tier_settings')
            settings = dict(cursor.fetchall())
        for key, value in settings.items():
            if value and value.lower() != 'null':
                CONFIG[key] = value

    def save_tier_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
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
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT application_id, channel_id, message_id, user_id 
                    FROM tier_application_messages 
                    WHERE application_id IN (SELECT id FROM tier_applications WHERE status = 'pending')
                """)
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        'application_id': row[0],
                        'channel_id': row[1],
                        'message_id': row[2],
                        'user_id': row[3]
                    })
                return result
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []

    def delete_tier_application_message(self, application_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tier_application_messages WHERE application_id = ?', (application_id,))
            conn.commit()
            return cursor.rowcount > 0

    def reset_stuck_tier_applications(self):
        """Сбросить все зависшие заявки TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ta.id FROM tier_applications ta
                LEFT JOIN tier_application_messages tam ON ta.id = tam.application_id
                WHERE ta.status = 'pending' AND tam.id IS NULL
            ''')
            stuck_apps = cursor.fetchall()
            if not stuck_apps:
                return 0
            for app in stuck_apps:
                cursor.execute('DELETE FROM tier_applications WHERE id = ?', (app[0],))
            conn.commit()
            return len(stuck_apps)

    # ===== МЕТОДЫ ДЛЯ TIER (для bot.py) =====
    
    def get_pending_tier_applications_raw(self):
        """Получить все ожидающие заявки TIER (без обёрток)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, user_name, nickname, arena_link, screenshots, additional 
                FROM tier_applications WHERE status = 'pending'
            ''')
            return cursor.fetchall()
    
    def save_tier_application_message_raw(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить сообщение заявки TIER"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tier_application_messages (application_id, channel_id, message_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (application_id, channel_id, message_id, user_id))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ CAPT =====

    def capt_get_active_session(self):
        """Получить активную сессию CAPT"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM capt_sessions WHERE is_active = 1 ORDER BY started_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def capt_update_session_messages(self, session_id: int, main_message_id: str, reserve_message_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE capt_sessions 
                SET main_message_id = ?, reserve_message_id = ?
                WHERE id = ?
            ''', (main_message_id, reserve_message_id, session_id))
            conn.commit()

    def capt_get_registrations(self, list_type: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if list_type:
                cursor.execute('SELECT id, user_id, user_name FROM capt_registrations WHERE is_active = 1 AND list_type = ? ORDER BY registered_at', (list_type,))
            else:
                cursor.execute('SELECT id, user_id, user_name, list_type FROM capt_registrations WHERE is_active = 1 ORDER BY list_type, registered_at')
            return cursor.fetchall()

    def capt_add_registration(self, user_id: str, user_name: str, list_type: str) -> bool:
        """Добавить участника в список CAPT"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Сначала удаляем старую запись, если есть
            cursor.execute('DELETE FROM capt_registrations WHERE user_id = ?', (user_id,))
            # Затем добавляем новую
            cursor.execute('''
                INSERT INTO capt_registrations (user_id, user_name, list_type, is_active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, user_name, list_type))
            conn.commit()
            return cursor.rowcount > 0

    def capt_remove_registration(self, user_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM capt_registrations WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def capt_clear_all(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM capt_registrations')
            conn.commit()

    def capt_move_to_main(self, reg_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE capt_registrations SET list_type = "main", registered_at = CURRENT_TIMESTAMP WHERE id = ? AND list_type = "reserve"', (reg_id,))
            conn.commit()
            return cursor.rowcount > 0

    def capt_move_to_reserve(self, reg_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE capt_registrations SET list_type = "reserve", registered_at = CURRENT_TIMESTAMP WHERE id = ? AND list_type = "main"', (reg_id,))
            conn.commit()
            return cursor.rowcount > 0

    def capt_move_all_to_main(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE capt_registrations SET list_type = "main", registered_at = CURRENT_TIMESTAMP WHERE list_type = "reserve"')
            conn.commit()
            return cursor.rowcount

    def capt_get_active_session(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM capt_sessions WHERE is_active = 1 ORDER BY started_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def capt_create_session(self, started_by: str, main_channel_id: str, reserve_channel_id: str, event_name: str, event_time: str, additional_info: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO capt_sessions (is_active, started_by, started_at, main_channel_id, reserve_channel_id, event_name, event_time, additional_info)
                VALUES (1, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            ''', (started_by, main_channel_id, reserve_channel_id, event_name, event_time, additional_info))
            conn.commit()
            return cursor.lastrowid

    def capt_end_session(self, session_id: int, ended_by: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE capt_sessions SET is_active = 0, ended_by = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?', (ended_by, session_id))
            conn.commit()

    def capt_update_session_messages(self, session_id: int, main_message_id: str, reserve_message_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE capt_sessions SET main_message_id = ?, reserve_message_id = ? WHERE id = ?', (main_message_id, reserve_message_id, session_id))
            conn.commit()

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ОТПУСКОВ =====
    
    def get_vacation_setting(self, key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM vacation_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_vacation_setting(self, key: str, value: str, updated_by: str = None):
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, user_name, reason, until_date, saved_roles, guild_id FROM vacation_applications WHERE id = ? AND status = "pending"', (app_id,))
            app = cursor.fetchone()
            if not app:
                return False
            user_id, user_name, reason, until_date, saved_roles, guild_id = app
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
        from core.config import CONFIG
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM vacation_settings')
            settings = dict(cursor.fetchall())
        for key, value in settings.items():
            if value and value.lower() != 'null':
                if key == 'vacation_approve_roles':
                    try:
                        CONFIG[key] = json.loads(value)
                    except:
                        CONFIG[key] = value.split(',') if value else []
                else:
                    CONFIG[key] = value

    def get_expired_vacations(self):
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
            except:
                pass
        return expired
    
    def delete_expired_vacations(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE until_date < date("now")')
            conn.commit()
            return cursor.rowcount
    
    def delete_vacation_user(self, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def remove_user_from_vacation(self, user_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ===== МЕТОДЫ ДЛЯ СИСТЕМЫ ИГР =====

    def get_active_game(self, game_id: str):
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO active_games 
                (game_id, game_type, channel_id, player1_id, player2_id, game_data, current_turn)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (game_id, game_type, channel_id, player1_id, player2_id, game_data, current_turn))
            conn.commit()

    def delete_active_game(self, game_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM active_games WHERE game_id = ?', (game_id,))
            conn.commit()

    def get_game_stats(self, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT wins, losses, games_played FROM game_stats WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return {'wins': row[0], 'losses': row[1], 'games_played': row[2]}
            return {'wins': 0, 'losses': 0, 'games_played': 0}

    def update_game_stats(self, user_id: str, user_name: str, won: bool):
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT enabled FROM game_settings WHERE game_type = ?', (game_type,))
            row = cursor.fetchone()
            if row:
                return row[0] == 1
            return True

    def set_game_enabled(self, game_type: str, enabled: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO game_settings (game_type, enabled)
                VALUES (?, ?)
            ''', (game_type, 1 if enabled else 0))
            conn.commit()

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
        """Добавить участника в список MCL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Сначала удаляем старую запись, если есть
            cursor.execute('DELETE FROM mcl_registrations WHERE user_id = ?', (user_id,))
            # Затем добавляем новую
            cursor.execute('''
                INSERT INTO mcl_registrations (user_id, user_name, list_type, is_active)
                VALUES (?, ?, ?, 1)
            ''', (user_id, user_name, list_type))
            conn.commit()
            return cursor.rowcount > 0

    def mcl_remove_registration(self, user_id: str) -> bool:
        """Удалить участника из списка MCL"""
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

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ МОДУЛЕЙ =====

    def get_module_setting(self, module_key: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT enabled FROM module_settings WHERE module_key = ?', (module_key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set_module_setting(self, module_key: str, enabled: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO module_settings (module_key, enabled)
                VALUES (?, ?)
            ''', (module_key, enabled))
            conn.commit()

    # ===== ЭКОНОМИКА =====

    def init_user_balance(self, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO user_balance (user_id) VALUES (?)', (user_id,))
            conn.commit()

    def get_user_balance(self, user_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM user_balance WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else None

    def add_user_balance(self, user_id: str, amount: int, reason: str, awarded_by: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_balance (user_id, balance, total_earned) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?, total_earned = total_earned + ?
            ''', (user_id, amount, amount, amount, amount))
            cursor.execute('INSERT INTO economy_transactions (user_id, amount, reason, action, operator) VALUES (?, ?, ?, "earn", ?)',
                        (user_id, amount, reason, awarded_by))
            conn.commit()
            cursor.execute('SELECT balance FROM user_balance WHERE user_id = ?', (user_id,))
            return cursor.fetchone()[0]

    def remove_user_balance(self, user_id: str, amount: int, reason: str, removed_by: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE user_balance SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ? AND balance >= ?',
                        (amount, amount, user_id, amount))
            if cursor.rowcount == 0:
                return None
            cursor.execute('INSERT INTO economy_transactions (user_id, amount, reason, action, operator) VALUES (?, ?, ?, "spend", ?)',
                        (user_id, amount, reason, removed_by))
            conn.commit()
            cursor.execute('SELECT balance FROM user_balance WHERE user_id = ?', (user_id,))
            return cursor.fetchone()[0]

    def get_user_total_earned(self, user_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT total_earned FROM user_balance WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else 0

    def get_user_total_spent(self, user_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT total_spent FROM user_balance WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else 0

    def get_top_balance_users(self, limit: int = 10) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, balance, total_earned FROM user_balance ORDER BY balance DESC LIMIT ?', (limit,))
            return cursor.fetchall()

    def get_recent_economy_transactions(self, limit: int = 20) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount, reason, action, timestamp FROM economy_transactions ORDER BY timestamp DESC LIMIT ?', (limit,))
            return [{'user_id': r[0], 'amount': r[1], 'reason': r[2], 'action': r[3], 'timestamp': r[4]} for r in cursor.fetchall()]

    def get_last_daily_claim(self, user_id: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT last_daily FROM user_balance WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else None

    def get_daily_streak(self, user_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT daily_streak FROM user_balance WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else 0

    def update_daily_claim(self, user_id: str, streak: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE user_balance SET last_daily = CURRENT_TIMESTAMP, daily_streak = ? WHERE user_id = ?', (streak, user_id))
            conn.commit()

    def get_daily_voice_earned(self, user_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM economy_transactions WHERE user_id = ? AND action="earn" AND reason LIKE "%голосовом%" AND date(timestamp) = date("now")', (user_id,))
            return cursor.fetchone()[0]

    # ===== МАГАЗИН =====

    def add_shop_item(self, name: str, desc: str, price: int, emoji: str, limit: int, created_by: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO shop_items (name, description, price, emoji, limited_quantity, created_by) VALUES (?, ?, ?, ?, ?, ?)',
                        (name, desc, price, emoji, limit, created_by))
            conn.commit()
            return cursor.lastrowid

    def get_shop_items(self, active_only: bool = True) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT id, name, description, price, emoji, limited_quantity, sold_count FROM shop_items WHERE is_active=1 ORDER BY price')
            else:
                cursor.execute('SELECT id, name, description, price, emoji, limited_quantity, sold_count FROM shop_items ORDER BY price')
            return [{'id': r[0], 'name': r[1], 'description': r[2], 'price': r[3], 'emoji': r[4], 'limited_quantity': r[5], 'sold_count': r[6]} for r in cursor.fetchall()]

    def get_shop_item(self, item_id: int) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, description, price, emoji, limited_quantity, sold_count, is_active FROM shop_items WHERE id = ?', (item_id,))
            r = cursor.fetchone()
            if r:
                return {'id': r[0], 'name': r[1], 'description': r[2], 'price': r[3], 'emoji': r[4], 'limited_quantity': r[5], 'sold_count': r[6], 'is_active': r[7]}
            return None

    def remove_shop_item(self, item_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE shop_items SET is_active = 0 WHERE id = ?', (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def purchase_item(self, user_id: str, item_id: int, price: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE shop_items SET sold_count = sold_count + 1 WHERE id = ?', (item_id,))
            cursor.execute('INSERT INTO user_purchases (user_id, item_id, price) VALUES (?, ?, ?)', (user_id, item_id, price))
            conn.commit()
            return True

    def get_user_purchases(self, user_id: str, limit: int = 10) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT up.id, up.item_id, up.price, up.purchased_at, si.name, si.emoji
                FROM user_purchases up JOIN shop_items si ON up.item_id = si.id
                WHERE up.user_id = ? ORDER BY up.purchased_at DESC LIMIT ?
            ''', (user_id, limit))
            return [{'id': r[0], 'item_id': r[1], 'price': r[2], 'purchased_at': r[3], 'item_name': r[4], 'item_emoji': r[5]} for r in cursor.fetchall()]

    def update_daily_voice_earned(self, user_id: str, amount: int):
        """Обновить ежедневный лимит голосовых баллов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Просто логируем, лимит проверяется через get_daily_voice_earned
            pass  # или можно хранить в отдельной таблице

    # ===== РАСШИРЕННАЯ СТАТИСТИКА =====

    def get_daily_new_members(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM audit_log WHERE action="MEMBER_JOIN" AND date(timestamp) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_left_members(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM audit_log WHERE action="MEMBER_LEAVE" AND date(timestamp) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_applications(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM applications WHERE date(created_at) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_accepted_applications(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM applications WHERE status="accepted" AND date(reviewed_at) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_capt_registrations(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM capt_registrations WHERE date(registered_at) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_mcl_registrations(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM mcl_registrations WHERE date(registered_at) = ?', (date,))
            return cursor.fetchone()[0]

    def get_daily_mp_takes(self, date: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM event_takes WHERE date(event_date) = ?', (date,))
            return cursor.fetchone()[0]

    def get_stats_for_last_days(self, days: int) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?', (days,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    # ===== ПОЧАСОВАЯ СТАТИСТИКА =====

    def update_hourly_stats(self, date: str, hour: int, messages: int, voice_users: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO hourly_stats (date, hour, messages, voice_users)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, hour) DO UPDATE SET
                    messages = excluded.messages,
                    voice_users = excluded.voice_users
            ''', (date, hour, messages, voice_users))
            conn.commit()

    def get_hourly_stats(self, date: str) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT hour, messages, voice_users FROM hourly_stats WHERE date = ? ORDER BY hour', (date,))
            return cursor.fetchall()

    # ===== СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ =====

    def update_user_activity(self, user_id: str, date: str, field: str, delta: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT INTO user_activity (user_id, date, {field}) VALUES (?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    {field} = {field} + ?
            ''', (user_id, date, delta, delta))
            conn.commit()

    def get_user_activity(self, user_id: str, days: int) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(messages) as messages, SUM(voice_minutes) as voice_minutes
                FROM user_activity
                WHERE user_id = ? AND date >= date("now", ?)
            ''', (user_id, f'-{days} days'))
            row = cursor.fetchone()
            return {'messages': row[0] or 0, 'voice_minutes': row[1] or 0}

    # ===== БЕКАПЫ =====

    def save_server_backup(self, backup_data: str, created_by: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO server_backups (backup_data, created_by, backup_size)
                VALUES (?, ?, ?)
            ''', (backup_data, created_by, len(backup_data)))
            conn.commit()
            return cursor.lastrowid

    def get_server_backups(self, limit: int = 10) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, backup_date, backup_size, created_by
                FROM server_backups ORDER BY backup_date DESC LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [{'id': r[0], 'backup_date': r[1], 'backup_size': r[2], 'created_by': r[3]} for r in rows]

    def get_server_backup(self, backup_id: int) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT backup_data, backup_date FROM server_backups WHERE id = ?', (backup_id,))
            row = cursor.fetchone()
            if row:
                return {'backup_data': row[0], 'backup_date': row[1]}
            return None

db = Database()