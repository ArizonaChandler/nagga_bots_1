"""Панель настроек системы временных комнат"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
from temp_voice.manager import temp_voice_manager


class TempVoiceSettingsView(AdminOnlyView):

    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        
        category_btn = discord.ui.Button(
            label="📁 Категория для комнат",
            style=discord.ButtonStyle.primary,
            emoji="📁",
            row=0,
            custom_id="temp_voice_category"
        )
        category_btn.callback = self.set_category
        self.add_item(category_btn)
        
        public_btn = discord.ui.Button(
            label="📢 Публичный канал",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            row=0,
            custom_id="temp_voice_public"
        )
        public_btn.callback = self.set_public_channel
        self.add_item(public_btn)
        
        log_btn = discord.ui.Button(
            label="📜 Канал логов",
            style=discord.ButtonStyle.primary,
            emoji="📜",
            row=1,
            custom_id="temp_voice_log"
        )
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        max_slots_btn = discord.ui.Button(
            label="📊 Максимум слотов",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=1,
            custom_id="temp_voice_max_slots"
        )
        max_slots_btn.callback = self.set_max_slots
        self.add_item(max_slots_btn)
        
        delay_btn = discord.ui.Button(
            label="⏰ Задержка удаления (сек)",
            style=discord.ButtonStyle.secondary,
            emoji="⏰",
            row=2,
            custom_id="temp_voice_delay"
        )
        delay_btn.callback = self.set_delete_delay
        self.add_item(delay_btn)
        
        show_btn = discord.ui.Button(
            label="📊 Текущие настройки",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=2,
            custom_id="temp_voice_show"
        )
        show_btn.callback = self.show_settings
        self.add_item(show_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="temp_voice_back_to_global"
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

    async def set_category(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTempVoiceCategoryModal())

    async def set_public_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTempVoicePublicChannelModal())

    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTempVoiceLogChannelModal())

    async def set_max_slots(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTempVoiceMaxSlotsModal())

    async def set_delete_delay(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTempVoiceDeleteDelayModal())

    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        settings = temp_voice_manager.get_settings()
        guild = interaction.guild
        
        category = guild.get_channel(int(settings['temp_voice_category'])) if settings['temp_voice_category'] else None
        public_channel = guild.get_channel(int(settings['temp_voice_public_channel'])) if settings['temp_voice_public_channel'] else None
        log_channel = guild.get_channel(int(settings['temp_voice_log_channel'])) if settings['temp_voice_log_channel'] else None
        
        embed = discord.Embed(title="📊 НАСТРОЙКИ ВРЕМЕННЫХ КОМНАТ", color=0x00ff00)
        embed.add_field(name="📁 Категория", value=category.mention if category else "`Не настроена`", inline=False)
        embed.add_field(name="📢 Публичный канал", value=public_channel.mention if public_channel else "`Не настроен`", inline=False)
        embed.add_field(name="📜 Канал логов", value=log_channel.mention if log_channel else "`Не настроен`", inline=False)
        embed.add_field(name="📊 Максимум слотов", value=f"`{settings['temp_voice_max_slots']}`", inline=True)
        embed.add_field(name="⏰ Задержка удаления", value=f"`{settings['temp_voice_delete_delay']}` сек", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetTempVoiceCategoryModal(discord.ui.Modal, title="📁 КАТЕГОРИЯ ДЛЯ КОМНАТ"):
    category_id = discord.ui.TextInput(label="ID категории", placeholder="123456789012345678", max_length=20, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            category = interaction.guild.get_channel(int(self.category_id.value))
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Категория не найдена", ephemeral=True)
                return
            temp_voice_manager.save_setting('temp_voice_category', self.category_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Категория настроена: {category.name}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTempVoicePublicChannelModal(discord.ui.Modal, title="📢 ПУБЛИЧНЫЙ КАНАЛ"):
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
            temp_voice_manager.save_setting('temp_voice_public_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Публичный канал настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTempVoiceLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ"):
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
            temp_voice_manager.save_setting('temp_voice_log_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTempVoiceMaxSlotsModal(discord.ui.Modal, title="📊 МАКСИМУМ СЛОТОВ"):
    slots = discord.ui.TextInput(label="Максимум слотов", placeholder="10", max_length=3, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            slots_num = int(self.slots.value)
            if slots_num < 2:
                await interaction.response.send_message("❌ Минимум 2 слота", ephemeral=True)
                return
            if slots_num > 99:
                await interaction.response.send_message("❌ Максимум 99 слотов", ephemeral=True)
                return
            temp_voice_manager.save_setting('temp_voice_max_slots', str(slots_num), str(interaction.user.id))
            await interaction.response.send_message(f"✅ Максимум слотов: **{slots_num}**", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


class SetTempVoiceDeleteDelayModal(discord.ui.Modal, title="⏰ ЗАДЕРЖКА УДАЛЕНИЯ"):
    delay = discord.ui.TextInput(label="Секунд до удаления", placeholder="60", max_length=4, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            delay_num = int(self.delay.value)
            if delay_num < 10:
                await interaction.response.send_message("❌ Минимум 10 секунд", ephemeral=True)
                return
            if delay_num > 300:
                await interaction.response.send_message("❌ Максимум 300 секунд (5 минут)", ephemeral=True)
                return
            temp_voice_manager.save_setting('temp_voice_delete_delay', str(delay_num), str(interaction.user.id))
            await interaction.response.send_message(f"✅ Задержка удаления: **{delay_num}** секунд", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)