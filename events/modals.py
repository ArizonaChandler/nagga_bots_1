"""Модальные окна для системы мероприятий"""
import discord
import re
from datetime import datetime
from core.database import db
from events.manager import events_manager
from events.views import EventsParticipantView


class CreateEventModal(discord.ui.Modal, title="🎯 СОЗДАНИЕ МЕРОПРИЯТИЯ"):
    
    event_name = discord.ui.TextInput(
        label="📌 Название мероприятия",
        placeholder="Например: Арена перед каптами",
        max_length=100,
        required=True
    )
    
    event_time = discord.ui.TextInput(
        label="⏰ Время начала (МСК)",
        placeholder="19:30",
        max_length=5,
        required=True
    )
    
    meeting_place = discord.ui.TextInput(
        label="📍 Место сбора",
        placeholder="У банка, аэропорт, мэрия",
        max_length=200,
        required=True
    )
    
    collect_time = discord.ui.TextInput(
        label="⏱️ Время на сбор (минуты)",
        placeholder="20",
        max_length=3,
        required=False
    )
    
    additional_info = discord.ui.TextInput(
        label="📝 Дополнительная информация",
        placeholder="Код группы, особые указания и т.д.",
        max_length=500,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.event_time.value):
            await interaction.response.send_message("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)
            return
        
        collect_minutes = 20
        if self.collect_time.value:
            try:
                collect_minutes = int(self.collect_time.value)
                if collect_minutes < 1:
                    await interaction.response.send_message("❌ Время сбора должно быть больше 0", ephemeral=True)
                    return
                if collect_minutes > 120:
                    await interaction.response.send_message("❌ Время сбора не может превышать 120 минут", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Введите число", ephemeral=True)
                return
        
        await interaction.response.defer(ephemeral=True)
        
        session_id = events_manager.create_session(
            creator_id=str(interaction.user.id),
            collect_time=collect_minutes,
            channel_id=str(interaction.channel.id),
            message_id="",
            event_time=self.event_time.value,
            event_name=self.event_name.value,
            meeting_place=self.meeting_place.value,
            additional_info=self.additional_info.value
        )
        
        await self._send_to_participants(interaction, session_id, collect_minutes)
        
        await interaction.followup.send(
            f"✅ Мероприятие **{self.event_name.value}** создано!\n"
            f"⏰ Начало в: {self.event_time.value}\n"
            f"📍 Место: {self.meeting_place.value}\n"
            f"⏱️ Сбор длится: {collect_minutes} минут",
            ephemeral=True
        )
    
    async def _send_to_participants(self, interaction, session_id: int, collect_minutes: int):
        settings = events_manager.get_settings()
        channel_id = settings.get('events_participant_channel')
        if not channel_id:
            return
        
        channel = interaction.client.get_channel(int(channel_id))
        if not channel:
            return
        
        content = (
            f"@everyone\n"
            f"**ВНИМАНИЕ, СБОР!**\n\n"
            f"Собирает: {interaction.user.mention} на **{self.event_name.value}**\n"
            f"📍 Место сбора: {self.meeting_place.value}\n"
            f"⏱️ Осталось времени: **{collect_minutes} мин.**\n"
            f"⏰ Начало в: {self.event_time.value}\n"
        )
        if self.additional_info.value:
            content += f"📝 {self.additional_info.value}\n"
        
        view = EventsParticipantView(session_id, collect_minutes)
        sent_message = await channel.send(content=content, view=view)
        view.set_message(sent_message)
        
        db.update_event_session_message(session_id, str(sent_message.id))
        
        await view.start_timer()