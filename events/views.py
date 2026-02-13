"""Event Views - Кнопки для мероприятий"""
import discord
from datetime import datetime, timedelta
import pytz
from core.database import db
from core.config import CONFIG
from admin.modals import TakeEventModal

MSK_TZ = pytz.timezone('Europe/Moscow')

class EventReminderView(discord.ui.View):
    """Кнопка 'Взять МП' в напоминании"""
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str, guild):
        super().__init__(timeout=2400)  # 40 минут в секундах
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time  # НОВОЕ: время сбора
        self.guild = guild
        self.taken = False
        self.message = None  # для сохранения сообщения
    
    @discord.ui.button(label="🎮 ВЗЯТЬ МП", style=discord.ButtonStyle.success, emoji="🎮")
    async def take_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.taken:
            await interaction.response.send_message(
                "❌ Это мероприятие уже кто-то взял",
                ephemeral=True
            )
            return
        
        # Проверяем, не взято ли уже
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
                await interaction.message.edit(view=self)
                await interaction.response.send_message(
                    f"❌ Мероприятие уже взял <@{result[0]}>",
                    ephemeral=True
                )
                return
        
        # Открываем модалку с временем сбора
        modal = TakeEventModal(
            self.event_id, 
            self.event_name, 
            self.event_time,
            self.meeting_time  # НОВОЕ: передаём время сбора
        )
        await interaction.response.send_modal(modal)
    
    async def on_timeout(self):
        """НОВОЕ: Когда прошло 40 минут и кнопка стала неактивной"""
        if not self.taken:
            # Отключаем кнопку
            for child in self.children:
                child.disabled = True
            
            # Обновляем сообщение
            if self.message:
                embed = self.message.embeds[0]
                embed.color = 0xff0000
                embed.set_footer(text="⏰ Время на взятие МП истекло")
                
                await self.message.edit(embed=embed, view=self)


class EventInfoView(discord.ui.View):
    """Кнопка информации о мероприятии в !info"""
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="📅 Мероприятия сегодня", style=discord.ButtonStyle.primary, emoji="📅")
    async def today_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        today = datetime.now(MSK_TZ).date()
        weekday = today.weekday()
        
        events = db.get_events(enabled_only=True, weekday=weekday)
        
        if not events:
            await interaction.response.send_message(
                "📅 На сегодня мероприятий нет",
                ephemeral=True
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
                status = f"✅ **Взял:** <@{result[0]}>\n"
                status += f"📍 **Сбор:** {result[2]}\n"
                status += f"🔢 **Код:** {result[1]}"
            else:
                # Проверяем, не истекло ли время взятия
                event_time = event['event_time']
                event_dt = datetime.strptime(event_time, "%H:%M")
                reminder_time = event_dt - timedelta(hours=1)
                now_time = datetime.now(MSK_TZ).time()
                
                if now_time > reminder_time.time() and now_time < event_dt.time():
                    status = "⏳ **Можно взять** (есть 40 минут)"
                elif now_time > event_dt.time():
                    status = "❌ **Прошло**"
                else:
                    status = "❌ **Свободно**"
            
            embed.add_field(
                name=f"{event['event_time']} — {event['name']}",
                value=status,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)