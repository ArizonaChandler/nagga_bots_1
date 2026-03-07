"""Менеджер для работы с системой заявок"""
from core.database import db
from core.config import CONFIG

class ApplicationManager:
    """Менеджер заявок (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
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
        """Сбросить все заявки пользователя (для возможности подать новую)"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем все заявки пользователя
            cursor.execute('''
                DELETE FROM applications 
                WHERE user_id = ?
            ''', (user_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0 and reset_by:
                db.log_action(reset_by, "RESET_USER_APPLICATIONS", f"User {user_id}, deleted {deleted_count} applications")
            
            return deleted_count > 0, f"✅ Удалено {deleted_count} заявок пользователя"

app_manager = ApplicationManager()