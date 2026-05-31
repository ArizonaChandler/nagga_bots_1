"""Панель управления системой дней рождения (в канале настроек)"""
import discord
from core.database import db
from core.utils import is_super_admin, is_admin
from birthday.base import PermanentView
from birthday.manager import birthday_manager


class BirthdaySettingsView(PermanentView):
    """Панель управления системой дней рождения (в канале на сервере)"""

    def __init__(self):
        super().__init__()
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        
        # ===== РЯД 0: НАСТРОЙКА КАНАЛОВ СИСТЕМЫ =====
        channel_btn = discord.ui.Button(
            label="📡 Настройка каналов системы",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            row=0
        )
        channel_btn.callback = self.channels_menu
        self.add_item(channel_btn)
        
        # ===== РЯД 1: ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ =====
        enabled = db.get_setting('birthday_enabled')
        if enabled is None:
            enabled = '1'
        
        toggle_btn = discord.ui.Button(
            label=f"{'🟢 ВКЛЮЧЕНА' if enabled == '1' else '🔴 ВЫКЛЮЧЕНА'}",
            style=discord.ButtonStyle.success if enabled == '1' else discord.ButtonStyle.danger,
            emoji="🎂",
            row=1
        )
        toggle_btn.callback = self.toggle_system
        self.add_item(toggle_btn)
        
        # ===== РЯД 2: УПРАВЛЕНИЕ ДАННЫМИ =====
        clear_btn = discord.ui.Button(
            label="🗑️ ОЧИСТИТЬ ВСЕ",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=2
        )
        clear_btn.callback = self.clear_all
        self.add_item(clear_btn)
        
        stats_btn = discord.ui.Button(
            label="📊 СТАТИСТИКА",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=2
        )
        stats_btn.callback = self.show_stats
        self.add_item(stats_btn)

    async def channels_menu(self, interaction: discord.Interaction):
        """Открыть меню выбора каналов для системы"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📡 **НАСТРОЙКА КАНАЛОВ СИСТЕМЫ**",
            description="Выберите, какой канал хотите настроить:",
            color=0x7289da
        )
        view = BirthdayChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def toggle_system(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return

        current = db.get_setting('birthday_enabled')
        if current is None:
            current = '1'
        
        new_state = '0' if current == '1' else '1'
        db.set_setting('birthday_enabled', new_state, str(interaction.user.id))
        
        await interaction.response.send_message(f"✅ Система дней рождения {'включена' if new_state == '1' else 'выключена'}", ephemeral=True)
        
        self._add_buttons()
        await interaction.message.edit(view=self)

    async def clear_all(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return

        success, msg = birthday_manager.clear_all()
        await interaction.response.send_message(msg, ephemeral=True)
        
        channel_id = db.get_setting('birthday_channel')
        if channel_id:
            from birthday.views import update_birthday_embed
            await update_birthday_embed(interaction.client, channel_id)

    async def show_stats(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return

        stats = birthday_manager.get_stats()
        embed = discord.Embed(title="📊 **СТАТИСТИКА ДНЕЙ РОЖДЕНИЯ**", color=0x00ff00)
        embed.add_field(name="👥 Всего записей", value=f"`{stats['total']}`", inline=True)
        embed.add_field(name="🎉 Сегодня", value=f"`{stats['today']}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BirthdayChannelsView(discord.ui.View):
    """Меню выбора каналов для системы"""

    def __init__(self):
        super().__init__(timeout=60)

        public_btn = discord.ui.Button(label="🎂 Канал дней рождения (публичный)", style=discord.ButtonStyle.secondary, row=0)
        public_btn.callback = self.set_public_channel
        self.add_item(public_btn)

        greeting_btn = discord.ui.Button(label="🎉 Канал поздравлений", style=discord.ButtonStyle.secondary, row=0)
        greeting_btn.callback = self.set_greeting_channel
        self.add_item(greeting_btn)

        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def set_public_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetSystemChannelModal("birthday_channel", "публичный канал дней рождения"))

    async def set_greeting_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetSystemChannelModal("birthday_greeting_channel", "канал поздравлений"))

    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ ДНЕЙ РОЖДЕНИЯ**",
            description="Настройка и управление системой",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=BirthdaySettingsView())


class SetSystemChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key

        self.channel_id = discord.ui.TextInput(
            label=f"ID {description}",
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        self.add_item(self.channel_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return

            db.set_setting(self.setting_key, self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(f"✅ {self.channel_id.label} настроен: {channel.mention}", ephemeral=True)
            
            # Если настраиваем публичный канал — сразу создаём embed
            if self.setting_key == "birthday_channel":
                from birthday.views import update_birthday_embed
                await update_birthday_embed(interaction.client, self.channel_id.value)

        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)