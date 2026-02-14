"""Event Views - Кнопки для мероприятий (ОДНО ОКНО)"""
import discord
from datetime import datetime, timedelta
import pytz
from core.database import db
from core.config import CONFIG
from core.menus import BaseMenuView  # Импорт из core.menus
from admin.modals import TakeEventModal

MSK_TZ = pytz.timezone('Europe/Moscow')

class EventReminderView(discord.ui.View):
    """Кнопка 'Взять МП' в напоминании"""
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str, guild):
        # Вычисляем таймаут: до времени начала минус 10 минут
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        
        # Парсим время мероприятия (работаем со строками, не с datetime)
        event_hour, event_min = map(int, event_time.split(':'))
        
        # Создаем datetime для времени мероприятия today
        event_datetime = msk_tz.localize(datetime(
            now.year, now.month, now.day,
            event_hour, event_min
        ))
        
        # Если мероприятие уже сегодня, но время прошло - добавляем день
        if event_datetime < now:
            event_datetime += timedelta(days=1)
        
        # Вычисляем время таймаута (за 10 минут до начала)
        timeout_datetime = event_datetime - timedelta(minutes=10)
        timeout_seconds = max(0, (timeout_datetime - now).total_seconds())
        
        super().__init__(timeout=timeout_seconds)
        
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        self.guild = guild
        self.taken = False
        self.message = None
    
    @discord.ui.button(label="🎮 ВЗЯТЬ МП", style=discord.ButtonStyle.success, emoji="🎮")
    async def take_event(self, interaction: discord.Interaction, button: discord.ui.Button):
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
                embed = self.message.embeds[0]
                embed.title = f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}"
                embed.description = f"Мероприятие проведёт: <@{result[0]}>"
                embed.color = 0x00ff00
                
                # Обновляем поля
                new_embed = discord.Embed(
                    title=embed.title,
                    description=embed.description,
                    color=embed.color
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
        
        # Открываем модалку с передачей ссылки на этот view
        from admin.modals import TakeEventModal
        modal = TakeEventModal(
            self.event_id, 
            self.event_name, 
            self.event_time, 
            self.meeting_time,
            self  # Передаем ссылку на текущий view
        )
        await interaction.response.send_modal(modal)
    
    async def update_taken_status(self, user_id: str, user_name: str, group_code: str, meeting_place: str):
        """Мгновенно обновить статус после взятия МП"""
        self.taken = True
        for child in self.children:
            child.disabled = True
        
        if self.message:
            # Создаём новый embed с обновлённой информацией
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
            
            await self.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        """Когда время вышло (за 10 минут до начала)"""
        if not self.taken and self.message:
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
        today = datetime.now(MSK_TZ).date()
        weekday = today.weekday()
        
        # Получаем все мероприятия на сегодня (включая прошедшие)
        events = db.get_events(enabled_only=True, weekday=weekday)
        
        if not events:
            await interaction.response.edit_message(
                content="📅 На сегодня мероприятий нет",
                embed=None,
                view=self
            )
            return
        
        # Фильтруем только будущие мероприятия
        now = datetime.now(MSK_TZ).time()
        future_events = []
        
        for event in events:
            event_time = datetime.strptime(event['event_time'], "%H:%M").time()
            # Показываем только мероприятия, которые ещё не начались
            if event_time >= now:
                future_events.append(event)
        
        if not future_events:
            await interaction.response.edit_message(
                content="📅 На сегодня все мероприятия уже прошли",
                embed=None,
                view=self
            )
            return
        
        embed = discord.Embed(
            title=f"📅 МЕРОПРИЯТИЯ НА СЕГОДНЯ ({today.strftime('%d.%m.%Y')})",
            color=0x7289da
        )
        
        for event in future_events:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT taken_by, group_code, meeting_place FROM event_schedule 
                    WHERE event_id = ? AND scheduled_date = ?
                ''', (event['id'], today.isoformat()))
                result = cursor.fetchone()
            
            if result and result[0]:
                status = f"✅ **Взял:** <@{result[0]}>\n📍 {result[2]}\n🔢 {result[1]}"
            else:
                status = "❌ **Свободно**"
            
            embed.add_field(
                name=f"{event['event_time']} — {event['name']}",
                value=status,
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)