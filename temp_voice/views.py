"""Кнопки для системы временных комнат"""
import discord
from temp_voice.base import PermanentView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal, SetSlotsModal, KickUserModal


class TempVoicePublicView(PermanentView):
    """Публичные кнопки для создания и управления комнатами"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="🎤 СОЗДАТЬ КОМНАТУ",
        style=discord.ButtonStyle.success,
        emoji="🎤",
        row=0,
        custom_id="temp_voice_create"
    )
    async def create_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        existing = temp_voice_manager.get_user_room(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CreateRoomModal())
    
    @discord.ui.button(
        label="⚙️ УСТАНОВИТЬ СЛОТЫ",
        style=discord.ButtonStyle.primary,
        emoji="⚙️",
        row=1,
        custom_id="temp_voice_set_slots"
    )
    async def set_slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nСначала создайте комнату кнопкой 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Ваша комната не найдена", ephemeral=True)
            return
        
        settings = temp_voice_manager.get_settings()
        max_slots = settings.get('temp_voice_max_slots', 10)
        
        modal = SetSlotsModal(channel.id, room['slots'], max_slots)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🔒 ЗАБЛОКИРОВАТЬ",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        row=2,
        custom_id="temp_voice_lock"
    )
    async def lock_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nСначала создайте комнату кнопкой 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Ваша комната не найдена", ephemeral=True)
            return
        
        success, msg = await temp_voice_manager.lock_room(interaction, channel)
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(
        label="🔓 РАЗБЛОКИРОВАТЬ",
        style=discord.ButtonStyle.success,
        emoji="🔓",
        row=2,
        custom_id="temp_voice_unlock"
    )
    async def unlock_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nСначала создайте комнату кнопкой 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Ваша комната не найдена", ephemeral=True)
            return
        
        success, msg = await temp_voice_manager.unlock_room(interaction, channel)
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(
        label="👢 КИКНУТЬ",
        style=discord.ButtonStyle.danger,
        emoji="👢",
        row=3,
        custom_id="temp_voice_kick"
    )
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nСначала создайте комнату кнопкой 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Ваша комната не найдена", ephemeral=True)
            return
        
        if not channel.members or len(channel.members) == 1:
            await interaction.response.send_message("❌ В комнате никого нет, кроме вас", ephemeral=True)
            return
        
        modal = KickUserModal(channel.id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🗑️ УДАЛИТЬ КОМНАТУ",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        row=3,
        custom_id="temp_voice_delete"
    )
    async def delete_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nСначала создайте комнату кнопкой 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Ваша комната не найдена", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        await temp_voice_manager.close_room(interaction, channel)
        await interaction.followup.send("✅ Комната удалена", ephemeral=True)