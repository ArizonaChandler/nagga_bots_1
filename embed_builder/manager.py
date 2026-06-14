"""Менеджер для создания embed сообщений"""
import discord
from core.database import db
from core.config import CONFIG


class EmbedBuilderManager:
    
    def __init__(self):
        self.bot = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    def get_settings(self):
        return {
            'embed_builder_channel': CONFIG.get('embed_builder_channel'),
            'embed_builder_settings_channel': CONFIG.get('embed_builder_settings_channel'),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        db.set_setting(key, value, updated_by)
        CONFIG[key] = value
    
    async def send_embed(self, channel_id: int, title: str, description: str, 
                         color: int, image_url: str = None, footer: str = None,
                         thumbnail_url: str = None, author_name: str = None,
                         author_icon: str = None, fields: list = None):
        """Отправить embed в канал"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return False, "❌ Канал не найден"
            
            embed = discord.Embed(
                title=title[:256] if title else None,
                description=description[:4096] if description else None,
                color=color
            )
            
            if image_url and image_url.strip():
                embed.set_image(url=image_url)
            
            if thumbnail_url and thumbnail_url.strip():
                embed.set_thumbnail(url=thumbnail_url)
            
            if footer and footer.strip():
                embed.set_footer(text=footer[:2048])
            
            if author_name and author_name.strip():
                embed.set_author(name=author_name[:256], icon_url=author_icon if author_icon else None)
            
            if fields:
                for field in fields[:25]:
                    embed.add_field(
                        name=field.get('name', '')[:256],
                        value=field.get('value', '')[:1024],
                        inline=field.get('inline', False)
                    )
            
            await channel.send(embed=embed)
            return True, "✅ Embed отправлен!"
        except Exception as e:
            print(f"❌ Ошибка отправки embed: {e}")
            return False, f"❌ Ошибка: {e}"
    
    async def send_simple_embed(self, interaction: discord.Interaction, title: str, 
                                 description: str, color: int, image_url: str = None):
        """Отправить embed в ответ на interaction"""
        try:
            embed = discord.Embed(
                title=title[:256] if title else None,
                description=description[:4096] if description else None,
                color=color
            )
            if image_url and image_url.strip():
                embed.set_image(url=image_url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


embed_builder_manager = EmbedBuilderManager()