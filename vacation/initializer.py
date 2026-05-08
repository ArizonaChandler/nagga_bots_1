"""Инициализация каналов системы отпусков"""
import asyncio
import discord
import logging
from datetime import datetime
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
        
        # ⭐⭐⭐ ПРОВЕРКА ПРОСРОЧЕННЫХ ПРИ ЗАПУСКЕ ⭐⭐⭐
        try:
            logger.info("🔍 ВЫЗЫВАЮ _check_expired_on_startup()...")
            await self._check_expired_on_startup()
            logger.info("✅ _check_expired_on_startup() ВЫПОЛНЕН")
        except Exception as e:
            logger.error(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
        
        settings = vacation_manager.get_settings()
        
        # 1. Публичный канал с кнопками
        await self._init_public_channel(settings)
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Запускаем фоновую проверку
        await self.start_expiry_checker()
        
        logger.info("✅ Инициализация системы отпусков завершена")
    
    async def _check_expired_on_startup(self):
        """ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ"""
        logger.info("🔍 === ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ ===")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем таблицу
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacation_active'")
                if not cursor.fetchone():
                    logger.warning("⚠️ Таблица vacation_active не существует")
                    return
                
                # Получаем просроченных
                cursor.execute("SELECT user_id, user_name, saved_roles, guild_id, until_date FROM vacation_active WHERE until_date < date('now')")
                expired = cursor.fetchall()
                
                logger.info(f"📊 Найдено просроченных: {len(expired)}")
                
                for user_id, user_name, saved_roles, guild_id, until_date in expired:
                    try:
                        logger.info(f"🔄 Возвращаю {user_name} (ID: {user_id})")
                        
                        guild = self.bot.get_guild(int(guild_id))
                        if not guild:
                            logger.error(f"❌ Гильдия {guild_id} не найдена")
                            continue
                        
                        member = guild.get_member(int(user_id))
                        if not member:
                            try:
                                member = await guild.fetch_member(int(user_id))
                            except:
                                logger.error(f"❌ Не могу найти {user_id} на сервере")
                                continue
                        
                        # Восстанавливаем роли
                        if saved_roles:
                            for rid in saved_roles.split(','):
                                rid = rid.strip()
                                try:
                                    role = guild.get_role(int(rid))
                                    if role and role.position < guild.me.top_role.position:
                                        await member.add_roles(role)
                                        logger.info(f"   ✅ Добавлена роль {role.name}")
                                except Exception as e:
                                    logger.error(f"   ❌ Не могу добавить роль {rid}: {e}")
                        
                        # Снимаем роль отпуска
                        vacation_role_id = vacation_manager.get_settings().get('vacation_role')
                        if vacation_role_id:
                            try:
                                vacation_role = guild.get_role(int(vacation_role_id))
                                if vacation_role and vacation_role in member.roles:
                                    await member.remove_roles(vacation_role)
                                    logger.info(f"   ✅ Снята роль отпуска")
                            except Exception as e:
                                logger.error(f"   ❌ Ошибка снятия роли отпуска: {e}")
                        
                        # Отправляем ЛС
                        try:
                            user = await self.bot.fetch_user(int(user_id))
                            if user:
                                await user.send(f"✅ **Вы автоматически возвращены из отпуска!**\nВаши роли восстановлены.")
                                logger.info(f"   ✅ ЛС отправлено")
                        except Exception as e:
                            logger.error(f"   ❌ Ошибка отправки ЛС: {e}")
                        
                        # Удаляем из БД
                        with db.get_connection() as conn2:
                            cur2 = conn2.cursor()
                            cur2.execute("DELETE FROM vacation_active WHERE user_id = ?", (user_id,))
                            conn2.commit()
                        
                        logger.info(f"✅ {user_name} успешно возвращён")
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка при возврате {user_name}: {e}")
                
                # Обновляем embed
                if expired:
                    settings = vacation_manager.get_settings()
                    if settings.get('vacation_public_channel'):
                        await update_vacation_embed(self.bot, settings['vacation_public_channel'])
                        logger.info(f"✅ Embed обновлён")
                
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
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
                await asyncio.sleep(60)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM vacation_active WHERE until_date < date('now')")
                    if cursor.rowcount > 0:
                        logger.info(f"🗑️ Удалено {cursor.rowcount} просроченных отпусков")
                        settings = vacation_manager.get_settings()
                        if settings.get('vacation_public_channel'):
                            await update_vacation_embed(self.bot, settings['vacation_public_channel'])
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой проверке: {e}")
    
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