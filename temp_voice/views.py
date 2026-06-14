"""Кнопки для системы временных комнат"""
import discord
from temp_voice.base import PermanentView, CreatorOnlyView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal, KickUserModal
from core.config import CONFIG


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
        """Создать временную комнату"""
        # Проверяем, не превышен ли лимит комнат
        existing = temp_voice_manager.get_user_room(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>\n"
                f"Вы можете управлять ею через кнопку '🔧 УПРАВЛЯТЬ'",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(CreateRoomModal())
    
    @discord.ui.button(
        label="🔧 УПРАВЛЯТЬ",
        style=discord.ButtonStyle.primary,
        emoji="🔧",
        row=0,
        custom_id="temp_voice_manage"
    )
    async def manage_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Управлять своей комнатой"""
        room = temp_voice_manager.get_user_room(interaction.user.id)
        
        if not room:
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\n"
                "Используйте кнопку 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message(
                "❌ Ваша комната не найдена. Возможно, она была удалена.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎤 УПРАВЛЕНИЕ КОМНАТОЙ",
            description=f"**Комната:** {channel.mention}\n"
                        f"**Слотов:** {room['slots']}\n"
                        f"**Создана:** {room['created_at'][:16]}\n\n"
                        f"**Участников в комнате:** {len(channel.members)}/{room['slots']}",
            color=0x00bfff
        )
        
        view = TempVoiceManageView(interaction.user.id, channel.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TempVoiceManageView(CreatorOnlyView):
    """Панель управления комнатой (только для создателя)"""
    
    def __init__(self, creator_id: int, channel_id: int):
        super().__init__(creator_id)
        self.channel_id = channel_id
        self._add_buttons()
    
    def _add_buttons(self):
        # Расширить слоты
        expand_btn = discord.ui.Button(
            label="➕ РАСШИРИТЬ (+2 СЛОТА)",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0,
            custom_id="temp_voice_expand"
        )
        expand_btn.callback = self.expand_slots
        self.add_item(expand_btn)
        
        # Кикнуть пользователя
        kick_btn = discord.ui.Button(
            label="👢 КИКНУТЬ ПОЛЬЗОВАТЕЛЯ",
            style=discord.ButtonStyle.danger,
            emoji="👢",
            row=1,
            custom_id="temp_voice_kick"
        )
        kick_btn.callback = self.kick_user
        self.add_item(kick_btn)
        
        # Закрыть комнату
        close_btn = discord.ui.Button(
            label="🔒 ЗАКРЫТЬ КОМНАТУ",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            row=2,
            custom_id="temp_voice_close"
        )
        close_btn.callback = self.close_room
        self.add_item(close_btn)
    
    async def get_channel(self, interaction: discord.Interaction) -> discord.VoiceChannel:
        """Получить канал комнаты"""
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return None
        return channel
    
    async def expand_slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Расширить количество слотов"""
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        success, msg = await temp_voice_manager.expand_slots(interaction, channel)
        await interaction.response.send_message(msg, ephemeral=True)
        
        # Обновляем embed
        if success:
            room = temp_voice_manager.get_room_by_channel(channel.id)
            if room:
                embed = discord.Embed(
                    title="🎤 УПРАВЛЕНИЕ КОМНАТОЙ",
                    description=f"**Комната:** {channel.mention}\n"
                                f"**Слотов:** {room['slots']}\n\n"
                                f"**Участников в комнате:** {len(channel.members)}/{room['slots']}",
                    color=0x00bfff
                )
                await interaction.edit_original_response(embed=embed)
    
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открыть модалку для выбора пользователя"""
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        if not channel.members:
            await interaction.response.send_message("❌ В комнате никого нет", ephemeral=True)
            return
        
        await interaction.response.send_modal(KickUserModal(channel.id))
    
    async def close_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Закрыть комнату"""
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        success, msg = await temp_voice_manager.close_room(interaction, channel)
        await interaction.response.send_message(msg, ephemeral=True)
        
        # Закрываем view
        self.stop()