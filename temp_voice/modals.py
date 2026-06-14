"""Модальные окна для системы временных комнат"""
import discord
from temp_voice.manager import temp_voice_manager


class CreateRoomModal(discord.ui.Modal, title="🎤 СОЗДАНИЕ КОМНАТЫ"):
    room_name = discord.ui.TextInput(
        label="Название комнаты",
        placeholder="Например: Комната Нагги",
        max_length=32,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        success, msg = await temp_voice_manager.create_room(interaction, self.room_name.value)
        await interaction.response.send_message(msg, ephemeral=True)


class KickUserModal(discord.ui.Modal, title="👢 КИКНУТЬ ПОЛЬЗОВАТЕЛЯ"):
    user_mention = discord.ui.TextInput(
        label="Упоминание пользователя",
        placeholder="@username",
        max_length=100,
        required=True
    )
    
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = None
        for word in self.user_mention.value.split():
            if word.startswith('<@') and word.endswith('>'):
                user_id = int(word.strip('<@!>'))
                break
        
        if not user_id:
            await interaction.response.send_message(
                "❌ Неверный формат. Используйте упоминание пользователя (например @username)",
                ephemeral=True
            )
            return
        
        target = interaction.guild.get_member(user_id)
        if not target:
            await interaction.response.send_message("❌ Пользователь не найден на сервере", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return
        
        success, msg = await temp_voice_manager.kick_user(interaction, channel, target)
        await interaction.response.send_message(msg, ephemeral=True)