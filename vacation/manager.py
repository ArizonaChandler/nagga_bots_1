"""Менеджер для работы с системой отпусков"""
from core.database import db
from core.config import CONFIG


class VacationManager:
    """Менеджер отпусков"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'vacation_public_channel': CONFIG.get('vacation_public_channel'),
            'vacation_applications_channel': CONFIG.get('vacation_applications_channel'),
            'vacation_log_channel': CONFIG.get('vacation_log_channel'),
            'vacation_settings_channel': CONFIG.get('vacation_settings_channel'),
            'vacation_approve_roles': CONFIG.get('vacation_approve_roles'),
            'vacation_role': CONFIG.get('vacation_role'),
            'vacation_max_days': CONFIG.get('vacation_max_days', 30),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_vacation_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def create_application(self, user_id: str, user_name: str, days: int, reason: str, roles: list) -> tuple:
        """Создать заявку на отпуск"""
        return db.create_vacation_application(user_id, user_name, days, reason, roles)
    
    def get_pending_applications(self):
        """Получить ожидающие заявки"""
        return db.get_pending_vacation_applications()
    
    def get_application(self, app_id: int):
        """Получить заявку по ID"""
        return db.get_vacation_application(app_id)
    
    def approve_application(self, app_id: int, reviewer_id: str):
        """Одобрить заявку"""
        return db.approve_vacation_application(app_id, reviewer_id)
    
    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        return db.reject_vacation_application(app_id, reviewer_id, reason)
    
    def get_user_vacation(self, user_id: str):
        """Получить активный отпуск пользователя"""
        return db.get_user_vacation(user_id)
    
    def get_all_vacations(self):
        """Получить всех в отпуске"""
        return db.get_all_vacations()
    
    def return_from_vacation(self, user_id: str, bot) -> tuple:
        """Вернуть пользователя из отпуска"""
        vacation = db.get_user_vacation(user_id)
        if not vacation:
            return False, "❌ Вы не в отпуске"
        
        # Восстанавливаем роли
        guild = None
        for g in bot.guilds:
            member = g.get_member(int(user_id))
            if member:
                guild = g
                break
        
        if guild:
            member = guild.get_member(int(user_id))
            roles_to_restore = vacation.get('saved_roles', [])
            if roles_to_restore:
                roles = [guild.get_role(int(r)) for r in roles_to_restore if guild.get_role(int(r))]
                if roles:
                    await member.add_roles(*roles)
            
            vacation_role_id = CONFIG.get('vacation_role')
            if vacation_role_id:
                vacation_role = guild.get_role(int(vacation_role_id))
                if vacation_role and vacation_role in member.roles:
                    await member.remove_roles(vacation_role)
        
        # Удаляем из БД
        db.return_from_vacation(user_id)
        return True, "✅ Вы вернулись из отпуска!"
    
    def check_expired_vacations(self):
        """Проверить просроченные отпуска"""
        return db.check_expired_vacations()
    
    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения заявки"""
        return db.save_vacation_application_message(application_id, channel_id, message_id, user_id)
    
    def get_all_application_messages(self):
        """Получить все сообщения заявок"""
        return db.get_all_vacation_application_messages()
    
    def delete_application_message(self, application_id: int):
        """Удалить запись о сообщении"""
        return db.delete_vacation_application_message(application_id)

vacation_manager = VacationManager()