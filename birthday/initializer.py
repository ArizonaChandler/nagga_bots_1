"""Инициализация каналов системы дней рождения"""
import discord
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from birthday.views import BirthdayPublicView, update_birthday_embed
from birthday.settings import BirthdaySettingsView
from birthday.manager import birthday_manager
from core.database import db

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


class BirthdayInitializer:
    """Инициализатор каналов системы дней рождения"""

    def __init__(self, bot):
        self.bot = bot

    async def initialize_all(self):
        """Инициализировать все каналы системы дней рождения"""
        logger.info("🔄 Инициализация системы дней рождения...")
        print("🎂 [Birthday] Инициализация системы дней рождения...")

        self.channel_id = db.get_setting('birthday_channel')
        self.settings_channel_id = db.get_setting('birthday_settings_channel')

        # 1. Публичный канал с кнопками
        await self._init_public_channel()

        # 2. Канал настроек
        await self._init_settings_channel()

        # 3. Запускаем проверку дней рождений в 00:00
        await self.start_birthday_checker()

        logger.info("✅ Инициализация системы дней рождения завершена")
        print("🎂 [Birthday] Инициализация системы дней рождения завершена")

    async def _init_public_channel(self):
        """Публичный канал с кнопками и embed"""
        if not self.channel_id:
            logger.warning("⚠️ Канал дней рождения не настроен")
            print("⚠️ [Birthday] Канал дней рождения не настроен")
            return

        channel = self.bot.get_channel(int(self.channel_id))
        if not channel:
            logger.error(f"❌ Канал дней рождения {self.channel_id} не найден")
            return

        await update_birthday_embed(self.bot, self.channel_id)

    async def _init_settings_channel(self):
        """Канал настроек дней рождения"""
        if not self.settings_channel_id:
            logger.warning("⚠️ Канал настроек дней рождения не настроен")
            return

        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ ДНЕЙ РОЖДЕНИЯ" in msg.embeds[0].title:
                    await msg.edit(view=BirthdaySettingsView())
                    logger.info(f"✅ Обновлена панель настроек в #{channel.name}")
                    return

        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ ДНЕЙ РОЖДЕНИЯ**",
            description="Настройка системы дней рождения",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=BirthdaySettingsView())
        logger.info(f"✅ Создана панель настроек в #{channel.name}")

    async def start_birthday_checker(self):
        """Запустить проверку дней рождений в 00:00"""
        self.bot.loop.create_task(self._birthday_checker())
        logger.info("✅ Запущен проверщик дней рождения (каждый день в 00:00)")

    async def _birthday_checker(self):
        """Проверка дней рождений в 00:00"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            now = datetime.now(MSK_TZ)
            tomorrow = now + timedelta(days=1)
            next_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
            next_midnight = MSK_TZ.localize(next_midnight)
            seconds_to_wait = (next_midnight - now).total_seconds()

            await asyncio.sleep(seconds_to_wait)

            try:
                await self._send_birthday_greetings()
            except Exception as e:
                logger.error(f"❌ Ошибка отправки поздравлений: {e}")

    async def _send_birthday_greetings(self):
        """Отправить поздравления именинникам"""
        if not self.channel_id:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        if not channel:
            return

        today_birthdays = birthday_manager.get_today_birthdays()

        if not today_birthdays:
            return

        # Отправляем поздравления
        for bd in today_birthdays:
            embed = discord.Embed(
                title="🎉 **С ДНЁМ РОЖДЕНИЯ!** 🎉",
                description=f"Поздравляем <@{bd['user_id']}>!\n"
                            f"Желаем счастья, здоровья и удачи! 🎂🥳",
                color=0xffa500,
                timestamp=datetime.now(MSK_TZ)
            )
            await channel.send(content=f"🎉 <@{bd['user_id']}> 🎉", embed=embed)

        # Обновляем embed (чтобы убрать подсветку сегодняшних)
        await update_birthday_embed(self.bot, self.channel_id)


initializer = None

async def setup(bot):
    global initializer
    initializer = BirthdayInitializer(bot)
    await initializer.initialize_all()
    return initializer