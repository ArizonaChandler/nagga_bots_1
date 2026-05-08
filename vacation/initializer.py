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
        
        settings = vacation_manager.get_settings()
        
        # ⭐ ДОБАВЛЕНА ПРОВЕРКА ПРОСРОЧЕННЫХ ПРИ ЗАПУСКЕ ⭐
        await self._check_expired_on_startup()
        
        # 1. Публичный канал с кнопками
        await self._init_public_channel(settings)
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Запускаем проверку просроченных отпусков
        await self.start_expiry_checker()
        
        logger.info("✅ Инициализация системы отпусков завершена")
    
    async def _check_expired_on_startup(self):
        """ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ (ДОБАВЛЕНО)"""
        import traceback
        
        print("🔥🔥🔥 МЕТОД _check_expired_on_startup ВЫЗВАН 🔥🔥🔥")
        logger.info("🔥🔥🔥 МЕТОД _check_expired_on_startup ВЫЗВАН 🔥🔥🔥")
        
        try:
            print("🔍 1. Получаю подключение к БД...")
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                print("🔍 2. Проверяю таблицу...")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacation_active'")
                if not cursor.fetchone():
                    print("⚠️ Таблица vacation_active не существует")
                    logger.warning("⚠️ Таблица vacation_active не существует")
                    return
                
                print("🔍 3. Ищу просроченных...")
                cursor.execute("SELECT user_id, user_name, saved_roles, guild_id, until_date FROM vacation_active WHERE until_date < date('now')")
                expired = cursor.fetchall()
                
                print(f"🔍 4. Найдено просроченных: {len(expired)}")
                logger.info(f"📊 Найдено просроченных: {len(expired)}")
                
                for user_id, user_name, saved_roles, guild_id, until_date in expired:
                    try:
                        print(f"🔍 5. Обрабатываю {user_name} (ID: {user_id})...")
                        
                        guild = self.bot.get_guild(int(guild_id))
                        if not guild:
                            print(f"❌ Гильдия {guild_id} не найдена")
                            continue
                        
                        member = guild.get_member(int(user_id))
                        if not member:
                            try:
                                member = await guild.fetch_member(int(user_id))
                            except:
                                print(f"❌ Не могу найти {user_id} на сервере")
                                continue
                        
                        # Восстанавливаем роли
                        if saved_roles:
                            for rid in saved_roles.split(','):
                                rid = rid.strip()
                                try:
                                    role = guild.get_role(int(rid))
                                    if role and role.position < guild.me.top_role.position:
                                        await member.add_roles(role)
                                        print(f"   ✅ Добавлена роль {role.name}")
                                except Exception as e:
                                    print(f"   ❌ Не могу добавить роль {rid}: {e}")
                        
                        # Снимаем роль отпуска
                        vacation_role_id = vacation_manager.get_settings().get('vacation_role')
                        if vacation_role_id:
                            try:
                                vacation_role = guild.get_role(int(vacation_role_id))
                                if vacation_role and vacation_role in member.roles:
                                    await member.remove_roles(vacation_role)
                                    print(f"   ✅ Снята роль отпуска")
                            except Exception as e:
                                print(f"   ❌ Ошибка снятия роли отпуска: {e}")
                        
                        # Отправляем ЛС
                        try:
                            user = await self.bot.fetch_user(int(user_id))
                            if user:
                                await user.send(f"✅ **Вы автоматически возвращены из отпуска!**\nВаши роли восстановлены.")
                                print(f"   ✅ ЛС отправлено")
                        except Exception as e:
                            print(f"   ❌ Ошибка отправки ЛС: {e}")
                        
                        # Удаляем из БД
                        with db.get_connection() as conn2:
                            cur2 = conn2.cursor()
                            cur2.execute("DELETE FROM vacation_active WHERE user_id = ?", (user_id,))
                            conn2.commit()
                        
                        print(f"✅ {user_name} успешно возвращён")
                        
                    except Exception as e:
                        print(f"❌ Ошибка при возврате {user_name}: {e}")
                
                # Обновляем embed
                if expired:
                    settings = vacation_manager.get_settings()
                    if settings.get('vacation_public_channel'):
                        await update_vacation_embed(self.bot, settings['vacation_public_channel'])
                        print(f"✅ Embed обновлён")
                
        except Exception as e:
            print(f"❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            traceback.print_exc()
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
    
    async def start_expiry_checker(self):
        """Запустить фоновую задачу для проверки просроченных отпусков"""
        self.bot.loop.create_task(self._check_expired_vacations())
        logger.info("✅ Запущен автоматический проверщик просроченного отпуска")
    
    async def _check_expired_vacations(self):
        """Фоновая задача: проверять каждые 60 секунд"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                expired = vacation_manager.check_expired_vacations()
                
                if expired:
                    logger.info(f"⏰ Найдено просроченных отпусков: {len(expired)}")
                    settings = vacation_manager.get_settings()
                    
                    # Обновляем embed
                    channel_id = settings.get('vacation_public_channel')
                    if channel_id:
                        await update_vacation_embed(self.bot, channel_id)
                    
                    # Отправляем логи и ЛС
                    log_channel_id = settings.get('vacation_log_channel')
                    if log_channel_id:
                        log_channel = self.bot.get_channel(int(log_channel_id))
                        if log_channel:
                            for user_id, user_name in expired:
                                embed = discord.Embed(
                                    title="⏰ ОТПУСК ЗАКОНЧИЛСЯ",
                                    description=f"У пользователя **{user_name}** закончился отпуск",
                                    color=0xffa500,
                                    timestamp=datetime.now(MSK_TZ)
                                )
                                await log_channel.send(embed=embed)
                                
                                # Отправляем ЛС
                                try:
                                    user = await self.bot.fetch_user(int(user_id))
                                    if user:
                                        await user.send("✅ Ваш отпуск закончился! Добро пожаловать обратно!")
                                except:
                                    pass
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в проверке отпусков: {e}")
                await asyncio.sleep(60)
    
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
        
        from vacation.views import VacationPublicView, update_vacation_embed
        
        # Ищем существующее сообщение с кнопками
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                if msg.components and len(msg.components) > 0:
                    for component in msg.components:
                        for button in component.children:
                            if button.custom_id in ["vacation_go", "vacation_back"]:
                                await msg.edit(view=VacationPublicView())
                                message_exists = True
                                logger.info(f"✅ Обновлена панель отпусков в #{channel.name}")
                                break
                        if message_exists:
                            break
                if message_exists:
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