"""Files Views - Кнопочный интерфейс с пагинацией"""
import discord
from files.core import file_manager

class FilesView(discord.ui.View):
    def __init__(self, user_id: str, page: int = 1):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.page = page
        self.load_files()
    
    def load_files(self):
        self.files, self.total = file_manager.get_files(self.page, per_page=5)
        self.max_page = (self.total + 4) // 5 if self.total > 0 else 1
        
        self.clear_items()
        
        for i, (file_id, name, desc, size, uploader, uploaded_at, downloads) in enumerate(self.files, 1):
            size_str = f"{size / 1024:.1f} КБ" if size < 1024*1024 else f"{size / (1024*1024):.1f} МБ"
            
            btn = discord.ui.Button(
                label=f"{i}. {name[:30]}...",
                style=discord.ButtonStyle.primary,
                custom_id=f"file_{file_id}"
            )
            
            async def callback(interaction, fid=file_id, fname=name, fdesc=desc):
                success, msg = await file_manager.send_file(interaction, fid)
                if success:
                    await interaction.response.send_message(
                        f"✅ Файл **{fname}** отправлен в ЛС!" + (f"\n⚠️ {msg}" if msg else ""),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            
            btn.callback = callback
            self.add_item(btn)
        
        if self.page > 1:
            prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
            async def prev_cb(interaction):
                await interaction.response.edit_message(view=FilesView(self.user_id, self.page - 1))
            prev_btn.callback = prev_cb
            self.add_item(prev_btn)
        
        if self.page < self.max_page:
            next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary)
            async def next_cb(interaction):
                await interaction.response.edit_message(view=FilesView(self.user_id, self.page + 1))
            next_btn.callback = next_cb
            self.add_item(next_btn)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Это меню вызвано другим пользователем", ephemeral=True)
            return False
        return True