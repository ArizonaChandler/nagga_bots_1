"""Кнопки для системы мероприятий"""
import discord
from datetime import datetime
from core.database import db
from events.base import PermanentView
from events.manager import events_manager


class EventsModerationView(discord.ui.View):
    
    def __init__(self, session_id: int):
        super().__init__(timeout=None)
        self.session_id = session_id
    
    @discord.ui.button(label="📊 Статистика", style=discord.ButtonStyle.secondary, emoji="📊", row=0)
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        embed.add_field(name="📌 Название", value=session.get('event_name', 'Не указано'), inline=True)
        embed.add_field(name="👤 Организатор", value=f"<@{session['creator_id']}>", inline=True)
        embed.add_field(name="⏰ Сбор в", value=session['event_time'], inline=True)
        embed.add_field(name="📍 Место", value=session.get('meeting_place', 'Не указано'), inline=True)
        embed.add_field(name="👥 Участников", value=f"**{len(participants)}**", inline=True)
        
        if participants:
            users = [p['user_id'] if isinstance(p, dict) else p for p in participants]
            embed.add_field(
                name="📋 Список участников",
                value="\n".join([f"• <@{uid}>" for uid in users[:20]]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="⏹️ ЗАВЕРШИТЬ", style=discord.ButtonStyle.danger, emoji="⏹️", row=0)
    async def end_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = events_manager.get_session(self.session_id)
        if not session:
            await interaction.response.send_message("❌ Сессия не найдена", ephemeral=True)
            return
        
        participants = events_manager.get_participants(self.session_id)
        db.finalize_event_participants(self.session_id, participants)
        events_manager.end_session(self.session_id)
        
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        await events_manager.log_action(
            self.session_id,
            f"⏹️ Сессия завершена досрочно модератором {interaction.user.mention}. Участников: {len(participants)}"
        )
        
        await interaction.response.send_message("✅ Сессия завершена", ephemeral=True)


class EventsParticipantView(PermanentView):
    
    def __init__(self, session_id: int):
        super().__init__()
        self.session_id = session_id
        self.message = None
    
    def set_message(self, message):
        self.message = message
    
    async def update_participants_list(self, interaction: discord.Interaction = None):
        participants = events_manager.get_participants(self.session_id)
        
        session = events_manager.get_session(self.session_id)
        if not session:
            return
        
        event_name = session.get('event_name', 'Мероприятие')
        meeting_place = session.get('meeting_place', 'Не указано')
        
        content = f"@everyone **🎯 МЕРОПРИЯТИЕ!**\n\n"
        content += f"📌 **{event_name}**\n"
        content += f"👤 Организатор: <@{session['creator_id']}>\n"
        content += f"⏰ Сбор в: {session['event_time']} МСК\n"
        content += f"📍 Место: {meeting_place}\n"
        if session.get('additional_info'):
            content += f"📝 {session['additional_info']}\n"
        content += f"\n**Участники ({len(participants)}):**\n"
        
        if participants:
            for p in participants:
                uid = p if isinstance(p, str) else p.get('user_id')
                content += f"└ <@{uid}>\n"
        else:
            content += "└ *Пока никого нет*"
        
        if self.message:
            await self.message.edit(content=content)
    
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
            await interaction.response.send_message("✅ Вы присоединились к мероприятию!", ephemeral=True)
            await self.update_participants_list(interaction)
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
            await interaction.response.send_message("✅ Вы отсоединились от мероприятия", ephemeral=True)
            await self.update_participants_list(interaction)
        else:
            await interaction.response.send_message("❌ Вы не были в списке участников", ephemeral=True)