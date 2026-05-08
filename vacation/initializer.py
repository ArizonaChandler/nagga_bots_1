"""Инициализация каналов системы отпусков"""
import asyncio
import discord
import logging
from datetime import datetime, timedelta
import pytz
from vacation.manager import vacation_manager
from vacation.views import VacationPublicView, update_vacation_embed
from vacation.settings_view import VacationSettingsView
from core.database import db

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


class VacationInitializer:
    """Инициализатор каналов системы отпусков"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы отпусков"""
        logger.info("🔄 Инициализация системы отпусков...")
        
        # ⭐ ВРЕМЕННЫЙ ЛОГ ДЛЯ ДИАГНОСТИКИ
        logger.info("🔍 ВЫЗЫВАЮ _check_expired_on_startup()")
        try:
            await self._check_expired_on_startup()
            logger.info("✅ _check_expired_on_startup() выполнен успешно")
        except Exception as e:
            logger.error(f"❌ ОШИБКА в _check_expired_on_startup(): {e}")
            import traceback
            traceback.print_exc()
        
        settings = vacation_manager.get_settings()
        
        # ⭐⭐⭐ ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ ⭐⭐⭐
        await self._check_expired_on_startup()
        
        # 1. Публичный канал с кнопками
        await self._init_public_channel(settings)
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Запускаем фоновую проверку
        await self.start_expiry_checker()
        
        logger.info("✅ Инициализация системы отпусков завершена")
    
    async def _check_expired_on_startup(self):
        """Проверка просроченных отпусков при запуске бота"""
        logger.info("🔍 === ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ ===")
        
        try:
            # Получаем всех просроченных из БД
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование таблицы
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacation_active'")
                if not cursor.fetchone():
                    logger.warning("⚠️ Таблица vacation_active не существует")
                    return
                
                # Получаем просроченных
                cursor.execute('''
                    SELECT user_id, user_name, saved_roles, guild_id, reason, until_date
                    FROM vacation_active 
                    WHERE until_date < date('now')
                ''')
                expired = cursor.fetchall()
            
            if not expired:
                logger.info("✅ Нет просроченных отпусков")
                return
            
            logger.info(f"⚠️ Найдено {len(expired)} просроченных отпусков. Возвращаем пользователей...")
            
            restored_count = 0
            failed_count = 0
            
            for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
                try:
                    logger.info(f"🔄 Обработка: {user_name} (ID: {user_id}), отпуск до {until_date}")
                    
                    # Находим сервер
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        logger.error(f"❌ Сервер {guild_id} не найден для {user_name}")
                        failed_count += 1
                        continue
                    
                    # Получаем участника
                    member = guild.get_member(int(user_id))
                    if not member:
                        try:
                            member = await guild.fetch_member(int(user_id))
                        except discord.NotFound:
                            logger.error(f"❌ Пользователь {user_id} не найден на сервере {guild.name}")
                            failed_count += 1
                            continue
                        except Exception as e:
                            logger.error(f"❌ Ошибка получения участника {user_id}: {e}")
                            failed_count += 1
                            continue
                    
                    # Восстанавливаем роли
                    restored_roles = []
                    failed_roles = []
                    
                    if saved_roles:
                        role_ids = [rid.strip() for rid in saved_roles.split(',') if rid.strip()]
                        logger.info(f"🎭 Восстанавливаем роли для {user_name}: {role_ids}")
                        
                        for rid in role_ids:
                            try:
                                role = guild.get_role(int(rid))
                                if role:
                                    # Проверяем, что роль не выше бота
                                    if role.position >= guild.me.top_role.position:
                                        logger.warning(f"⚠️ Роль {role.name} выше бота, пропускаем")
                                        failed_roles.append(f"{role.name} (выше бота)")
                                        continue
                                    
                                    await member.add_roles(role)
                                    restored_roles.append(role.name)
                                    logger.info(f"   ✅ Роль {role.name} восстановлена")
                                else:
                                    failed_roles.append(f"ID:{rid} (не найдена)")
                                    logger.warning(f"   ❌ Роль с ID {rid} не найдена")
                            except discord.Forbidden:
                                failed_roles.append(f"ID:{rid} (нет прав)")
                                logger.warning(f"   ❌ Нет прав на роль {rid}")
                            except Exception as e:
                                failed_roles.append(f"ID:{rid} ({e})")
                                logger.error(f"   ❌ Ошибка: {e}")
                    
                    # Снимаем роль отпуска
                    vacation_role_id = vacation_manager.get_settings().get('vacation_role')
                    if vacation_role_id:
                        vacation_role = guild.get_role(int(vacation_role_id))
                        if vacation_role and vacation_role in member.roles:
                            await member.remove_roles(vacation_role)
                            logger.info(f"   ✅ Снята роль отпуска {vacation_role.name}")
                    
                    # Удаляем из БД (через database.py)
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
                        conn.commit()
                    logger.info(f"   ✅ Запись удалена из БД")
                    
                    # Отправляем ЛС пользователю
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                                description=f"**Ваш отпуск автоматически завершён.**\n\n"
                                            f"📅 Длился до: {until_date}\n"
                                            f"✅ Восстановлено ролей: {len(restored_roles)}\n"
                                            f"❌ Ошибок: {len(failed_roles)}",
                                color=0x00ff00 if restored_roles else 0xffa500
                            )
                            if restored_roles:
                                embed.add_field(name="✅ Восстановленные роли", value=", ".join(restored_roles), inline=False)
                            if failed_roles:
                                embed.add_field(name="⚠️ Не удалось восстановить", value=", ".join(failed_roles), inline=False)
                            await user.send(embed=embed)
                            logger.info(f"   ✅ ЛС отправлено {user_name}")
                    except Exception as e:
                        logger.error(f"   ❌ Ошибка отправки ЛС: {e}")
                    
                    restored_count += 1
                    
                    # Логируем в канал логов
                    log_channel_id = vacation_manager.get_settings().get('vacation_log_channel')
                    if log_channel_id:
                        log_channel = self.bot.get_channel(int(log_channel_id))
                        if log_channel:
                            embed = discord.Embed(
                                title="✅ АВТОМАТИЧЕСКИЙ ВОЗВРАТ ИЗ ОТПУСКА",
                                description=f"Пользователь **{user_name}** автоматически возвращён из отпуска",
                                color=0x00ff00,
                                timestamp=datetime.now(MSK_TZ)
                            )
                            embed.add_field(name="📅 Дата окончания", value=until_date, inline=True)
                            embed.add_field(name="✅ Восстановлено ролей", value=str(len(restored_roles)), inline=True)
                            await log_channel.send(embed=embed)
                    
                except Exception as e:
                    logger.error(f"❌ Критическая ошибка при возврате {user_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
            
            # Обновляем embed в публичном канале
            settings = vacation_manager.get_settings()
            public_channel_id = settings.get('vacation_public_channel')
            if public_channel_id:
                await update_vacation_embed(self.bot, public_channel_id)
                logger.info(f"✅ Embed обновлён в публичном канале")
            
            logger.info(f"✅ Завершено: возвращено {restored_count}, ошибок {failed_count}")
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в _check_expired_on_startup: {e}")
            import traceback
            traceback.print_exc()
    
    async def start_expiry_checker(self):
        """Запустить фоновую задачу для проверки просроченных отпусков (каждую минуту)"""
        self.bot.loop.create_task(self._check_expired_periodically())
        logger.info("✅ Запущен автоматический проверщик просроченных отпусков (каждую минуту)")
    
    async def _check_expired_periodically(self):
        """Фоновая задача: проверять каждые 60 секунд"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Проверяем просроченные отпуска через database.py
                expired = db.get_expired_vacations()
                
                if expired:
                    logger.info(f"⏰ Найдено просроченных отпусков: {len(expired)}")
                    
                    for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
                        try:
                            await self._return_user_from_vacation(user_id, user_name, saved_roles, guild_id, until_date)
                        except Exception as e:
                            logger.error(f"❌ Ошибка возврата {user_name}: {e}")
                    
                    # Удаляем просроченных из БД
                    deleted = db.delete_expired_vacations()
                    logger.info(f"✅ Удалено {deleted} просроченных отпусков из БД")
                    
                    # Обновляем embed
                    settings = vacation_manager.get_settings()
                    channel_id = settings.get('vacation_public_channel')
                    if channel_id:
                        await update_vacation_embed(self.bot, channel_id)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в проверке отпусков: {e}")
                await asyncio.sleep(60)
    
    async def _return_user_from_vacation(self, user_id: str, user_name: str, saved_roles: str, guild_id: str, until_date: str):
        """Вернуть пользователя из отпуска (вспомогательный метод)"""
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            logger.error(f"❌ Сервер {guild_id} не найден")
            return
        
        member = guild.get_member(int(user_id))
        if not member:
            try:
                member = await guild.fetch_member(int(user_id))
            except:
                logger.error(f"❌ Пользователь {user_id} не найден")
                return
        
        restored_roles = []
        
        if saved_roles:
            role_ids = [rid.strip() for rid in saved_roles.split(',') if rid.strip()]
            for rid in role_ids:
                try:
                    role = guild.get_role(int(rid))
                    if role and role.position < guild.me.top_role.position:
                        await member.add_roles(role)
                        restored_roles.append(role.name)
                except:
                    pass
        
        # Снимаем роль отпуска
        vacation_role_id = vacation_manager.get_settings().get('vacation_role')
        if vacation_role_id:
            vacation_role = guild.get_role(int(vacation_role_id))
            if vacation_role and vacation_role in member.roles:
                await member.remove_roles(vacation_role)
        
        # Отправляем ЛС
        try:
            user = await self.bot.fetch_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                    description=f"Ваш отпуск закончился.\n\n**Восстановлено ролей:** {len(restored_roles)}",
                    color=0x00ff00
                )
                await user.send(embed=embed)
        except:
            pass
        
        logger.info(f"✅ {user_name} возвращён из отпуска, восстановлено {len(restored_roles)} ролей")
    
    async def _init_public_channel(self, settings):
        """Инициализация публичного канала с кнопками"""
        channel_id = settings.get('vacation_public_channel')
        if not channel_id:
            logger.warning("⚠️ Публичный канал отпуска не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Публичный канал {channel_id} не найден")
            return
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.edit(view=VacationPublicView())
                message_exists = True
                logger.info(f"✅ Обновлена панель отпусков в #{channel.name}")
                break
        
        if not message_exists:
            embed = discord.Embed(
                title="🏖️ **СИСТЕМА ОТПУСКОВ**",
                description="✨ Никого нет в отпуске",
                color=0x00ff00
            )
            embed.set_footer(text="Нажмите кнопку, чтобы подать заявку")
            await channel.send(embed=embed, view=VacationPublicView())
            logger.info(f"✅ Создана панель отпусков в #{channel.name}")
        
        await update_vacation_embed(self.bot, channel_id)
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек отпусков"""
        from core.config import CONFIG
        channel_id = CONFIG.get('vacation_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек отпусков не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {channel_id} не найден")
            return
        
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ ОТПУСКОВ" in msg.embeds[0].title:
                    await msg.edit(view=VacationSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек отпусков в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ ОТПУСКОВ**",
                description="Настройка системы отпусков",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=VacationSettingsView())
            logger.info(f"✅ Создана панель настроек отпусков в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = VacationInitializer(bot)
    await initializer.initialize_all()