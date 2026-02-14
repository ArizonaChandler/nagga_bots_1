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
    """Кнопка 'Взять МП' с поддержкой нескольких каналов"""
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str, guild, reminder_channels=None):
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        
        # Парсим время мероприятия
        event_hour, event_min = map(int, event_time.split(':'))
        
        # Создаем datetime для времени мероприятия
        event_datetime = msk_tz.localize(datetime(
            now.year, now.month, now.day,
            event_hour, event_min
        ))
        
        # Если время мероприятия уже прошло - добавляем день
        if event_datetime < now:
            event_datetime += timedelta(days=1)
        
        # Время таймаута (за 10 минут до начала)
        timeout_datetime = event_datetime - timedelta(minutes=10)
        timeout_seconds = max(0, (timeout_datetime - now).total_seconds())
        
        super().__init__(timeout=timeout_seconds)
        
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        self.guild = guild
        self.taken = False
        self.messages = {}  # Словарь {channel_id: message}
        self.reminder_channels = reminder_channels or []
        self.timeout_occurred = False
    
    def add_message(self, message, channel_id):
        """Добавить сообщение из конкретного канала"""
        self.messages[str(channel_id)] = message
    
    async def update_all_messages(self, embed, view=None):
        """Обновить сообщения во всех каналах"""
        view = view or self
        for channel_id, message in self.messages.items():
            try:
                await message.edit(embed=embed, view=view)
            except Exception as e:
                file_logger.error(f"Ошибка обновления сообщения в канале {channel_id}: {e}")
    
    @discord.ui.button(label="🎮 ВЗЯТЬ МП", style=discord.ButtonStyle.success, emoji="🎮")
    async def take_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        file_logger.debug("="*50)
        file_logger.debug("take_event CALLED")
        
        if self.timeout_occurred:
            await interaction.response.send_message("⏰ Время на взятие МП истекло!", ephemeral=True)
            return
        
        if self.taken:
            await interaction.response.send_message("❌ Уже взято", ephemeral=True)
            return
        
        today = datetime.now(MSK_TZ).date().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT taken_by FROM event_schedule 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (self.event_id, today))
            result = cursor.fetchone()
            
            if result and result[0]:
                self.taken = True
                button.disabled = True
                
                # Обновляем embed
                announce_roles = CONFIG.get('announce_roles', [])
                role_mentions = []
                for role_id in announce_roles:
                    role = self.guild.get_role(int(role_id))
                    if role:
                        role_mentions.append(role.mention)
                
                content = ' '.join(role_mentions) if role_mentions else None
                
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
                
                # Обновляем ВСЕ сообщения
                await self.update_all_messages(new_embed)
                
                await interaction.response.send_message(f"❌ Уже взял <@{result[0]}>", ephemeral=True)
                return
        
        from admin.modals import TakeEventModal
        modal = TakeEventModal(
            self.event_id, 
            self.event_name, 
            self.event_time, 
            self.meeting_time,
            self  # Передаем view для обновления всех каналов
        )
        await interaction.response.send_modal(modal)
    
    async def update_taken_status(self, user_id: str, user_name: str, group_code: str, meeting_place: str):
        """Обновить статус после взятия МП во всех каналах"""
        self.taken = True
        for child in self.children:
            child.disabled = True
        
        # Получаем роли для оповещений
        announce_roles = CONFIG.get('announce_roles', [])
        role_mentions = []
        for role_id in announce_roles:
            role = self.guild.get_role(int(role_id))
            if role:
                role_mentions.append(role.mention)
        
        content = ' '.join(role_mentions) if role_mentions else None
        
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
        
        # Обновляем все сообщения во всех каналах
        await self.update_all_messages(embed)
    
    async def on_timeout(self):
        """Когда время вышло (за 10 минут до начала)"""
        self.timeout_occurred = True
        if not self.taken and self.messages:
            # Отключаем все кнопки
            for child in self.children:
                child.disabled = True
            
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
            
            # Обновляем все сообщения
            await self.update_all_messages(embed)


class EventInfoView(BaseMenuView):
    """Кнопка информации о мероприятии в !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        # Создаём кнопку динамически
        self.add_item(self.create_today_button())
    
    def create_today_button(self):
        """Создать кнопку 'Мероприятия сегодня'"""
        btn = discord.ui.Button(
            label="📅 Мероприятия сегодня", 
            style=discord.ButtonStyle.primary, 
            emoji="📅"
        )
        
        async def callback(interaction: discord.Interaction):
            # При нажатии сразу убираем кнопку
            self.clear_items()
            self.add_back_button()
            
            await self.show_today_events(interaction)
        
        btn.callback = callback
        return btn
    
    async def show_today_events(self, interaction: discord.Interaction):
        """Показать мероприятия на сегодня"""
        try:
            today = datetime.now(MSK_TZ).date()
            weekday = today.weekday()
            now = datetime.now(MSK_TZ)
            current_time_str = now.strftime("%H:%M")
            
            # Получаем все мероприятия на сегодня
            events = db.get_events(enabled_only=True, weekday=weekday)
            
            if not events:
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
                event_time = event['event_time']
                event_hour, event_min = map(int, event_time.split(':'))
                reminder_time = f"{event_hour-1:02d}:{event_min:02d}" if event_hour > 0 else f"23:{event_min:02d}"
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT taken_by, group_code, meeting_place, reminder_sent 
                        FROM event_schedule 
                        WHERE event_id = ? AND scheduled_date = ?
                    ''', (event['id'], today.isoformat()))
                    result = cursor.fetchone()
                
                # Определяем статус
                if result and result[0]:  # Взято
                    status = f"✅ **Проводит:** <@{result[0]}>\n📍 {result[2]}\n🔢 {result[1]}"
                else:
                    if current_time_str >= event_time:
                        status = "⌛ **Мероприятие уже идёт или прошло**"
                    elif current_time_str >= reminder_time:
                        # Напоминание уже пришло
                        status = "⏳ **Ожидаем информацию от HIGH состава**"
                    else:
                        # Напоминание ещё не пришло
                        status = "🕒 **Будет проводиться позже**"
                
                embed.add_field(
                    name=f"{event_time} — {event['name']}",
                    value=status,
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            file_logger.error(f"Ошибка в show_today_events: {e}")
            await interaction.response.edit_message(
                content=f"❌ Ошибка при загрузке мероприятий",
                embed=None,
                view=self
            )