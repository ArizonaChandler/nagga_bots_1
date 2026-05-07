"""Менеджер для работы с системой отпусков"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG


class VacationManager:
    """Менеджер отпусков"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        max_days = CONFIG.get('vacation_max_days', 30)
        if isinstance(max_days, str):
            try:
                max_days = int(max_days)
            except:
                max_days = 30
        
        approve_roles = CONFIG.get('vacation_approve_roles', [])
        if isinstance(approve_roles, str):
            try:
                import json
                approve_roles = json.loads(approve_roles)
            except:
                approve_roles = []
        
        return {
            'vacation_public_channel': CONFIG.get('vacation_public_channel'),
            'vacation_applications_channel': CONFIG.get('vacation_applications_channel'),
            'vacation_log_channel': CONFIG.get('vacation_log_channel'),
            'vacation_settings_channel': CONFIG.get('vacation_settings_channel'),
            'vacation_approve_roles': approve_roles,
            'vacation_role': CONFIG.get('vacation_role'),
            'vacation_max_days': max_days,
        }
    
    def save_setting(self, key: str, value, updated_by: str = None):
        """Сохранить настройку"""
        import json
        if isinstance(value, list):
            value = json.dumps(value)
        
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
    
    def approve_application(self, app_id: int, reviewer_id: str) -> bool:
        """Одобрить заявку"""
        return db.approve_vacation_application(app_id, reviewer_id)
    
    def reject_application(self, app_id: int, reviewer_id: str, reason: str) -> bool:
        """Отклонить заявку"""
        return db.reject_vacation_application(app_id, reviewer_id, reason)
    
    def get_user_vacation(self, user_id: str):
        """Получить активный отпуск пользователя"""
        return db.get_user_vacation(user_id)
    
    def get_all_vacations(self):
        """Получить всех в отпуске"""
        return db.get_all_vacations()
    
    async def return_from_vacation(self, user_id: str, bot) -> tuple:
        """Вернуть пользователя из отпуска"""
        vacation = db.get_user_vacation(user_id)
        if not vacation:
            return False, "❌ Вы не в отпуске"
        
        # Отправляем ЛС пользователю
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                    description="Вы вернулись из отпуска! Ваши роли восстановлены.",
                    color=0x00ff00
                )
                await user.send(embed=embed)
                print(f"✅ ЛС отправлено пользователю {user_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки ЛС: {e}")
        
        # Восстанавливаем роли
        guild = None
        for g in bot.guilds:
            member = g.get_member(int(user_id))
            if member:
                guild = g
                break
        
        if guild:
            member = guild.get_member(int(user_id))
            if not member:
                return False, "❌ Пользователь не найден на сервере"
            
            # Восстанавливаем сохранённые роли
            saved_roles_str = vacation.get('saved_roles', '')
            if saved_roles_str:
                role_ids = saved_roles_str.split(',') if isinstance(saved_roles_str, str) else saved_roles_str
                roles_to_restore = []
                failed_roles = []
                
                for rid in role_ids:
                    if rid:
                        role = guild.get_role(int(rid))
                        if role:
                            roles_to_restore.append(role)
                
                for role in roles_to_restore:
                    try:
                        await member.add_roles(role)
                        print(f"✅ Восстановлена роль: {role.name}")
                    except discord.Forbidden:
                        failed_roles.append(role.name)
                        print(f"❌ Нет прав для восстановления роли: {role.name}")
                    except Exception as e:
                        failed_roles.append(role.name)
                        print(f"❌ Ошибка восстановления роли {role.name}: {e}")
                
                if failed_roles:
                    print(f"⚠️ Не удалось восстановить роли: {', '.join(failed_roles)}")
            
            # Снимаем роль отпуска
            vacation_role_id = CONFIG.get('vacation_role')
            if vacation_role_id:
                vacation_role = guild.get_role(int(vacation_role_id))
                if vacation_role and vacation_role in member.roles:
                    try:
                        await member.remove_roles(vacation_role)
                        print(f"✅ Снята роль отпуска")
                    except Exception as e:
                        print(f"❌ Ошибка снятия роли отпуска: {e}")
        
        # Логируем в канал логов
        log_channel_id = CONFIG.get('vacation_log_channel')
        if log_channel_id:
            log_channel = bot.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                    description=f"Пользователь <@{user_id}> вернулся из отпуска",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="📝 Результат", value="Роли восстановлены" + (f" (не удалось: {', '.join(failed_roles)})" if failed_roles else ""), inline=False)
                await log_channel.send(embed=embed)
        
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