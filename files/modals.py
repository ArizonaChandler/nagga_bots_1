"""Files Modals - Загрузка и удаление файлов"""
import discord
import asyncio
from datetime import datetime
from files.core import file_manager
from core.utils import is_admin

class UploadFileModal(discord.ui.Modal, title="📁 ЗАГРУЗКА ФАЙЛА"):
    file_name = discord.ui.TextInput(
        label="Название файла",
        placeholder="Например: Убрать кровь",
        max_length=100
    )
    
    file_description = discord.ui.TextInput(
        label="Описание",
        placeholder="Автоустановщик OPEN IV для вырезания крови",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "📤 **Отправьте файл в этот чат**\n"
            "Поддерживаются любые форматы (rar, zip, exe, dll, etc)",
            ephemeral=True
        )
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   len(m.attachments) > 0)
        
        try:
            msg = await interaction.client.wait_for('message', timeout=60.0, check=check)
            attachment = msg.attachments[0]
            
            file_id, error = await file_manager.save_file(
                interaction,
                self.file_name.value,
                self.file_description.value or "Нет описания",
                attachment
            )
            
            if error:
                await interaction.followup.send(f"❌ Ошибка: {error}", ephemeral=True)
            else:
                embed = discord.Embed(
                    title="✅ Файл успешно загружен!",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="📌 ID", value=f"`{file_id}`", inline=True)
                embed.add_field(name="📁 Название", value=self.file_name.value, inline=True)
                embed.add_field(name="📦 Размер", value=f"{attachment.size / 1024:.1f} КБ", inline=True)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Время ожидания истекло", ephemeral=True)

class DeleteFileModal(discord.ui.Modal, title="🗑️ УДАЛЕНИЕ ФАЙЛА"):
    file_id = discord.ui.TextInput(
        label="ID файла",
        placeholder="Введите ID файла из списка",
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            file_id = int(self.file_id.value)
            success, msg = file_manager.delete_file(file_id, str(interaction.user.id))
            await interaction.response.send_message(
                f"{'✅' if success else '❌'} {msg}",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат ID", ephemeral=True)