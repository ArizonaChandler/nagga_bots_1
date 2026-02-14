"""Event Views - Кнопки для мероприятий"""
import discord
import logging
import traceback
from datetime import datetime, timedelta
import pytz
from core.database import db
from core.config import CONFIG
from core.menus import BaseMenuView

# Настройка логирования
file_logger = logging.getLogger('events_views')
file_logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('events_views.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
file_logger.addHandler(fh)

MSK_TZ = pytz.timezone('Europe/Moscow')

class EventReminderView(discord.ui.View):
    """Кнопка 'Взять МП' в напоминании"""
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str, guild):
        file_logger.debug("="*50)
        file_logger.debug("EventReminderView __init__ START")
        file_logger.debug(f"event_id: {event_id}, event_name: {event_name}, event_time: {event_time}, meeting_time: {meeting_time}")
        
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        file_logger.debug(f"now: {now}")
        
        # Парсим время мероприятия
        event_hour, event_min = map(int, event_time.split(':'))
        file_logger.debug(f"event_hour: {event_hour}, event_min: {event_min}")
        
        # Создаем datetime для времени мероприятия
        event_datetime = msk_tz.localize(datetime(
            now.year, now.month, now.day,
            event_hour, event_min
        ))
        file_logger.debug(f"event_datetime: {event_datetime}")
        
        # Если время мероприятия уже прошло - добавляем день
        if event_datetime < now:
            file_logger.debug("Время мероприятия прошло, добавляем день")
            event_datetime += timedelta(days=1)
            file_logger.debug(f"new event_datetime: {event_datetime}")
        
        # Время таймаута (за 10 минут до начала)
        timeout_datetime = event_datetime - timedelta(minutes=10)
        timeout_seconds = max(0, (timeout_datetime - now).total_seconds())
        file_logger.debug(f"timeout_datetime: {timeout_datetime}")
        file_logger.debug(f"timeout_seconds: {timeout_seconds}")
        
        super().__init__(timeout=timeout_seconds)
        
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        self.guild = guild
        self.taken = False
        self.message = None
        self.timeout_occurred = False
        
        file_logger.debug("EventReminderView __init__ END")
    
    @discord.ui.button(label="🎮 ВЗЯТЬ МП", style=discord.ButtonStyle.success, emoji="🎮")
    async def take_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        file_logger.debug("="*50)
        file_logger.debug("take_event CALLED")
        file_logger.debug(f"user: {interaction.user.id} - {interaction.user.name}")
        file_logger.debug(f"timeout_occurred: {self.timeout_occurred}")
        file_logger.debug(f"taken: {self.taken}")
        
        # ПРОВЕРКА: Если таймаут уже наступил - блокируем
        if self.timeout_occurred:
            file_logger.warning("Попытка взять МП после таймаута")
            await interaction.response.send_message("⏰ Время на взятие МП истекло!", ephemeral=True)
            return
        
        if self.taken:
            file_logger.warning("Попытка взять уже взятое МП")
            await interaction.response.send_message("❌ Уже взято", ephemeral=True)
            return
        
        today = datetime.now(MSK_TZ).date().isoformat()
        file_logger.debug(f"today: {today}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT taken_by FROM event_schedule 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (self.event_id, today))
            result = cursor.fetchone()
            file_logger.debug(f"result from DB: {result}")
            
            if result and result[0]:
                self.taken = True
                button.disabled = True
                file_logger.info(f"МП уже взято пользователем {result[0]}")
                
                # Обновляем embed
                embed = self.message.embeds[0]
                new_embed = discord.Embed(
                    title=f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}",
                    description=f"Мероприятие проведёт: <@{result[0]}>",
                    color=0x00ff00
                )
                
                new_embed.add_field(
                    name="⏱️ Сбор в",
                    value=f"**{self.meeting_time}** МСК",
                    inline=False
                )
                
                new_embed.add_field(
                    name="📍 Место сбора",
                    value="Будет указано организатором",
                    inline=True
                )
                
                new_embed.add_field(
                    name="🔢 Код группы",
                    value="Будет указан организатором",
                    inline=True
                )
                
                new_embed.add_field(
                    name="Участие:",
                    value="Для участия зайди в игру, в войс и приедь на место сбора",
                    inline=False
                )
                
                new_embed.set_footer(text="Unit Management System by Nagga")
                
                await self.message.edit(embed=new_embed, view=self)
                await interaction.response.send_message(f"❌ Уже взял <@{result[0]}>", ephemeral=True)
                return
        
        from admin.modals import TakeEventModal
        modal = TakeEventModal(
            self.event_id, 
            self.event_name, 
            self.event_time, 
            self.meeting_time,
            self
        )
        file_logger.debug("Открытие модального окна TakeEventModal")
        await interaction.response.send_modal(modal)
    
    async def update_taken_status(self, user_id: str, user_name: str, group_code: str, meeting_place: str):
        """Мгновенно обновить статус после взятия МП"""
        file_logger.debug("="*50)
        file_logger.debug("update_taken_status CALLED")
        file_logger.debug(f"user_id: {user_id}, user_name: {user_name}")
        file_logger.debug(f"group_code: {group_code}, meeting_place: {meeting_place}")
        
        self.taken = True
        for child in self.children:
            child.disabled = True
        
        if self.message:
            embed = discord.Embed(
                title=f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}",
                description=f"Мероприятие проведёт: <@{user_id}>",
                color=0x00ff00
            )
            
            embed.add_field(
                name="⏱️ Сбор в",
                value=f"**{self.meeting_time}** МСК",
                inline=False
            )
            
            embed.add_field(
                name="📍 Место сбора",
                value=meeting_place,
                inline=True
            )
            
            embed.add_field(
                name="🔢 Код группы",
                value=group_code,
                inline=True
            )
            
            embed.add_field(
                name="Участие:",
                value="Для участия зайди в игру, в войс и приедь на место сбора",
                inline=False
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            file_logger.info(f"Обновление статуса: МП {self.event_name} взял {user_name}")
            await self.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        """Когда время вышло (за 10 минут до начала)"""
        file_logger.debug("="*50)
        file_logger.debug("on_timeout CALLED")
        file_logger.debug(f"taken: {self.taken}")
        
        self.timeout_occurred = True
        if not self.taken and self.message:
            file_logger.info(f"ТАЙМАУТ для МП {self.event_name}")
            
            # Отключаем все кнопки
            for child in self.children:
                child.disabled = True
            
            # Обновляем embed
            embed = discord.Embed(
                title=f"⏰ ВРЕМЯ ВЫШЛО: {self.event_name}",
                description=f"Мероприятие в **{self.event_time}** не состоялось - никто не взял его вовремя.",
                color=0xff0000
            )
            
            embed.add_field(
                name="⏰ Время начала",
                value=f"**{self.event_time}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Сбор был в",
                value=f"**{self.meeting_time}** МСК",
                inline=True
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            await self.message.edit(embed=embed, view=self)


class EventInfoView(BaseMenuView):
    """Кнопка информации о мероприятии в !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        file_logger.debug("EventInfoView __init__")
        super().__init__(user_id, guild, previous_view, previous_embed)
        self.add_item(self.create_button())
    
    def create_button(self):
        btn = discord.ui.Button(label="📅 Мероприятия сегодня", style=discord.ButtonStyle.primary, emoji="📅")
        async def callback(interaction: discord.Interaction, button: discord.ui.Button):
            file_logger.debug(f"EventInfoView button clicked by {interaction.user.id}")
            await self.today_events(interaction, button)
        btn.callback = callback
        return btn
    
    async def today_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        file_logger.debug("="*50)
        file_logger.debug("today_events CALLED")
        
        today = datetime.now(MSK_TZ).date()
        weekday = today.weekday()
        file_logger.debug(f"today: {today}, weekday: {weekday}")
        
        events = db.get_events(enabled_only=True, weekday=weekday)
        file_logger.debug(f"Найдено мероприятий: {len(events)}")
        
        if not events:
            file_logger.debug("Мероприятий нет")
            self.clear_items()
            self.add_back_button()
            await interaction.response.edit_message(
                content="📅 На сегодня мероприятий нет",
                embed=None,
                view=self
            )
            return
        
        embed = discord.Embed(
            title=f"📅 МЕРОПРИЯТИЯ НА СЕГОДНЯ ({today.strftime('%d.%m.%Y')})",
            color=0x7289da
        )
        
        for event in events:
            file_logger.debug(f"Обработка события: {event['id']} - {event['name']} - {event['event_time']}")
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT taken_by, group_code, meeting_place FROM event_schedule 
                    WHERE event_id = ? AND scheduled_date = ?
                ''', (event['id'], today.isoformat()))
                result = cursor.fetchone()
                file_logger.debug(f"Результат из БД: {result}")
            
            if result and result[0]:
                status = f"✅ **Взял:** <@{result[0]}>\n📍 {result[2]}\n🔢 {result[1]}"
            else:
                status = "❌ **Свободно**"
            
            embed.add_field(
                name=f"{event['event_time']} — {event['name']}",
                value=status,
                inline=False
            )
        
        self.clear_items()
        self.add_back_button()
        await interaction.response.edit_message(embed=embed, view=self)