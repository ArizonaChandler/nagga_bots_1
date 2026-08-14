"""Кнопки для системы мероприятий"""
import discord
from datetime import datetime
from events.base import PermanentView
from events.manager import events_manager
from events.modals import CreateEventModal
from events.templates import get_event_templates, format_templates_for_select


class EventsModerationView(discord.ui.View):
    """Кнопки для модерации мероприятия"""
    
    def __init__(self, session_id: int):
        super().__init__(timeout=None)
        self.session_id = session_id
    
    @discord.ui.button(label="📊 Статистика", style=discord.ButtonStyle.secondary, emoji="📊", row=0)
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать статистику сессии"""
        session = events_manager.get_session(self.session_id)
        if not session:
            await interaction.response.send_message("❌ Сессия не найдена", ephemeral=True)
            return
        
        participants = events_manager.get_participants(self.session_id)
        
        embed = discord.Embed(
            title=f"📊 СТАТИСТИКА СЕССИИ #{self.session_id}",
            color=0x00bfff,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Организатор", value=f"<@{session['creator_id']}>", inline=True)
        embed.add_field(name="⏰ Время начала", value=session['event_time'], inline=True)
        embed.add_field(name="👥 Участников", value=f"**{len(participants)}**", inline=True)
        
        if participants:
            embed.add_field(
                name="📋 Список участников",
                value="\n".join([f"• <@{uid}>" for uid in participants[:20]]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="⏹️ ЗАВЕРШИТЬ", style=discord.ButtonStyle.danger, emoji="⏹️", row=0)
    async def end_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Завершить сессию досрочно"""
        session = events_manager.get_session(self.session_id)
        if not session:
            await interaction.response.send_message("❌ Сессия не найдена", ephemeral=True)
            return
        
        # Сохраняем участников
        participants = events_manager.get_participants(self.session_id)
        db.finalize_event_participants(self.session_id, participants)
        
        events_manager.end_session(self.session_id)
        
        # Отключаем кнопки
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        await events_manager.log_action(
            self.session_id,
            f"⏹️ Сессия завершена досрочно модератором {interaction.user.mention}. Участников: {len(participants)}"
        )
        
        await interaction.response.send_message("✅ Сессия завершена", ephemeral=True)


class EventsParticipantView(PermanentView):
    """Публичные кнопки для участников"""
    
    def __init__(self, session_id: int):
        super().__init__()
        self.session_id = session_id
        self.message = None
    
    def set_message(self, message):
        self.message = message
    
    async def update_participants_list(self, interaction: discord.Interaction):
        """Обновить текстовый список участников"""
        participants = events_manager.get_participants(self.session_id)
        
        session = events_manager.get_session(self.session_id)
        if not session:
            return
        
        content = f"@everyone **🎯 МЕРОПРИЯТИЕ!**\n\n"
        content += f"👤 Организатор: <@{session['creator_id']}>\n"
        content += f"⏰ Начало: {session['event_time']} МСК\n"
        if session.get('additional_info'):
            content += f"📝 {session['additional_info']}\n"
        content += f"\n**Участники ({len(participants)}):**\n"
        
        if participants:
            for uid in participants:
                content += f"└ <@{uid}>\n"
        else:
            content += "└ *Пока никого нет*"
        
        # Обновляем сообщение
        if self.message:
            await self.message.edit(content=content)
    
    @discord.ui.button(label="✅ ПРИСОЕДИНИТЬСЯ", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Присоединиться к мероприятию"""
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
            await interaction.response.send_message("✅ Вы присоединились к мероприятию!", ephemeral=True)
            await self.update_participants_list(interaction)
        else:
            await interaction.response.send_message("❌ Вы уже в списке участников", ephemeral=True)
    
    @discord.ui.button(label="❌ ОТСОЕДИНИТЬСЯ", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отсоединиться от мероприятия"""
        session = events_manager.get_session(self.session_id)
        if not session or session['status'] != 'active':
            await interaction.response.send_message("❌ Мероприятие уже завершено", ephemeral=True)
            return
        
        success = events_manager.remove_participant(self.session_id, str(interaction.user.id))
        
        if success:
            await interaction.response.send_message("✅ Вы отсоединились от мероприятия", ephemeral=True)
            await self.update_participants_list(interaction)
        else:
            await interaction.response.send_message("❌ Вы не были в списке участников", ephemeral=True)