"""Менеджер для работы с системой заявок"""
from core.database import db
from core.config import CONFIG

class ApplicationManager:
    """Менеджер заявок (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'submit_channel': CONFIG.get('submit_channel'),
            'applications_channel': CONFIG.get('applications_channel'),
            'applications_log_channel': CONFIG.get('applications_log_channel'),
            'applications_recruit_role': CONFIG.get('applications_recruit_role'),
            'applications_member_role': CONFIG.get('applications_member_role'),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_application_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def create_application(self, user_id: str, user_name: str, nickname: str, 
                          static: str, previous_families: str, prime_time: str, 
                          hours_per_day: str) -> tuple:
        """Создать заявку"""
        return db.create_application(user_id, user_name, nickname, static, 
                                    previous_families, prime_time, hours_per_day)
    
    def get_pending_applications(self):
        """Получить ожидающие заявки"""
        return db.get_pending_applications()
    
    def get_application(self, app_id: int):
        """Получить заявку по ID"""
        return db.get_application(app_id)
    
    def accept_application(self, app_id: int, reviewer_id: str):
        """Принять заявку"""
        return db.accept_application(app_id, reviewer_id)
    
    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        return db.reject_application(app_id, reviewer_id, reason)
    
    def set_interviewing(self, app_id: int, reviewer_id: str):
        """Назначить обзвон"""
        return db.set_interviewing(app_id, reviewer_id)

    def reset_user_applications(self, user_id: str, reset_by: str = None):
        """Сбросить все заявки пользователя"""
        return db.reset_user_applications(user_id, reset_by)

    def check_member_in_guild(self, user_id: str, guild) -> bool:
        """Проверить, находится ли пользователь на сервере"""
        member = guild.get_member(int(user_id))
        return member is not None
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С СООБЩЕНИЯМИ =====
    
    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения с заявкой"""
        return db.save_application_message(application_id, channel_id, message_id, user_id)
    
    def get_all_application_messages(self):
        """Получить все сохранённые сообщения с заявками"""
        return db.get_all_application_messages()
    
    def delete_application_message(self, application_id: int):
        """Удалить запись о сообщении"""
        return db.delete_application_message(application_id)
    
    def get_application_by_message(self, message_id: str):
        """Получить заявку по ID сообщения"""
        return db.get_application_by_message(message_id)

    def delete_interview_channel(self, channel_id: int):
    """Удалить канал обзвона"""
    try:
        # Этот метод будет вызываться из views.py, но само удаление
        # происходит через discord, поэтому здесь просто заглушка
        # для совместимости, если понадобится логика в будущем
        return True
    except Exception as e:
        print(f"❌ Ошибка при удалении канала: {e}")
        return False

app_manager = ApplicationManager()