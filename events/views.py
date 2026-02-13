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
        super().__init__(timeout=2400)
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
                # Обновляем embed с информацией кто взял
                embed = self.message.embeds[0]
                embed.set_field_at(2, name="👥 Статус", value=f"✅ Взял: <@{result[0]}>", inline=False)
                await self.message.edit(embed=embed, view=self)
                await interaction.response.send_message(f"❌ Уже взял <@{result[0]}>", ephemeral=True)
                return
        
        from admin.modals import TakeEventModal
        modal = TakeEventModal(self.event_id, self.event_name, self.event_time, self.meeting_time)
        await interaction.response.send_modal(modal)
    
    async def update_taken_status(self, user_id: str, user_name: str):
        """Обновить статус после взятия МП"""
        self.taken = True
        for child in self.children:
            child.disabled = True
        
        if self.message:
            embed = self.message.embeds[0]
            embed.title = f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}"
            embed.description = f"Мероприятие проведёт: <@{user_id}>"
            embed.color = 0x00ff00
            embed.set_field_at(2, name="👥 Статус", value=f"✅ Взял: <@{user_id}>", inline=False)
            embed.set_footer(text="Unit Management System by Nagga")
            await self.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        if not self.taken and self.message:
            for child in self.children:
                child.disabled = True
            embed = self.message.embeds[0]
            embed.color = 0xff0000
            embed.set_footer(text="⏰ Время на взятие МП истекло")
            await self.message.edit(embed=embed, view=self)

class EventInfoView(BaseMenuView):
    """Кнопка информации о мероприятии в !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        self.add_item(self.create_button())
    
    def create_button(self):
        btn = discord.ui.Button(label="📅 Мероприятия сегодня", style=discord.ButtonStyle.primary, emoji="📅")
        async def callback(interaction: discord.Interaction, button: discord.ui.Button):
            await self.today_events(interaction, button)
        btn.callback = callback
        return btn
    
    async def today_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        today = datetime.now(MSK_TZ).date()
        weekday = today.weekday()
        
        events = db.get_events(enabled_only=True, weekday=weekday)
        
        if not events:
            # Убираем кнопку и показываем сообщение
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
                event_time = event['event_time']
                event_dt = datetime.strptime(event_time, "%H:%M")
                reminder_time = event_dt - timedelta(hours=1)
                now_time = datetime.now(MSK_TZ).time()
                
                if now_time > reminder_time.time() and now_time < event_dt.time():
                    status = "⏳ **Можно взять** (40 мин)"
                elif now_time > event_dt.time():
                    status = "❌ **Прошло**"
                else:
                    status = "❌ **Свободно**"
            
            embed.add_field(
                name=f"{event['event_time']} — {event['name']}",
                value=status,
                inline=False
            )
        
        # Убираем кнопку "Мероприятия сегодня" после нажатия
        self.clear_items()
        self.add_back_button()
        await interaction.response.edit_message(embed=embed, view=self)