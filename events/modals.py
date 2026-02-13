"""Event Modals - Дополнительные модальные окна"""
import discord
from datetime import datetime
import pytz
from core.database import db
from core.utils import is_admin

MSK_TZ = pytz.timezone('Europe/Moscow')

class ScheduleEventModal(discord.ui.Modal, title="📅 ЗАПЛАНИРОВАТЬ РАЗОВОЕ МЕРОПРИЯТИЕ"):
    """Для разовых мероприятий вне расписания"""
    event_name = discord.ui.TextInput(
        label="Название мероприятия",
        placeholder="Штурм, Каньон, ГГ",
        max_length=100
    )
    
    event_date = discord.ui.TextInput(
        label="Дата (ДД.ММ.ГГГГ)",
        placeholder="25.12.2026",
        max_length=10
    )
    
    event_time = discord.ui.TextInput(
        label="Время (ЧЧ:ММ)",
        placeholder="19:30",
        max_length=5
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            date_obj = datetime.strptime(self.event_date.value, "%d.%m.%Y")
            weekday = date_obj.weekday()
            date_iso = date_obj.date().isoformat()
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", ephemeral=True)
            return
        
        try:
            datetime.strptime(self.event_time.value, "%H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)
            return
        
        # Проверяем дату (не в прошлом)
        if date_obj.date() < datetime.now(MSK_TZ).date():
            await interaction.response.send_message("❌ Нельзя создать мероприятие в прошлом", ephemeral=True)
            return
        
        # Создаём временное мероприятие
        event_id = db.add_event(
            name=f"[РАЗОВОЕ] {self.event_name.value}",
            weekday=weekday,
            event_time=self.event_time.value,
            created_by=str(interaction.user.id)
        )
        
        # Добавляем в расписание на конкретную дату
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO event_schedule 
                (event_id, scheduled_date, reminder_sent)
                VALUES (?, ?, 0)
            ''', (event_id, date_iso))
            conn.commit()
        
        db.log_event_action(event_id, "scheduled", str(interaction.user.id),
                           f"Разовое на {self.event_date.value} {self.event_time.value}")
        
        await interaction.response.send_message(
            f"✅ Разовое мероприятие запланировано на {self.event_date.value} в {self.event_time.value}",
            ephemeral=True
        )