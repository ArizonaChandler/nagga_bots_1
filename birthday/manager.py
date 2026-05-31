"""Менеджер для работы с днями рождения (обёртка над database.py)"""
from core.database import db


class BirthdayManager:
    """Менеджер дней рождения"""

    def set_birthday(self, user_id: str, user_name: str, birthday_date: str) -> tuple:
        try:
            day, month = birthday_date.split('.')
            day = int(day)
            month = int(month)
            if day < 1 or day > 31 or month < 1 or month > 12:
                return False, "❌ Неверная дата. День: 1-31, месяц: 1-12"
        except:
            return False, "❌ Неверный формат. Используйте ДД.ММ (например 15.05)"

        birthday_date = f"{day:02d}.{month:02d}"
        
        if db.set_birthday(user_id, user_name, birthday_date):
            return True, f"✅ День рождения сохранён: {birthday_date}"
        return False, "❌ Ошибка сохранения"

    def remove_birthday(self, user_id: str) -> tuple:
        if db.remove_birthday(user_id):
            return True, "✅ День рождения удалён"
        return False, "❌ День рождения не найден"

    def get_birthday(self, user_id: str):
        return db.get_birthday(user_id)

    def get_today_birthdays(self):
        return db.get_today_birthdays()

    def get_birthdays_by_month(self, month: str):
        return db.get_birthdays_by_month(month)

    def get_all_birthdays(self):
        return db.get_all_birthdays()

    def clear_all(self) -> tuple:
        count = db.clear_all_birthdays()
        return True, f"✅ Удалено {count} записей"

    def get_stats(self) -> dict:
        return {
            'total': db.get_birthday_count(),
            'today': len(db.get_today_birthdays())
        }


birthday_manager = BirthdayManager()