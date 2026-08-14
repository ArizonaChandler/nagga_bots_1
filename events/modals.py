"""Модальные окна для системы мероприятий"""
import discord
import re
from events.manager import events_manager
from events.templates import get_event_templates, format_templates_for_select


class CreateEventModal(discord.ui.Modal, title="🎯 СОЗДАНИЕ МЕРОПРИЯТИЯ"):
    
    event_time = discord.ui.TextInput(
        label="⏰ Время начала (МСК)",
        placeholder="19:30",
        max_length=5,
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
        placeholder="Место сбора, код группы и т.д.",
        max_length=500,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, templates: list):
        super().__init__()
        self.templates = templates
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверка времени
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.event_time.value):
            await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
            return
        
        # Проверка времени сбора
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
        
        # Проверяем, выбран ли шаблон
        if not hasattr(self, 'selected_template_id') or not self.selected_template_id:
            await interaction.response.send_message("❌ Выберите шаблон мероприятия", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Создаём сессию
        session_id = events_manager.create_session(
            creator_id=str(interaction.user.id),
            template_id=self.selected_template_id,
            collect_time=collect_minutes,
            channel_id=str(interaction.channel.id),
            message_id="",
            event_time=self.event_time.value
        )
        
        # Отправляем в канал модерации
        await self._send_to_moderation(interaction, session_id)
        
        # Отправляем в канал сбора
        await self._send_to_participants(interaction, session_id, collect_minutes)
        
        await interaction.followup.send(
            f"✅ Мероприятие создано!\n"
            f"⏰ Начало: {self.event_time.value}\n"
            f"⏱️ Сбор: {collect_minutes} минут",
            ephemeral=True
        )
    
    async def _send_to_moderation(self, interaction, session_id: int):
        """Отправить информацию в канал модерации"""
        settings = events_manager.get_settings()
        channel_id = settings.get('events_moderation_channel')
        if not channel_id:
            return
        
        channel = interaction.client.get_channel(int(channel_id))
        if not channel:
            return
        
        embed = discord.Embed(
            title="🎯 НОВОЕ МЕРОПРИЯТИЕ",
            color=0x00bfff,
            timestamp=datetime.now()
        )
        embed.add_field(name="🆔 ID сессии", value=f"`{session_id}`", inline=True)
        embed.add_field(name="👤 Организатор", value=interaction.user.mention, inline=True)
        embed.add_field(name="⏰ Время начала", value=self.event_time.value, inline=True)
        embed.add_field(name="⏱️ Время на сбор", value=f"{collect_minutes} мин", inline=True)
        if self.additional_info.value:
            embed.add_field(name="📝 Дополнительно", value=self.additional_info.value, inline=False)
        
        # Кнопки управления для модераторов
        view = EventsModerationView(session_id)
        await channel.send(embed=embed, view=view)
    
    async def _send_to_participants(self, interaction, session_id: int, collect_minutes: int):
        """Отправить сообщение в канал сбора участников"""
        settings = events_manager.get_settings()
        channel_id = settings.get('events_participant_channel')
        if not channel_id:
            return
        
        channel = interaction.client.get_channel(int(channel_id))
        if not channel:
            return
        
        # Текстовое сообщение с информацией о МП
        content = f"@everyone **🎯 МЕРОПРИЯТИЕ!**\n\n"
        content += f"👤 Организатор: {interaction.user.mention}\n"
        content += f"⏰ Начало: {self.event_time.value} МСК\n"
        content += f"⏱️ Сбор: {collect_minutes} минут\n"
        if self.additional_info.value:
            content += f"📝 {self.additional_info.value}\n"
        content += f"\n**Участники:**\n"
        content += "└ *Пока никого нет*"
        
        view = EventsParticipantView(session_id)
        sent_message = await channel.send(content=content, view=view)
        
        # Сохраняем ID сообщения
        db.update_event_session_message(session_id, str(sent_message.id))
        
        # Запускаем таймер сбора
        await events_manager.start_collect_timer(
            session_id, 
            collect_minutes,
            str(channel.id),
            str(sent_message.id)
        )