import discord
from datetime import datetime
from files.core import file_manager
from core.menus import BaseMenuView
from core.config import CONFIG

class FilesView(BaseMenuView):
    def __init__(self, user_id: str, page: int = 1, previous_view=None, previous_embed=None):
        super().__init__(user_id, None, previous_view, previous_embed)
        self.page = page
        self.files = []
        self.total = 0
        self.max_page = 1
        self.message = None
        self.load_files()
    
    def load_files(self):
        self.files, self.total = file_manager.get_files(self.page, per_page=5)
        self.max_page = (self.total + 4) // 5 if self.total > 0 else 1
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        for i, (file_id, name, desc, size, uploader, uploaded_at, downloads) in enumerate(self.files, 1):
            size_str = f"{size / 1024:.1f} КБ" if size < 1024*1024 else f"{size / (1024*1024):.1f} МБ"
            
            btn = discord.ui.Button(
                label=f"{i}. {name[:30]}...",
                style=discord.ButtonStyle.primary,
                custom_id=f"file_{file_id}"
            )
            
            async def callback(interaction, fid=file_id, fname=name, fdesc=desc, fsize=size_str):
                success, msg = await file_manager.send_file(interaction, fid)
                if success:
                    embed = discord.Embed(
                        title="✅ Файл отправлен!",
                        description=f"**{fname}**\n{fdesc}",
                        color=0x00ff00
                    )
                    embed.add_field(name="📦 Размер", value=fsize, inline=True)
                    embed.add_field(name="📥 Статус", value="Успешно", inline=True)
                    if msg:
                        embed.add_field(name="⚠️", value=msg, inline=False)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            
            btn.callback = callback
            self.add_item(btn)
        
        # Пагинация
        if self.page > 1:
            prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
            async def prev_cb(interaction):
                self.page -= 1
                self.load_files()
                embed = self.create_embed()
                await interaction.response.edit_message(embed=embed, view=self)
            prev_btn.callback = prev_cb
            self.add_item(prev_btn)
        
        if self.page < self.max_page:
            next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary)
            async def next_cb(interaction):
                self.page += 1
                self.load_files()
                embed = self.create_embed()
                await interaction.response.edit_message(embed=embed, view=self)
            next_btn.callback = next_cb
            self.add_item(next_btn)
        
        # Кнопка "Назад" в главное меню
        self.add_back_button(row=4)
    
    def create_embed(self):
        description = f"**📊 Всего доступно файлов: {self.total}**\n\n"
        for idx, (file_id, name, desc, size, uploader, uploaded_at, downloads) in enumerate(self.files, 1):
            size_str = f"{size / 1024:.1f} КБ" if size < 1024*1024 else f"{size / (1024*1024):.1f} МБ"
            date_str = uploaded_at[:10] if uploaded_at else "?"
            description += f"**{idx}. {name}**\n"
            description += f"   📝 {desc[:100]}{'...' if len(desc) > 100 else ''}\n"
            description += f"   📦 {size_str} | ⬇️ {downloads} | 📅 {date_str}\n\n"
        
        embed = discord.Embed(
            title="📁 **ПОЛЕЗНЫЕ ФАЙЛЫ**",
            description=description,
            color=0x00ff00
        )
        embed.set_footer(text=f"{CONFIG.get('family_name', 'Семья')} • Страница {self.page}/{self.max_page}")
        return embed
    
    async def send_initial(self, interaction):
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        self.message = await interaction.original_response()