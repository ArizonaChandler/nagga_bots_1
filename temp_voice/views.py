"""Кнопки для системы временных комнат"""
import discord
from temp_voice.base import PermanentView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal, KickUserModal, ExpandSlotsModal


class TempVoicePublicView(PermanentView):
    """Публичные кнопки для создания и управления комнатами (ВСЕ КНОПКИ В ОДНОМ МЕСТЕ)"""
    
    def __init__(self):
        super().__init__()
        print("🎤 [DEBUG] TempVoicePublicView создан")
    
    # КНОПКА 1: СОЗДАТЬ КОМНАТУ
    @discord.ui.button(
        label="🎤 СОЗДАТЬ КОМНАТУ",
        style=discord.ButtonStyle.success,
        emoji="🎤",
        row=0,
        custom_id="temp_voice_create"
    )
    async def create_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] create_room НАЖАТА пользователем {interaction.user.name}")
        existing = temp_voice_manager.get_user_room(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CreateRoomModal())
    
    # КНОПКА 2: РАСШИРИТЬ КОМНАТУ (только если есть комната)
    @discord.ui.button(
        label="➕ РАСШИРИТЬ",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        row=1,
        custom_id="temp_voice_expand"
    )
    async def expand_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] expand_room НАЖАТА пользователем {interaction.user.name}")
        
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
        
        modal = ExpandSlotsModal(channel.id, room['slots'], max_slots)
        await interaction.response.send_modal(modal)
    
    # КНОПКА 3: КИКНУТЬ ПОЛЬЗОВАТЕЛЯ (только если есть комната)
    @discord.ui.button(
        label="👢 КИКНУТЬ",
        style=discord.ButtonStyle.danger,
        emoji="👢",
        row=1,
        custom_id="temp_voice_kick"
    )
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] kick_user НАЖАТА пользователем {interaction.user.name}")
        
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
    
    # КНОПКА 4: ЗАКРЫТЬ КОМНАТУ (только если есть комната)
    @discord.ui.button(
        label="🔒 ЗАКРЫТЬ",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        row=1,
        custom_id="temp_voice_close"
    )
    async def close_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] close_room НАЖАТА пользователем {interaction.user.name}")
        
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
        await interaction.followup.send("✅ Комната закрыта", ephemeral=True)