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
        
        print(f"🔍 Данные отпуска: {vacation}")
        
        # Отправляем ЛС пользователю (предварительное)
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="🔄 ВОЗВРАТ ИЗ ОТПУСКА",
                    description="Идёт восстановление ваших ролей...",
                    color=0xffa500
                )
                await user.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка отправки ЛС: {e}")
        
        # Восстанавливаем роли
        guild = None
        for g in bot.guilds:
            member = g.get_member(int(user_id))
            if member:
                guild = g
                break
        
        if not guild:
            return False, "❌ Сервер не найден"
        
        member = guild.get_member(int(user_id))
        if not member:
            return False, "❌ Пользователь не найден на сервере"
        
        # Восстанавливаем сохранённые роли
        saved_roles_str = vacation.get('saved_roles', '')
        restored_roles = []
        failed_roles = []
        skipped_roles = []  # роли, которые выше бота
        
        if saved_roles_str:
            role_ids = [rid.strip() for rid in saved_roles_str.split(',') if rid.strip()]
            print(f"🎭 ID ролей для восстановления: {role_ids}")
            
            for rid in role_ids:
                role = guild.get_role(int(rid))
                if not role:
                    failed_roles.append(f"ID:{rid} (не найдена)")
                    print(f"❌ Роль с ID {rid} не найдена")
                    continue
                
                # Проверяем, может ли бот управлять этой ролью
                if role.position >= guild.me.top_role.position:
                    skipped_roles.append(role.name)
                    print(f"⚠️ Роль {role.name} выше бота, пропускаем")
                    continue
                
                try:
                    await member.add_roles(role)
                    restored_roles.append(role.name)
                    print(f"✅ Восстановлена роль: {role.name}")
                    await asyncio.sleep(0.5)  # небольшая задержка
                except discord.Forbidden:
                    failed_roles.append(role.name)
                    print(f"❌ Нет прав для роли: {role.name}")
                except Exception as e:
                    failed_roles.append(role.name)
                    print(f"❌ Ошибка восстановления {role.name}: {e}")
        
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
        
        # Удаляем из БД (в любом случае, чтобы отпуск закрылся)
        db.return_from_vacation(user_id)
        
        # Формируем итоговое сообщение
        result_msg = "✅ Вы вернулись из отпуска!\n\n"
        
        if restored_roles:
            result_msg += f"✅ Восстановлены роли: {', '.join(restored_roles)}\n"
        else:
            result_msg += f"⚠️ Не удалось восстановить ни одной роли\n"
        
        if skipped_roles:
            result_msg += f"⚠️ Пропущены (выше бота): {', '.join(skipped_roles)}\n"
        
        if failed_roles:
            result_msg += f"❌ Ошибки: {', '.join(failed_roles)}\n"
        
        # Отправляем результат пользователю в ЛС
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                color = 0x00ff00 if restored_roles else 0xffa500
                embed = discord.Embed(
                    title="✅ ВОЗВРАТ ИЗ ОТПУСКА" if restored_roles else "⚠️ ВОЗВРАТ ИЗ ОТПУСКА (С ОШИБКАМИ)",
                    description=result_msg,
                    color=color
                )
                if skipped_roles:
                    embed.add_field(name="💡 Решение", value="Попросите администратора поднять роль бота выше этих ролей", inline=False)
                await user.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка отправки финального ЛС: {e}")
        
        # Логируем в канал логов
        log_channel_id = CONFIG.get('vacation_log_channel')
        if log_channel_id:
            log_channel = bot.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                    description=f"Пользователь <@{user_id}> вернулся из отпуска",
                    color=0x00ff00 if restored_roles else 0xffa500,
                    timestamp=datetime.now()
                )
                embed.add_field(name="📝 Результат", value=result_msg, inline=False)
                await log_channel.send(embed=embed)
        
        return True, result_msg
    
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