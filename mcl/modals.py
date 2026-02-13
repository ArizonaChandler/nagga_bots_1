"""Модальные окна для настройки MCL"""
import discord
from core.database import db
from core.config import CONFIG, save_config
from core.utils import format_mention
from mcl.core import dual_mcl_core

class SetMclChannelModal(discord.ui.Modal, title="💬 УСТАНОВИТЬ КАНАЛ MCL"):
    channel_id = discord.ui.TextInput(
        label="ID канала",
        placeholder="123456789012345678"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['channel_id'] = self.channel_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_MCL_CHANNEL", f"Channel ID: {self.channel_id.value}")
        await interaction.response.send_message(
            f"✅ Канал MCL: {format_mention(interaction.guild, self.channel_id.value, 'channel')}",
            ephemeral=True
        )

class SetDualColorModal(discord.ui.Modal, title="🎨 УСТАНОВИТЬ ЦВЕТА DUAL MCL"):
    color1 = discord.ui.TextInput(
        label="🎨 Цвет токена 1 (основной)",
        placeholder="Pink",
        default="Pink"
    )
    color2 = discord.ui.TextInput(
        label="🎨 Цвет токена 2 (основной)",
        placeholder="Orange",
        default="Orange"
    )
    extra_color1 = discord.ui.TextInput(
        label="🎨 Доп. цвет токена 1",
        placeholder="Purple",
        default="Purple",
        required=False
    )
    extra_color2 = discord.ui.TextInput(
        label="🎨 Доп. цвет токена 2",
        placeholder="Gold",
        default="Gold",
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Основные цвета
        CONFIG['message_1'] = f"Unit\n{self.color1.value}"
        CONFIG['message_2'] = f"Unit\n{self.color2.value}"
        
        # Дополнительные цвета (сохраняем в отдельные настройки)
        CONFIG['extra_color_1'] = self.extra_color1.value
        CONFIG['extra_color_2'] = self.extra_color2.value
        
        save_config(str(interaction.user.id))
        
        # Обновляем в core
        dual_mcl_core.token_colors = {1: self.color1.value, 2: self.color2.value}
        dual_mcl_core.token_extra_colors = {1: self.extra_color1.value, 2: self.extra_color2.value}
        
        db.log_action(str(interaction.user.id), "SET_DUAL_COLORS", 
                     f"Colors: {self.color1.value}/{self.color2.value}, Extra: {self.extra_color1.value}/{self.extra_color2.value}")
        
        await interaction.response.send_message(
            f"✅ Цвета DUAL MCL:\n"
            f"Токен 1: {self.color1.value} (осн.), {self.extra_color1.value} (доп.)\n"
            f"Токен 2: {self.color2.value} (осн.), {self.extra_color2.value} (доп.)",
            ephemeral=True
        )