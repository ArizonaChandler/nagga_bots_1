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


class SetSlotsModal(discord.ui.Modal, title="⚙️ УСТАНОВИТЬ КОЛИЧЕСТВО СЛОТОВ"):
    slots = discord.ui.TextInput(
        label="Количество слотов",
        placeholder="Введите число от 1 до максимума",
        max_length=2,
        required=True
    )
    
    def __init__(self, channel_id: int, current_slots: int, max_slots: int):
        super().__init__()
        self.channel_id = channel_id
        self.current_slots = current_slots
        self.max_slots = max_slots
        self.slots.placeholder = f"Текущее: {current_slots}, максимум: {max_slots}"
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_slots = int(self.slots.value)
            if new_slots < 1:
                await interaction.response.send_message("❌ Минимум 1 слот", ephemeral=True)
                return
            
            if new_slots > self.max_slots:
                await interaction.response.send_message(f"❌ Нельзя превысить максимум {self.max_slots} слотов", ephemeral=True)
                return
            
            channel = interaction.guild.get_channel(self.channel_id)
            if not channel:
                await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
                return
            
            # Проверяем, что в комнате не больше участников, чем новый лимит
            if len(channel.members) > new_slots:
                await interaction.response.send_message(
                    f"❌ В комнате {len(channel.members)} участников, нельзя уменьшить до {new_slots}",
                    ephemeral=True
                )
                return
            
            if new_slots > self.current_slots:
                success, msg = await temp_voice_manager.expand_slots_to(interaction, channel, new_slots)
            elif new_slots < self.current_slots:
                success, msg = await temp_voice_manager.reduce_slots_to(interaction, channel, new_slots)
            else:
                await interaction.response.send_message("ℹ️ Количество слотов не изменилось", ephemeral=True)
                return
            
            await interaction.response.send_message(msg, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


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