"""Admin Modals - Модальные окна для административных настроек"""
import discord
from core.database import db
from core.config import CONFIG, save_config, SUPER_ADMIN_ID
from core.utils import format_mention, is_super_admin

class SetRoleModal(discord.ui.Modal, title="🎭 УСТАНОВИТЬ РОЛЬ CAPT"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['capt_role_id'] = self.role_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_CAPT_ROLE", f"Role ID: {self.role_id.value}")
        await interaction.response.send_message(
            f"✅ Роль CAPT: {format_mention(interaction.guild, self.role_id.value, 'role')}",
            ephemeral=True
        )

class SetCaptChannelModal(discord.ui.Modal, title="💬 УСТАНОВИТЬ ЧАТ ОШИБОК"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['capt_channel_id'] = self.channel_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_CAPT_CHANNEL", f"Channel ID: {self.channel_id.value}")
        await interaction.response.send_message(
            f"✅ Чат ошибок: {format_mention(interaction.guild, self.channel_id.value, 'channel')}",
            ephemeral=True
        )

class SetServerModal(discord.ui.Modal, title="🌍 УСТАНОВИТЬ СЕРВЕР"):
    server_id = discord.ui.TextInput(label="ID сервера", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['server_id'] = self.server_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_SERVER", f"Server ID: {self.server_id.value}")
        await interaction.response.send_message(
            f"✅ Сервер: `{self.server_id.value}`",
            ephemeral=True
        )

class AddUserModal(discord.ui.Modal, title="👥 ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if db.add_user(self.user_id.value, str(interaction.user.id)):
            db.log_action(str(interaction.user.id), "ADD_USER", f"Added {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Добавлен: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь уже существует", ephemeral=True)

class RemoveUserModal(discord.ui.Modal, title="❌ УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if db.remove_user(self.user_id.value):
            db.log_action(str(interaction.user.id), "REMOVE_USER", f"Removed {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Удалён: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь не найден", ephemeral=True)

class AddAdminModal(discord.ui.Modal, title="👑 ДОБАВИТЬ АДМИНИСТРАТОРА"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор", ephemeral=True)
            return
        
        if db.add_admin(self.user_id.value, str(interaction.user.id)):
            db.add_user(self.user_id.value, str(interaction.user.id))
            db.log_action(str(interaction.user.id), "ADD_ADMIN", f"Added admin {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Администратор: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь уже администратор", ephemeral=True)

class RemoveAdminModal(discord.ui.Modal, title="👑 УДАЛИТЬ АДМИНИСТРАТОРА"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор", ephemeral=True)
            return
        
        if self.user_id.value == SUPER_ADMIN_ID:
            await interaction.response.send_message("❌ Нельзя удалить супер-администратора", ephemeral=True)
            return
        
        if db.remove_admin(self.user_id.value):
            db.log_action(str(interaction.user.id), "REMOVE_ADMIN", f"Removed admin {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Администратор удалён: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь не является администратором", ephemeral=True)