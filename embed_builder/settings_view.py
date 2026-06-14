"""Панель настроек системы создания embed"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
from embed_builder.views import EmbedBuilderPanelView
from embed_builder.manager import embed_builder_manager


class EmbedBuilderSettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        channel_btn = discord.ui.Button(
            label="📢 Канал для отправки",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            row=0,
            custom_id="embed_channel"
        )
        channel_btn.callback = self.set_channel
        self.add_item(channel_btn)
        
        create_btn = discord.ui.Button(
            label="📝 СОЗДАТЬ EMBED",
            style=discord.ButtonStyle.success,
            emoji="📝",
            row=1,
            custom_id="embed_create"
        )
        create_btn.callback = self.open_panel
        self.add_item(create_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="embed_back_to_global"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)
    
    async def set_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEmbedChannelModal())
    
    async def open_panel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        settings = embed_builder_manager.get_settings()
        channel_id = settings.get('embed_builder_channel')
        
        if not channel_id:
            await interaction.response.send_message(
                "❌ Сначала настройте канал для отправки embed!\n"
                "Используйте кнопку «📢 Канал для отправки»",
                ephemeral=True
            )
            return
        
        view = EmbedBuilderPanelView(int(channel_id))
        embed = discord.Embed(
            title="📝 **СОЗДАНИЕ EMBED**",
            description="Выберите тип embed для создания",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)


class SetEmbedChannelModal(discord.ui.Modal, title="📢 КАНАЛ ДЛЯ ОТПРАВКИ EMBED"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            embed_builder_manager.save_setting('embed_builder_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал для отправки embed настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)