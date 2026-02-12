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
