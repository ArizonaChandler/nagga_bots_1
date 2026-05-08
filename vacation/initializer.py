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
        
        # ⭐⭐⭐ ДОБАВЛЕНО: ПРОВЕРКА ПРОСРОЧЕННЫХ ПРИ ЗАПУСКЕ ⭐⭐⭐
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
        print("🔥🔥🔥 ПРОВЕРКА ПРОСРОЧЕННЫХ ОТПУСКОВ ПРИ ЗАПУСКЕ 🔥🔥🔥")
        logger.info("🔍 Проверка просроченных отпусков при запуске...")
        
        try:
            # ИСПОЛЬЗУЕМ МЕТОД ИЗ DATABASE.PY
            expired = db.get_expired_vacations()
            
            if not expired:
                print("✅ Нет просроченных отпусков")
                logger.info("✅ Нет просроченных отпусков")
                return
            
            print(f"⚠️ Найдено просроченных отпусков: {len(expired)}")
            logger.info(f"⚠️ Найдено просроченных отпусков: {len(expired)}")
            
            for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
                try:
                    print(f"🔄 Возвращаем {user_name} (ID: {user_id}) из отпуска...")
                    
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        print(f"❌ Сервер {guild_id} не найден для {user_name}")
                        continue
                    
                    member = guild.get_member(int(user_id))
                    if not member:
                        try:
                            member = await guild.fetch_member(int(user_id))
                        except:
                            print(f"❌ Пользователь {user_id} не найден на сервере")
                            continue
                    
                    # Восстанавливаем роли
                    restored_roles = []
                    if saved_roles:
                        role_ids = [rid.strip() for rid in saved_roles.split(',') if rid.strip()]
                        for rid in role_ids:
                            try:
                                role = guild.get_role(int(rid))
                                if role and role.position < guild.me.top_role.position:
                                    await member.add_roles(role)
                                    restored_roles.append(role.name)
                                    print(f"   ✅ Роль {role.name} восстановлена")
                            except Exception as e:
                                print(f"   ❌ Ошибка восстановления роли {rid}: {e}")
                    
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
                    
                    # Отправляем ЛС пользователю
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="✅ ВОЗВРАТ ИЗ ОТПУСКА",
                                description=f"**Ваш отпуск автоматически завершён.**\n\n"
                                            f"📅 Длился до: {until_date}\n"
                                            f"✅ Восстановлено ролей: {len(restored_roles)}",
                                color=0x00ff00
                            )
                            if restored_roles:
                                embed.add_field(name="✅ Восстановленные роли", value=", ".join(restored_roles), inline=False)
                            await user.send(embed=embed)
                            print(f"   ✅ ЛС отправлено {user_name}")
                    except Exception as e:
                        print(f"   ❌ Ошибка отправки ЛС: {e}")
                    
                    # Удаляем из БД (через database.py)
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
                        conn.commit()
                    
                    print(f"✅ {user_name} успешно возвращён")
                    
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
                    print(f"❌ Критическая ошибка при возврате {user_name}: {e}")
            
            # Обновляем embed в публичном канале
            settings = vacation_manager.get_settings()
            public_channel_id = settings.get('vacation_public_channel')
            if public_channel_id:
                await update_vacation_embed(self.bot, public_channel_id)
                print(f"✅ Embed обновлён в публичном канале")
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в _check_expired_on_startup: {e}")
            import traceback
            traceback.print_exc()
    
    async def start_expiry_checker(self):
        """Запустить фоновую задачу для проверки просроченных отпусков"""
        self.bot.loop.create_task(self._check_expired_vacations())
        logger.info("✅ Запущен автоматический проверщик просроченного отпуска")
        print("✅ ЗАПУЩЕН ФОНОВЫЙ ПРОВЕРЩИК (КАЖДУЮ МИНУТУ)")
    
    async def _check_expired_vacations(self):
        """Фоновая задача: проверять каждые 60 секунд"""
        await self.bot.wait_until_ready()
        
        print("🔄 ФОНОВЫЙ ПРОВЕРЩИК ЗАПУЩЕН, ЖДУ ПЕРВУЮ ПРОВЕРКУ...")
        
        while not self.bot.is_closed():
            await asyncio.sleep(60)  # Проверка каждую минуту
            
            try:
                print("🔍 Фоновая проверка просроченных отпусков...")
                expired = db.get_expired_vacations()
                
                if expired:
                    print(f"⏰ Найдено просроченных отпусков: {len(expired)}")
                    logger.info(f"⏰ Найдено просроченных отпусков: {len(expired)}")
                    
                    for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
                        try:
                            # Возвращаем пользователя (ТОТ ЖЕ КОД, ЧТО В _check_expired_on_startup)
                            guild = self.bot.get_guild(int(guild_id))
                            if guild:
                                member = guild.get_member(int(user_id))
                                if member:
                                    if saved_roles:
                                        for rid in saved_roles.split(','):
                                            role = guild.get_role(int(rid.strip()))
                                            if role and role.position < guild.me.top_role.position:
                                                await member.add_roles(role)
                                    
                                    vacation_role_id = vacation_manager.get_settings().get('vacation_role')
                                    if vacation_role_id:
                                        vacation_role = guild.get_role(int(vacation_role_id))
                                        if vacation_role and vacation_role in member.roles:
                                            await member.remove_roles(vacation_role)
                            
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
                                conn.commit()
                            
                            print(f"✅ {user_name} автоматически возвращён")
                            
                        except Exception as e:
                            print(f"❌ Ошибка возврата {user_name}: {e}")
                    
                    # Обновляем embed
                    settings = vacation_manager.get_settings()
                    if settings.get('vacation_public_channel'):
                        await update_vacation_embed(self.bot, settings['vacation_public_channel'])
                
            except Exception as e:
                print(f"❌ Ошибка в фоновой проверке: {e}")
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