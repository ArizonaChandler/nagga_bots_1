"""Кнопки для системы временных комнат"""
import discord
from temp_voice.base import PermanentView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal, KickUserModal


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
        print("🎤 [DEBUG] create_room нажата")
        existing = temp_voice_manager.get_user_room(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CreateRoomModal())
    
    @discord.ui.Button(
        label="🔧 УПРАВЛЯТЬ",
        style=discord.ButtonStyle.primary,
        emoji="🔧",
        row=0,
        custom_id="temp_voice_manage"
    )
    async def manage_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("🎤 [DEBUG] manage_room нажата")
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message("❌ У вас нет активной комнаты", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return
        
        # Создаём embed
        embed = discord.Embed(
            title="🎤 УПРАВЛЕНИЕ КОМНАТОЙ",
            description=f"**Комната:** {channel.mention}\n"
                        f"**Слотов:** {room['slots']}\n"
                        f"**Создана:** {room['created_at'][:16]}\n\n"
                        f"**Участников:** {len(channel.members)}/{room['slots']}",
            color=0x00bfff
        )
        
        # Создаём view и отправляем
        view = TempVoiceManageView(interaction.user.id, channel.id, interaction.message.channel)
        await interaction.response.send_message(embed=embed, view=view)


class TempVoiceManageView(discord.ui.View):
    """Панель управления комнатой"""
    
    def __init__(self, creator_id: int, channel_id: int, target_channel):
        super().__init__(timeout=120)  # 2 минуты на управление
        self.creator_id = creator_id
        self.channel_id = channel_id
        self.target_channel = target_channel
        self.message = None
        self._add_buttons()
    
    def _add_buttons(self):
        # Расширить слоты
        expand_btn = discord.ui.Button(
            label="➕ РАСШИРИТЬ (+2 СЛОТА)",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        )
        expand_btn.callback = self.expand_slots
        self.add_item(expand_btn)
        
        # Кикнуть пользователя
        kick_btn = discord.ui.Button(
            label="👢 КИКНУТЬ ПОЛЬЗОВАТЕЛЯ",
            style=discord.ButtonStyle.danger,
            emoji="👢",
            row=1
        )
        kick_btn.callback = self.kick_user
        self.add_item(kick_btn)
        
        # Закрыть комнату
        close_btn = discord.ui.Button(
            label="🔒 ЗАКРЫТЬ КОМНАТУ",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            row=2
        )
        close_btn.callback = self.close_room
        self.add_item(close_btn)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "❌ Только создатель комнаты может управлять ею!",
                ephemeral=True
            )
            return False
        return True
    
    async def get_channel(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return None
        return channel
    
    async def expand_slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] expand_slots вызван")
        
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        success, msg = await temp_voice_manager.expand_slots(interaction, channel)
        await interaction.response.send_message(msg, ephemeral=True)
        
        if success:
            # Обновляем embed в сообщении
            room = temp_voice_manager.get_room_by_channel(channel.id)
            if room:
                embed = discord.Embed(
                    title="🎤 УПРАВЛЕНИЕ КОМНАТОЙ",
                    description=f"**Комната:** {channel.mention}\n"
                                f"**Слотов:** {room['slots']}\n\n"
                                f"**Участников:** {len(channel.members)}/{room['slots']}",
                    color=0x00bfff
                )
                await interaction.message.edit(embed=embed)
    
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] kick_user вызван")
        
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        if not channel.members:
            await interaction.response.send_message("❌ В комнате никого нет", ephemeral=True)
            return
        
        # Отправляем модалку
        modal = KickUserModal(self.channel_id)
        await interaction.response.send_modal(modal)
    
    async def close_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] close_room вызван")
        
        channel = await self.get_channel(interaction)
        if not channel:
            return
        
        await interaction.response.send_message("🔒 Закрываю комнату...", ephemeral=True)
        await temp_voice_manager.close_room(interaction, channel)
        
        # Удаляем сообщение с кнопками
        await interaction.message.delete()
        self.stop()


class TempVoiceTestView(discord.ui.View):
    """Тестовый view для проверки работы кнопок"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="✅ ТЕСТ",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("🎤 [TEST] ТЕСТОВАЯ КНОПКА СРАБОТАЛА!")
        await interaction.response.send_message("✅ Кнопка работает!", ephemeral=True)