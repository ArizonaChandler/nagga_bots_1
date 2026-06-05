"""Инициализация каналов системы отпусков"""
import asyncio
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from vacation.manager import vacation_manager
from vacation.views import VacationPublicView, update_vacation_embed
from vacation.settings_view import VacationSettingsView

MSK_TZ = pytz.timezone('Europe/Moscow')


class VacationInitializer:
    """Инициализатор каналов системы отпусков"""

    def __init__(self, bot):
        self.bot = bot

    async def initialize_all(self):
        """Инициализировать все каналы системы отпусков"""
        settings = vacation_manager.get_settings()

        await self._check_expired_on_startup()
        await self._init_public_channel(settings)
        await self._init_settings_channel()
        await self._start_midnight_checker()
        await self._restore_application_buttons()

    async def _check_expired_on_startup(self):
        """Проверка просроченных отпусков при запуске"""
        expired = db.get_expired_vacations()

        for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
            await self._return_user_from_vacation(user_id, user_name, saved_roles, guild_id, until_date)

        if expired:
            await self._refresh_public_embed()

    async def _return_user_from_vacation(self, user_id: str, user_name: str, saved_roles: str, guild_id: str, until_date: str):
        """Вернуть пользователя из отпуска и восстановить роли"""
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return

        member = guild.get_member(int(user_id))
        if not member:
            try:
                member = await guild.fetch_member(int(user_id))
            except:
                return

        # Восстановление ролей
        if saved_roles:
            for rid in saved_roles.split(','):
                rid = rid.strip()
                role = guild.get_role(int(rid))
                if role and role.position < guild.me.top_role.position:
                    await member.add_roles(role)

        # Снятие роли отпуска
        vacation_role_id = vacation_manager.get_settings().get('vacation_role')
        if vacation_role_id:
            vacation_role = guild.get_role(int(vacation_role_id))
            if vacation_role and vacation_role in member.roles:
                await member.remove_roles(vacation_role)

        # Удаление из БД
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vacation_active WHERE user_id = ?', (user_id,))
            conn.commit()

        # ЛС пользователю
        try:
            user = await self.bot.fetch_user(int(user_id))
            if user:
                await user.send("✅ **Вы автоматически возвращены из отпуска.** Ваши роли восстановлены.")
        except:
            pass

        # Лог в канал
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
                await log_channel.send(embed=embed)

    async def _start_midnight_checker(self):
        """Запуск фоновой проверки в 00:00 каждый день"""
        self.bot.loop.create_task(self._midnight_checker())

    async def _midnight_checker(self):
        """Фоновая проверка раз в сутки в полночь"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            now = datetime.now(MSK_TZ)
            tomorrow = now + timedelta(days=1)
            next_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
            next_midnight = MSK_TZ.localize(next_midnight)
            seconds_to_wait = (next_midnight - now).total_seconds()

            await asyncio.sleep(seconds_to_wait)

            expired = db.get_expired_vacations()
            for user_id, user_name, saved_roles, guild_id, reason, until_date in expired:
                await self._return_user_from_vacation(user_id, user_name, saved_roles, guild_id, until_date)

            if expired:
                await self._refresh_public_embed()

    async def _refresh_public_embed(self):
        """Обновить embed в публичном канале"""
        settings = vacation_manager.get_settings()
        channel_id = settings.get('vacation_public_channel')
        if channel_id:
            await update_vacation_embed(self.bot, channel_id)

    async def _init_public_channel(self, settings):
        """Инициализация публичного канала с кнопками"""
        channel_id = settings.get('vacation_public_channel')
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.edit(view=VacationPublicView())
                break
        else:
            embed = discord.Embed(
                title="🏖️ **СИСТЕМА ОТПУСКОВ**",
                description="✨ Никого нет в отпуске",
                color=0x00ff00
            )
            embed.set_footer(text="Нажмите кнопку, чтобы подать заявку")
            await channel.send(embed=embed, view=VacationPublicView())

        await update_vacation_embed(self.bot, channel_id)

    async def _init_settings_channel(self):
        """Инициализация канала настроек отпусков"""
        from core.config import CONFIG
        channel_id = CONFIG.get('vacation_settings_channel')
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if "НАСТРОЙКИ ОТПУСКОВ" in msg.embeds[0].title:
                    await msg.edit(view=VacationSettingsView())
                    break
        else:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ ОТПУСКОВ**",
                description="Настройка системы отпусков",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=VacationSettingsView())

    def get_all_application_messages(self):
        return db.get_all_vacation_application_messages()

    def delete_application_message(self, application_id: int):
        return db.delete_vacation_application_message(application_id)

    async def _restore_application_buttons(self):
        """Восстановить кнопки у активных заявок на отпуск"""
        from vacation.views import VacationModerationView
        
        print("🔄 [VACATION] Восстановление кнопок заявок на отпуск...")
        
        messages = vacation_manager.get_all_application_messages()
        
        if not messages:
            print("📭 [VACATION] Нет активных заявок для восстановления")
            return
        
        restored = 0
        for msg_data in messages:
            try:
                channel = self.bot.get_channel(int(msg_data['channel_id']))
                if not channel:
                    print(f"❌ [VACATION] Канал {msg_data['channel_id']} не найден")
                    continue
                
                try:
                    message = await channel.fetch_message(int(msg_data['message_id']))
                except discord.NotFound:
                    print(f"❌ [VACATION] Сообщение {msg_data['message_id']} не найдено")
                    vacation_manager.delete_application_message(msg_data['application_id'])
                    continue
                
                # Восстанавливаем view
                view = VacationModerationView(msg_data['application_id'])
                await message.edit(view=view)
                restored += 1
                print(f"✅ [VACATION] Восстановлена заявка на отпуск {msg_data['application_id']} в #{channel.name}")
                
            except Exception as e:
                print(f"❌ [VACATION] Ошибка восстановления заявки {msg_data['application_id']}: {e}")
        
        print(f"✅ [VACATION] Восстановлено {restored} заявок на отпуск")

    async def stop(self):
        """Остановить систему отпусков"""
        print("🏖️ [VACATION] Остановка системы отпусков...")
        
        if hasattr(self, 'task') and self.task:
            self.task.cancel()
        
        settings = vacation_manager.get_settings()
        channel_id = settings.get('vacation_public_channel')
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                async for msg in channel.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        await msg.edit(
                            embed=discord.Embed(
                                title="🏖️ **СИСТЕМА ОТПУСКОВ**",
                                description="⛔ **Система отключена администратором**\nОбратитесь к администрации для включения.",
                                color=0x808080
                            ),
                            view=None
                        )
                        break


# Глобальный экземпляр
initializer = None

async def setup(bot):
    global initializer
    initializer = VacationInitializer(bot)
    await initializer.initialize_all()
    return initializer