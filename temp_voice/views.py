"""Кнопки для системы временных комнат"""
import discord
from temp_voice.base import PermanentView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal, KickUserModal


class TempVoicePublicView(PermanentView):
    """Публичные кнопки для создания и управления комнатами"""
    
    def __init__(self):
        super().__init__()
        print("🎤 [DEBUG] TempVoicePublicView создан")
    
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
            print(f"🎤 [DEBUG] create_room: у пользователя уже есть комната {existing['channel_id']}")
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return
        print(f"🎤 [DEBUG] create_room: отправляем модалку")
        await interaction.response.send_modal(CreateRoomModal())
    
    @discord.ui.button(
        label="🔧 УПРАВЛЯТЬ",
        style=discord.ButtonStyle.primary,
        emoji="🔧",
        row=0,
        custom_id="temp_voice_manage"
    )
    async def manage_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] manage_room НАЖАТА пользователем {interaction.user.name}")
        room = temp_voice_manager.get_user_room(interaction.user.id)
        
        if not room:
            print(f"🎤 [DEBUG] manage_room: у пользователя нет комнаты")
            await interaction.response.send_message(
                "❌ У вас нет активной комнаты.\nИспользуйте кнопку 'СОЗДАТЬ КОМНАТУ'",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            print(f"🎤 [DEBUG] manage_room: комната {room['channel_id']} не найдена")
            await interaction.response.send_message(
                "❌ Ваша комната не найдена. Возможно, она была удалена.",
                ephemeral=True
            )
            return
        
        print(f"🎤 [DEBUG] manage_room: комната найдена - {channel.name}")
        
        embed = discord.Embed(
            title="🎤 УПРАВЛЕНИЕ КОМНАТОЙ",
            description=f"**Комната:** {channel.mention}\n"
                        f"**Слотов:** {room['slots']}\n"
                        f"**Создана:** {room['created_at'][:16]}\n\n"
                        f"**Участников в комнате:** {len(channel.members)}/{room['slots']}",
            color=0x00bfff
        )
        
        view = TempVoiceManageView(interaction.user.id, channel.id)
        print(f"🎤 [DEBUG] manage_room: отправляем панель управления")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


class TempVoiceManageView(discord.ui.View):
    """Панель управления комнатой (только для создателя)"""
    
    def __init__(self, creator_id: int, channel_id: int):
        super().__init__(timeout=120)
        self.creator_id = creator_id
        self.channel_id = channel_id
        print(f"🎤 [DEBUG] TempVoiceManageView создан для creator_id={creator_id}, channel_id={channel_id}")
        
        expand_btn = discord.ui.Button(
            label="➕ РАСШИРИТЬ (+2 СЛОТА)",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0,
            custom_id=f"temp_voice_expand_{channel_id}"
        )
        expand_btn.callback = self.expand_slots
        self.add_item(expand_btn)
        print(f"🎤 [DEBUG] TempVoiceManageView: кнопка РАСШИРИТЬ добавлена")
        
        kick_btn = discord.ui.Button(
            label="👢 КИКНУТЬ ПОЛЬЗОВАТЕЛЯ",
            style=discord.ButtonStyle.danger,
            emoji="👢",
            row=1,
            custom_id=f"temp_voice_kick_{channel_id}"
        )
        kick_btn.callback = self.kick_user
        self.add_item(kick_btn)
        print(f"🎤 [DEBUG] TempVoiceManageView: кнопка КИКНУТЬ добавлена")
        
        close_btn = discord.ui.Button(
            label="🔒 ЗАКРЫТЬ КОМНАТУ",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            row=2,
            custom_id=f"temp_voice_close_{channel_id}"
        )
        close_btn.callback = self.close_room
        self.add_item(close_btn)
        print(f"🎤 [DEBUG] TempVoiceManageView: кнопка ЗАКРЫТЬ добавлена")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        print(f"🎤 [DEBUG] TempVoiceManageView.interaction_check: user={interaction.user.id}, creator={self.creator_id}")
        if interaction.user.id != self.creator_id:
            print(f"🎤 [DEBUG] TempVoiceManageView: доступ запрещён (не создатель)")
            await interaction.response.send_message(
                "❌ Только создатель комнаты может управлять ею!",
                ephemeral=True
            )
            return False
        print(f"🎤 [DEBUG] TempVoiceManageView: доступ разрешён")
        return True
    
    async def get_channel(self, interaction: discord.Interaction):
        print(f"🎤 [DEBUG] get_channel: channel_id={self.channel_id}")
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            print(f"🎤 [DEBUG] get_channel: канал не найден")
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return None
        print(f"🎤 [DEBUG] get_channel: канал найден - {channel.name}")
        return channel
    
    async def expand_slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] expand_slots ВЫЗВАН пользователем {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        print(f"🎤 [DEBUG] expand_slots: response.defer выполнен")
        
        channel = await self.get_channel(interaction)
        if not channel:
            print(f"🎤 [DEBUG] expand_slots: канал не получен, выход")
            return
        
        print(f"🎤 [DEBUG] expand_slots: вызываем temp_voice_manager.expand_slots")
        success, msg = await temp_voice_manager.expand_slots(interaction, channel)
        print(f"🎤 [DEBUG] expand_slots: результат success={success}, msg={msg}")
        
        await interaction.followup.send(msg, ephemeral=True)
        
        if success:
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
                print(f"🎤 [DEBUG] expand_slots: embed обновлён")
    
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] kick_user ВЫЗВАН пользователем {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        print(f"🎤 [DEBUG] kick_user: response.defer выполнен")
        
        channel = await self.get_channel(interaction)
        if not channel:
            print(f"🎤 [DEBUG] kick_user: канал не получен, выход")
            return
        
        if not channel.members:
            print(f"🎤 [DEBUG] kick_user: в комнате никого нет")
            await interaction.followup.send("❌ В комнате никого нет", ephemeral=True)
            return
        
        print(f"🎤 [DEBUG] kick_user: отправляем модалку")
        modal = KickUserModal(self.channel_id)
        await interaction.followup.send_modal(modal)
    
    async def close_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"🎤 [DEBUG] close_room ВЫЗВАН пользователем {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        print(f"🎤 [DEBUG] close_room: response.defer выполнен")
        
        channel = await self.get_channel(interaction)
        if not channel:
            print(f"🎤 [DEBUG] close_room: канал не получен, выход")
            return
        
        print(f"🎤 [DEBUG] close_room: вызываем temp_voice_manager.close_room")
        await temp_voice_manager.close_room(interaction, channel)
        await interaction.followup.send("✅ Комната закрыта", ephemeral=True)
        
        try:
            await interaction.message.delete()
            print(f"🎤 [DEBUG] close_room: сообщение удалено")
        except Exception as e:
            print(f"🎤 [DEBUG] close_room: не удалось удалить сообщение - {e}")
        
        self.stop()
        print(f"🎤 [DEBUG] close_room: view остановлен")