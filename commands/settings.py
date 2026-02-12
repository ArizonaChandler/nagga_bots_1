"""Команда !settings - панель администратора (только ЛС)"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin, is_super_admin, format_mention
from admin.views import SettingsView
from files.modals import UploadFileModal, DeleteFileModal
from files.core import file_manager

class AdminSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        settings_btn = discord.ui.Button(
            label="⚙️ Настройки бота",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0
        )
        async def settings_cb(i):
            view = SettingsView(self.user_id, self.guild)
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ БОТА**",
                color=0x7289da
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        settings_btn.callback = settings_cb
        self.add_item(settings_btn)
        
        files_btn = discord.ui.Button(
            label="📁 Управление файлами",
            style=discord.ButtonStyle.success,
            emoji="📁",
            row=0
        )
        async def files_cb(i):
            view = FileSettingsView(self.user_id, self.guild)
            embed = discord.Embed(
                title="📁 **УПРАВЛЕНИЕ ФАЙЛАМИ**",
                description=f"Всего файлов: **{file_manager.get_files(page=1)[1]}**",
                color=0x00ff00
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        files_btn.callback = files_cb
        self.add_item(files_btn)

class FileSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        add_btn = discord.ui.Button(
            label="➕ Добавить файл",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        )
        async def add_cb(i):
            await i.response.send_modal(UploadFileModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        delete_btn = discord.ui.Button(
            label="🗑️ Удалить файл",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=0
        )
        async def delete_cb(i):
            await i.response.send_modal(DeleteFileModal())
        delete_btn.callback = delete_cb
        self.add_item(delete_btn)
        
        list_btn = discord.ui.Button(
            label="📋 Список файлов",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            row=1
        )
        async def list_cb(i):
            files, total = file_manager.get_files(page=1, per_page=10)
            
            if not files:
                await i.response.send_message("📁 Нет загруженных файлов", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 **ЗАГРУЖЕННЫЕ ФАЙЛЫ**",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            for file_id, name, desc, size, uploader, uploaded_at, downloads in files:
                size_str = f"{size / 1024:.1f} КБ"
                uploader_mention = format_mention(self.guild, uploader, 'user')
                date_str = uploaded_at[:10] if uploaded_at else "?"
                
                embed.add_field(
                    name=f"ID: {file_id} - {name}",
                    value=f"📦 {size_str} | 👤 {uploader_mention} | 📅 {date_str} | ⬇️ {downloads}\n{desc[:100]}",
                    inline=False
                )
            
            embed.set_footer(text=f"Всего файлов: {total}")
            await i.response.send_message(embed=embed, ephemeral=True)
        list_btn.callback = list_cb
        self.add_item(list_btn)

def setup(bot):
    @bot.command(name='settings')
    async def settings(ctx):
        user_id = str(ctx.author.id)
        
        if ctx.guild is not None:
            return
        
        if not await is_admin(user_id):
            return
        
        embed = discord.Embed(
            title="⚙️ **ПАНЕЛЬ АДМИНИСТРАТОРА**",
            description="Выберите раздел для настройки:",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        if await is_super_admin(user_id):
            embed.add_field(
                name="👑 Ваш статус",
                value="**Супер-администратор** (полный доступ)",
                inline=False
            )
        else:
            embed.add_field(
                name="👑 Ваш статус",
                value="**Администратор**",
                inline=False
            )
        
        view = AdminSettingsView(user_id, ctx.guild)
        await ctx.author.send(embed=embed, view=view)
        db.log_action(user_id, "SETTINGS_OPEN")
