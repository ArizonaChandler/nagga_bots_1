"""Инициализация каналов системы дней рождения"""
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from birthday.views import BirthdayPublicView, update_birthday_embed
from birthday.settings import BirthdaySettingsView
from birthday.manager import birthday_manager

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

        # Загружаем настройки из БД
        self.channel_id = db.get_setting('birthday_channel')
        self.greeting_channel_id = db.get_setting('birthday_greeting_channel')
        self.settings_channel_id = db.get_setting('birthday_settings_channel')

        # 1. Публичный канал с кнопками и embed
        await self._init_public_channel()

        # 2. Канал настроек (панель управления)
        await self._init_settings_channel()

        # 3. Запускаем проверку дней рождений в 00:00
        await self.start_birthday_checker()

        logger.info("✅ Инициализация системы дней рождения завершена")
        print("🎂 [Birthday] Инициализация системы дней рождения завершена")

    async def _init_public_channel(self):
        """Публичный канал с кнопками и embed именинников месяца — ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ"""
        if not self.channel_id:
            logger.warning("⚠️ Публичный канал дней рождения не настроен")
            print("⚠️ [Birthday] Публичный канал дней рождения не настроен")
            return

        channel = self.bot.get_channel(int(self.channel_id))
        if not channel:
            logger.error(f"❌ Публичный канал {self.channel_id} не найден")
            return

        # УДАЛЯЕМ ВСЕ СТАРЫЕ СООБЩЕНИЯ БОТА В ЭТОМ КАНАЛЕ
        deleted_count = 0
        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                    deleted_count += 1
                except:
                    pass
        print(f"🎂 [Birthday] Удалено старых сообщений: {deleted_count}")

        # СОЗДАЁМ НОВЫЙ EMBED С КНОПКАМИ
        now = datetime.now()
        months = {
            '01': 'Январе', '02': 'Феврале', '03': 'Марте', '04': 'Апреле',
            '05': 'Мае', '06': 'Июне', '07': 'Июле', '08': 'Августе',
            '09': 'Сентябре', '10': 'Октябре', '11': 'Ноябре', '12': 'Декабре'
        }
        current_month = now.strftime("%m")
        birthdays = birthday_manager.get_birthdays_by_month(current_month)
        birthdays.sort(key=lambda x: int(x['birthday_date'][:2]))

        embed = discord.Embed(
            title="🎂 **ДНИ РОЖДЕНИЯ**",
            description=f"Именинники в **{months.get(current_month, 'этом месяце')}**:",
            color=0xffa500,
            timestamp=now
        )

        if birthdays:
            text = ""
            for bd in birthdays:
                day = bd['birthday_date'][:2]
                if bd['birthday_date'] == now.strftime("%d.%m"):
                    text += f"🎉 **<@{bd['user_id']}> — {day} числа (СЕГОДНЯ!)** 🎉\n"
                else:
                    text += f"• <@{bd['user_id']}> — {day} числа\n"
            embed.description += f"\n\n{text}"
        else:
            embed.description += "\n\n✨ В этом месяце пока нет именинников"

        embed.set_footer(text="Нажмите кнопку, чтобы указать свой день рождения")

        await channel.send(embed=embed, view=BirthdayPublicView())
        print(f"🎂 [Birthday] Создан новый embed с кнопками в #{channel.name}")

    async def _init_settings_channel(self):
        """Канал настроек (панель управления системой)"""
        if not self.settings_channel_id:
            logger.warning("⚠️ Канал настроек дней рождения не настроен")
            print("⚠️ [Birthday] Канал настроек дней рождения не настроен")
            return

        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
            return

        # Удаляем старые сообщения бота
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()

        # Создаём новое сообщение с панелью управления
        embed = discord.Embed(
            title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ ДНЕЙ РОЖДЕНИЯ**",
            description="Настройка и управление системой",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=BirthdaySettingsView())
        print(f"🎂 [Birthday] Создана панель управления в #{channel.name}")

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
        enabled = db.get_setting('birthday_enabled')
        if enabled == '0':
            return

        channel_id = self.greeting_channel_id or self.channel_id
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        today_birthdays = birthday_manager.get_today_birthdays()

        for bd in today_birthdays:
            embed = discord.Embed(
                title="🎉 **С ДНЁМ РОЖДЕНИЯ!** 🎉",
                description=f"Поздравляем <@{bd['user_id']}>!\n"
                            f"Желаем счастья, здоровья и удачи! 🎂🥳",
                color=0xffa500,
                timestamp=datetime.now(MSK_TZ)
            )
            await channel.send(content=f"🎉 <@{bd['user_id']}> 🎉", embed=embed)

        if today_birthdays and self.channel_id:
            await update_birthday_embed(self.bot, self.channel_id)


initializer = None

async def setup(bot):
    global initializer
    initializer = BirthdayInitializer(bot)
    await initializer.initialize_all()
    return initializer