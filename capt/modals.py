"""Модальное окно для CAPT"""
import discord
from core.database import db
from core.config import CONFIG
from core.utils import has_access
from capt.core import capt_core

class CaptModal(discord.ui.Modal, title="🚨 СОЗДАНИЕ ОБЩЕГО СБОРА"):
    time_input = discord.ui.TextInput(
        label="⏰ Время сбора (ЧЧ:ММ)",
        placeholder="19:30",
        max_length=5
    )
    message_input = discord.ui.TextInput(
        label="📝 Дополнительное сообщение",
        placeholder="Сбор у телепорта!",
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await has_access(str(interaction.user.id)):
            await interaction.response.send_message("❌ У вас нет доступа", ephemeral=True)
            return
        
        if not CONFIG['capt_role_id'] or not CONFIG['capt_channel_id']:
            await interaction.response.send_message("❌ CAPT не настроен", ephemeral=True)
            return
        
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Только на сервере", ephemeral=True)
            return
        
        role = guild.get_role(int(CONFIG['capt_role_id']))
        if not role:
            await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
            return
        
        members = [m for m in guild.members if role in m.roles]
        if not members:
            await interaction.response.send_message("⚠️ Нет участников с этой ролью", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"🚀 **CAPT** | {len(members)} участников | ⚡ Запуск...",
            ephemeral=False
        )
        
        await capt_core.send_bulk(interaction, members, self.time_input.value, self.message_input.value)