"""Панель управления системой дней рождения (в канале настроек)"""
import discord
from core.database import db
from core.utils import is_super_admin
from core.admin_views import AdminOnlyView
from birthday.manager import birthday_manager


class BirthdaySettingsView(AdminOnlyView):
    """Панель управления системой дней рождения"""

    def __init__(self):
        super().__init__()
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        
        enabled = db.get_setting('birthday_enabled')
        if enabled is None:
            enabled = '1'
        
        toggle_btn = discord.ui.Button(label=f"{'🟢 ВКЛЮЧЕНА' if enabled == '1' else '🔴 ВЫКЛЮЧЕНА'}", style=discord.ButtonStyle.success if enabled == '1' else discord.ButtonStyle.danger, emoji="🎂", row=0, custom_id="birthday_toggle")
        toggle_btn.callback = self.toggle_system
        self.add_item(toggle_btn)
        
        clear_btn = discord.ui.Button(label="🗑️ ОЧИСТИТЬ ВСЕ", style=discord.ButtonStyle.danger, emoji="🗑️", row=1, custom_id="birthday_clear")
        clear_btn.callback = self.clear_all
        self.add_item(clear_btn)
        
        stats_btn = discord.ui.Button(label="📊 СТАТИСТИКА", style=discord.ButtonStyle.secondary, emoji="📊", row=1, custom_id="birthday_stats")
        stats_btn.callback = self.show_stats
        self.add_item(stats_btn)

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