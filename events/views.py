"""Кнопки для системы мероприятий"""
import discord
import asyncio
from datetime import datetime
from core.database import db
from events.base import PermanentView
from events.manager import events_manager


class EventsParticipantView(PermanentView):
    """Публичные кнопки для участников с обновлением времени"""
    
    def __init__(self, session_id: int, collect_minutes: int):
        super().__init__()
        self.session_id = session_id
        self.message = None
        self.collect_minutes = collect_minutes
        self.remaining_minutes = collect_minutes
        self.update_task = None
    
    def set_message(self, message):
        self.message = message
    
    async def start_timer(self):
        """Запускает обновление времени каждую минуту"""
        async def timer_loop():
            while self.remaining_minutes > 0:
                await asyncio.sleep(60)
                self.remaining_minutes -= 1
                await self.update_message()
            
            # Время вышло - отключаем кнопки
            await self.disable_buttons()
        
        self.update_task = asyncio.create_task(timer_loop())
    
    async def update_message(self):
        """Обновляет сообщение с новым временем и списком участников"""
        if not self.message:
            return
        
        session = events_manager.get_session(self.session_id)
        if not session or session['status'] != 'active':
            return
        
        participants = events_manager.get_participants(self.session_id)
        event_name = session.get('event_name', 'Мероприятие')
        meeting_place = session.get('meeting_place', 'Не указано')
        creator_id = session.get('creator_id')
        
        # Формируем обновлённое сообщение
        content = (
            f"@everyone\n"
            f"**ВНИМАНИЕ, СБОР!**\n\n"
            f"Собирает: <@{creator_id}> на **{event_name}**\n"
            f"📍 Место сбора: {meeting_place}\n"
            f"⏱️ Осталось времени: **{self.remaining_minutes} мин.**\n"
        )
        if session.get('additional_info'):
            content += f"📝 {session['additional_info']}\n"
        
        # Список участников
        if participants:
            content += f"\n**Участники ({len(participants)}):**\n"
            for p in participants:
                uid = p if isinstance(p, str) else p.get('user_id')
                content += f"└ <@{uid}>\n"
        else:
            content += f"\n**Участники (0):**\n"
            content += "└ *Пока никого нет*"
        
        await self.message.edit(content=content)
    
    async def disable_buttons(self):
        """Отключает кнопки по истечению времени"""
        if not self.message:
            return
        
        # Отключаем все кнопки в сообщении
        for child in self.message.components[0].children:
            child.disabled = True
        await self.message.edit(view=self.message.components[0])
        
        # Завершаем сессию
        session = events_manager.get_session(self.session_id)
        if session and session['status'] == 'active':
            participants = events_manager.get_participants(self.session_id)
            db.finalize_event_participants(self.session_id, participants)
            events_manager.end_session(self.session_id)
            
            await events_manager.log_action(
                self.session_id,
                f"⏰ Сбор завершён. Участников: {len(participants)}"
            )
    
    @discord.ui.button(label="✅ ПРИСОЕДИНИТЬСЯ", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = events_manager.get_session(self.session_id)
        if not session or session['status'] != 'active':
            await interaction.response.send_message("❌ Мероприятие уже завершено", ephemeral=True)
            return
        
        success = events_manager.add_participant(
            self.session_id,
            str(interaction.user.id),
            interaction.user.display_name
        )
        
        if success:
            await interaction.response.send_message("✅ Вы присоединились к сбору!", ephemeral=True)
            await self.update_message()
        else:
            await interaction.response.send_message("❌ Вы уже в списке участников", ephemeral=True)
    
    @discord.ui.button(label="❌ ОТСОЕДИНИТЬСЯ", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = events_manager.get_session(self.session_id)
        if not session or session['status'] != 'active':
            await interaction.response.send_message("❌ Мероприятие уже завершено", ephemeral=True)
            return
        
        success = events_manager.remove_participant(self.session_id, str(interaction.user.id))
        
        if success:
            await interaction.response.send_message("✅ Вы отсоединились от сбора", ephemeral=True)
            await self.update_message()
        else:
            await interaction.response.send_message("❌ Вы не были в списке участников", ephemeral=True)