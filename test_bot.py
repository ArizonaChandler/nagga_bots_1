#!/usr/bin/env python3
"""
Автоматический тестировщик MAJESTIC BOT
Проверяет все системы бота без ручного вмешательства
Запуск: python test_bot.py
"""

import asyncio
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_test(text, status="info"):
    """Красивый вывод тестов"""
    if status == "ok":
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    elif status == "error":
        print(f"{Colors.RED}❌ {text}{Colors.END}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")
    elif status == "info":
        print(f"{Colors.BLUE}📋 {text}{Colors.END}")
    elif status == "title":
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    else:
        print(text)

class BotTester:
    def __init__(self):
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "tests": []
        }
        self.db_path = "bot_data.db"
        
    def run_all_tests(self):
        """Запуск всех тестов"""
        print_test("🚀 MAJESTIC BOT - АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ", "title")
        
        # 1. Проверка файловой структуры
        self.test_file_structure()
        
        # 2. Проверка базы данных
        self.test_database()
        
        # 3. Проверка конфигурации
        self.test_config()
        
        # 4. Проверка модулей
        self.test_modules()
        
        # 5. Проверка систем
        self.test_applications_system()
        self.test_tier_system()
        self.test_capt_system()
        self.test_events_system()
        self.test_afk_system()
        self.test_vacation_system()
        self.test_birthday_system()
        self.test_games_system()
        
        # 6. Проверка целостности данных
        self.test_data_integrity()
        
        # Итоги
        self.print_summary()
        
    def test_file_structure(self):
        """Проверка наличия всех необходимых файлов"""
        print_test("📁 ПРОВЕРКА ФАЙЛОВОЙ СТРУКТУРЫ", "title")
        
        required_files = [
            "bot.py",
            "core/config.py",
            "core/database.py",
            "core/module_manager.py",
            "core/admin_views.py",
            "applications/__init__.py",
            "applications/views.py",
            "applications/modals.py",
            "tier/__init__.py",
            "tier/views.py",
            "tier/manager.py",
            "capt_registration/__init__.py",
            "capt_registration/views.py",
            "capt_registration/manager.py",
            "events/__init__.py",
            "afk/__init__.py",
            "vacation/__init__.py",
            "birthday/__init__.py",
            "games/__init__.py"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print_test(f"Файл найден: {file_path}", "ok")
                self.results["passed"] += 1
                self.results["tests"].append({"name": f"Файл {file_path}", "status": "passed"})
            else:
                print_test(f"Файл отсутствует: {file_path}", "error")
                self.results["failed"] += 1
                self.results["tests"].append({"name": f"Файл {file_path}", "status": "failed"})
    
    def test_database(self):
        """Проверка базы данных и всех таблиц"""
        print_test("🗄️ ПРОВЕРКА БАЗЫ ДАННЫХ", "title")
        
        required_tables = [
            "users", "admins", "settings", "audit_log", "command_stats",
            "applications", "application_messages", "application_fields",
            "tier_applications", "tier_settings", "tier_requirements", "tier_application_messages",
            "capt_registrations", "capt_sessions",
            "events", "event_takes", "event_schedule",
            "afk_users", "afk_settings",
            "vacation_applications", "vacation_active", "vacation_settings",
            "birthdays",
            "active_games", "game_stats"
        ]
        
        if not os.path.exists(self.db_path):
            print_test("Файл базы данных не найден!", "error")
            self.results["failed"] += 1
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    # Проверяем количество записей
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print_test(f"Таблица {table}: {count} записей", "ok")
                    self.results["passed"] += 1
                    self.results["tests"].append({"name": f"Таблица {table}", "status": "passed", "count": count})
                else:
                    print_test(f"Таблица отсутствует: {table}", "error")
                    self.results["failed"] += 1
                    self.results["tests"].append({"name": f"Таблица {table}", "status": "failed"})
            
            conn.close()
        except Exception as e:
            print_test(f"Ошибка подключения к БД: {e}", "error")
            self.results["failed"] += 1
    
    def test_config(self):
        """Проверка конфигурации"""
        print_test("⚙️ ПРОВЕРКА КОНФИГУРАЦИИ", "title")
        
        try:
            from core.config import CONFIG
            
            required_keys = [
                "token", "server_id", "family_name",
                "applications_channel", "applications_log_channel",
                "tier_submit_channel", "tier_applications_channel",
                "capt_reg_main_channel", "capt_reg_reserve_channel",
                "events_channel", "afk_channel", "vacation_channel"
            ]
            
            for key in required_keys:
                if key in CONFIG:
                    value = CONFIG[key]
                    if value and value != "null":
                        print_test(f"Настройка {key}: {value[:50] if len(str(value)) > 50 else value}", "ok")
                        self.results["passed"] += 1
                    else:
                        print_test(f"Настройка {key}: не настроена", "warning")
                        self.results["warnings"] += 1
                else:
                    print_test(f"Настройка {key}: отсутствует", "warning")
                    self.results["warnings"] += 1
                    
        except Exception as e:
            print_test(f"Ошибка загрузки конфига: {e}", "error")
            self.results["failed"] += 1
    
    def test_modules(self):
        """Проверка загрузки модулей"""
        print_test("📦 ПРОВЕРКА МОДУЛЕЙ", "title")
        
        modules = [
            ("applications", "Система заявок"),
            ("tier", "Tier система"),
            ("capt_registration", "CAPT регистрация"),
            ("events", "Мероприятия"),
            ("afk", "AFK система"),
            ("vacation", "Отпуска"),
            ("birthday", "Дни рождения"),
            ("games", "Игры")
        ]
        
        for module_name, module_desc in modules:
            try:
                __import__(module_name)
                print_test(f"Модуль {module_desc} загружен", "ok")
                self.results["passed"] += 1
            except ImportError as e:
                print_test(f"Модуль {module_desc} не загружен: {e}", "error")
                self.results["failed"] += 1
    
    def test_applications_system(self):
        """Проверка системы заявок"""
        print_test("📝 ПРОВЕРКА СИСТЕМЫ ЗАЯВОК", "title")
        
        try:
            from core.database import db
            
            # Проверяем поля заявок
            fields = db.get_application_fields()
            print_test(f"Найдено {len(fields)} полей заявки", "ok")
            
            # Проверяем ожидающие заявки
            pending = db.get_pending_applications()
            print_test(f"Ожидающих заявок: {len(pending)}", "ok" if len(pending) < 50 else "warning")
            
            # Проверяем настройки
            channel = db.get_application_setting('applications_channel')
            print_test(f"Канал заявок: {channel if channel else 'не настроен'}", "warning" if not channel else "ok")
            
            self.results["passed"] += 3
            
        except Exception as e:
            print_test(f"Ошибка в системе заявок: {e}", "error")
            self.results["failed"] += 1
    
    def test_tier_system(self):
        """Проверка Tier системы"""
        print_test("🌟 ПРОВЕРКА TIER СИСТЕМЫ", "title")
        
        try:
            from core.database import db
            from tier.manager import tier_manager
            
            # Проверяем требования к тирам
            for tier in ["tier1", "tier2", "tier3"]:
                req = tier_manager.get_tier_requirements(tier)
                print_test(f"Требования {tier}: {req[:50] if req else 'не установлены'}", "ok" if req else "warning")
            
            # Проверяем ожидающие заявки
            pending = tier_manager.get_pending_applications()
            print_test(f"Ожидающих заявок на Tier: {len(pending)}", "ok")
            
            # Проверяем настройки
            settings = tier_manager.get_settings()
            for key in ["tier_submit_channel", "tier_applications_channel"]:
                value = settings.get(key)
                print_test(f"Настройка {key}: {value if value else 'не настроена'}", "warning" if not value else "ok")
            
            self.results["passed"] += 4
            
        except Exception as e:
            print_test(f"Ошибка в Tier системе: {e}", "error")
            self.results["failed"] += 1
    
    def test_capt_system(self):
        """Проверка CAPT системы"""
        print_test("🎯 ПРОВЕРКА CAPT СИСТЕМЫ", "title")
        
        try:
            from core.database import db
            
            # Проверяем регистрации
            main_list = db.capt_get_registrations('main')
            reserve_list = db.capt_get_registrations('reserve')
            print_test(f"Основной список: {len(main_list)} участников", "ok")
            print_test(f"Резервный список: {len(reserve_list)} участников", "ok")
            
            # Проверяем активную сессию
            session = db.capt_get_active_session()
            if session:
                print_test(f"Активная сессия: {session.get('event_name', 'Без названия')}", "ok")
            else:
                print_test("Нет активной сессии", "info")
            
            # Проверяем статистику
            total = db.get_total_capt_registrations() if hasattr(db, 'get_total_capt_registrations') else 0
            print_test(f"Всего регистраций за всё время: {total}", "ok")
            
            self.results["passed"] += 3
            
        except Exception as e:
            print_test(f"Ошибка в CAPT системе: {e}", "error")
            self.results["failed"] += 1
    
    def test_events_system(self):
        """Проверка системы мероприятий"""
        print_test("📅 ПРОВЕРКА СИСТЕМЫ МЕРОПРИЯТИЙ", "title")
        
        try:
            from core.database import db
            
            # Проверяем мероприятия
            events = db.get_events(enabled_only=False)
            print_test(f"Всего мероприятий: {len(events)}", "ok")
            
            active_events = db.get_events(enabled_only=True)
            print_test(f"Активных мероприятий: {len(active_events)}", "ok")
            
            # Проверяем статистику
            stats = db.get_event_stats_summary()
            print_test(f"Всего взятий: {stats.get('total_takes', 0)}", "ok")
            print_test(f"За последние 30 дней: {stats.get('takes_30d', 0)}", "ok")
            
            # Проверяем топ организаторов
            top = db.get_top_organizers(limit=5)
            if top:
                print_test(f"Лучший организатор: {top[0][1]} ({top[0][2]} мероприятий)", "ok")
            
            self.results["passed"] += 4
            
        except Exception as e:
            print_test(f"Ошибка в системе мероприятий: {e}", "error")
            self.results["failed"] += 1
    
    def test_afk_system(self):
        """Проверка AFK системы"""
        print_test("🛌 ПРОВЕРКА AFK СИСТЕМЫ", "title")
        
        try:
            from core.database import db
            
            # Проверяем AFK пользователей
            afk_users = db.get_all_afk_users()
            print_test(f"В AFK: {len(afk_users)} пользователей", "ok")
            
            # Проверяем просроченных
            expired = db.check_expired_afk_users()
            print_test(f"Просроченных AFK: {len(expired)}", "ok")
            
            # Проверяем настройки
            max_hours = db.get_afk_setting('afk_max_hours')
            print_test(f"Максимальное время AFK: {max_hours if max_hours else '24'} часов", "ok")
            
            self.results["passed"] += 3
            
        except Exception as e:
            print_test(f"Ошибка в AFK системе: {e}", "error")
            self.results["failed"] += 1
    
    def test_vacation_system(self):
        """Проверка системы отпусков"""
        print_test("🏖️ ПРОВЕРКА СИСТЕМЫ ОТПУСКОВ", "title")
        
        try:
            from core.database import db
            
            # Проверяем заявки
            pending = db.get_pending_vacation_applications()
            print_test(f"Ожидающих заявок на отпуск: {len(pending)}", "ok")
            
            # Проверяем активные отпуска
            active = db.get_all_vacations()
            print_test(f"Активных отпусков: {len(active)}", "ok")
            
            # Проверяем просроченные
            expired = db.get_expired_vacations()
            print_test(f"Просроченных отпусков: {len(expired)}", "ok")
            
            # Проверяем настройки
            max_days = db.get_vacation_setting('vacation_max_days')
            print_test(f"Максимальная длительность: {max_days if max_days else '30'} дней", "ok")
            
            self.results["passed"] += 4
            
        except Exception as e:
            print_test(f"Ошибка в системе отпусков: {e}", "error")
            self.results["failed"] += 1
    
    def test_birthday_system(self):
        """Проверка системы дней рождений"""
        print_test("🎂 ПРОВЕРКА СИСТЕМЫ ДНЕЙ РОЖДЕНИЙ", "title")
        
        try:
            from core.database import db
            
            # Проверяем количество
            count = db.get_birthday_count()
            print_test(f"Зарегистрированных дней рождений: {count}", "ok")
            
            # Проверяем сегодняшние
            today = db.get_today_birthdays()
            print_test(f"Именинников сегодня: {len(today)}", "ok")
            
            # Проверяем по месяцам
            for month in ["01", "06", "12"]:
                birthdays = db.get_birthdays_by_month(month)
                if birthdays:
                    print_test(f"ДР в месяце {month}: {len(birthdays)}", "ok")
            
            self.results["passed"] += 3
            
        except Exception as e:
            print_test(f"Ошибка в системе дней рождений: {e}", "error")
            self.results["failed"] += 1
    
    def test_games_system(self):
        """Проверка системы игр"""
        print_test("🎮 ПРОВЕРКА СИСТЕМЫ ИГР", "title")
        
        try:
            from core.database import db
            
            # Проверяем активные игры
            active = db.get_all_active_games()
            print_test(f"Активных игр: {len(active)}", "ok")
            
            # Проверяем статистику
            top = db.get_top_players(limit=3)
            if top:
                print_test(f"Топ игроков: {len(top)}", "ok")
            
            # Проверяем настройки
            enabled = db.get_game_enabled('tic_tac_toe')
            print_test(f"Игры включены: {'Да' if enabled else 'Нет'}", "ok")
            
            self.results["passed"] += 3
            
        except Exception as e:
            print_test(f"Ошибка в системе игр: {e}", "error")
            self.results["failed"] += 1
    
    def test_data_integrity(self):
        """Проверка целостности данных между таблицами"""
        print_test("🔗 ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ", "title")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем связи заявок
            cursor.execute("""
                SELECT COUNT(*) FROM application_messages am
                LEFT JOIN applications a ON am.application_id = a.id
                WHERE a.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                print_test(f"Сиротских записей в application_messages: {orphaned}", "warning")
                self.results["warnings"] += 1
            else:
                print_test("Все связи application_messages корректны", "ok")
                self.results["passed"] += 1
            
            # Проверяем связи Tier заявок
            cursor.execute("""
                SELECT COUNT(*) FROM tier_application_messages tam
                LEFT JOIN tier_applications ta ON tam.application_id = ta.id
                WHERE ta.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                print_test(f"Сиротских записей в tier_application_messages: {orphaned}", "warning")
                self.results["warnings"] += 1
            else:
                print_test("Все связи tier_application_messages корректны", "ok")
                self.results["passed"] += 1
            
            # Проверяем дубликаты пользователей
            cursor.execute("""
                SELECT user_id, COUNT(*) FROM users 
                GROUP BY user_id HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                print_test(f"Найдено дубликатов пользователей: {len(duplicates)}", "warning")
                self.results["warnings"] += 1
            else:
                print_test("Дубликатов пользователей не найдено", "ok")
                self.results["passed"] += 1
            
            conn.close()
            
        except Exception as e:
            print_test(f"Ошибка проверки целостности: {e}", "error")
            self.results["failed"] += 1
    
    def print_summary(self):
        """Вывод итогов тестирования"""
        print_test("\n📊 ИТОГИ ТЕСТИРОВАНИЯ", "title")
        
        total = self.results["passed"] + self.results["failed"] + self.results["warnings"]
        
        print(f"\n{Colors.BOLD}Результаты:{Colors.END}")
        print(f"  {Colors.GREEN}✅ Пройдено: {self.results['passed']}{Colors.END}")
        print(f"  {Colors.RED}❌ Провалено: {self.results['failed']}{Colors.END}")
        print(f"  {Colors.YELLOW}⚠️ Предупреждений: {self.results['warnings']}{Colors.END}")
        print(f"  {Colors.BLUE}📊 Всего проверок: {total}{Colors.END}")
        
        # Процент успеха
        if total > 0:
            success_rate = (self.results["passed"] / total) * 100
            print(f"\n{Colors.BOLD}Общая оценка:{Colors.END}")
            
            if success_rate >= 90:
                print(f"  {Colors.GREEN}Отлично! ({success_rate:.1f}%){Colors.END}")
            elif success_rate >= 70:
                print(f"  {Colors.YELLOW}Хорошо, есть над чем поработать ({success_rate:.1f}%){Colors.END}")
            else:
                print(f"  {Colors.RED}Требуется доработка ({success_rate:.1f}%){Colors.END}")
        
        # Рекомендации
        print(f"\n{Colors.BOLD}💡 Рекомендации:{Colors.END}")
        if self.results["failed"] > 0:
            print(f"  {Colors.RED}• Исправьте {self.results['failed']} критических ошибок{Colors.END}")
        if self.results["warnings"] > 0:
            print(f"  {Colors.YELLOW}• Обратите внимание на {self.results['warnings']} предупреждений{Colors.END}")
        if self.results["failed"] == 0 and self.results["warnings"] == 0:
            print(f"  {Colors.GREEN}• Все системы работают идеально!{Colors.END}")
        
        # Сохраняем результаты в файл
        self.save_results()
    
    def save_results(self):
        """Сохранение результатов в файл"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "system_info": {
                "python_version": sys.version,
                "os": os.name
            }
        }
        
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{Colors.BLUE}📄 Отчёт сохранён в test_report.json{Colors.END}")

def main():
    tester = BotTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()