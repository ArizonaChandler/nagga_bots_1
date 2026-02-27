"""Auto Advertising Views - Интерфейс настроек"""
import discord
from datetime import datetime
from core.database import db
from core.menus import BaseMenuView

class AdSettingsView(BaseMenuView):
    """Меню настроек авто-рекламы"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        print("🔵 [AdSettingsView] __init__ started")
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Информационное сообщение
        info_embed = discord.Embed(
            title="📢 Авто-реклама",
            description="Используйте слэш-команды для настройки:\n\n"
                       "`/ad_text` - текст рекламы\n"
                       "`/ad_channel` - канал отправки\n"
                       "`/ad_interval` - интервал (мин)\n"
                       "`/ad_sleep` - режим сна\n"
                       "`/ad_image` - URL картинки\n"
                       "`/ad_status` - статус настроек\n"
                       "`/ad_toggle` - вкл/выкл",
            color=0x00ff00
        )
        
        # Кнопка статуса
        status_btn = discord.ui.Button(
            label="📊 Статус",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=0
        )
        async def status_cb(i):
            settings = db.get_active_ad()
            
            embed = discord.Embed(
                title="📊 Статус авто-рекламы",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            if settings:
                embed.add_field(name="📝 Текст", value=settings['message_text'][:100] + "...", inline=False)
                embed.add_field(name="📢 Канал", value=f"<#{settings['channel_id']}>" if settings['channel_id'] else "❌ Не установлен", inline=True)
                embed.add_field(name="⏱️ Интервал", value=f"{settings['interval_minutes']} мин", inline=True)
                embed.add_field(name="😴 Сон", value=f"{settings['sleep_start']} - {settings['sleep_end']}", inline=True)
                embed.add_field(name="🖼️ Картинка", value="✅ Есть" if settings.get('image_url') else "❌ Нет", inline=True)
                embed.add_field(name="🔘 Статус", value="✅ Активна" if settings.get('is_active') else "❌ Неактивна", inline=True)
            else:
                embed.description = "❌ Настройки не найдены"
            
            await i.response.edit_message(embed=embed, view=self)
        status_btn.callback = status_cb
        self.add_item(status_btn)
        
        # Кнопка помощи
        help_btn = discord.ui.Button(
            label="❓ Помощь",
            style=discord.ButtonStyle.secondary,
            emoji="❓",
            row=0
        )
        async def help_cb(i):
            await i.response.edit_message(embed=info_embed, view=self)
        help_btn.callback = help_cb
        self.add_item(help_btn)
        
        self.add_back_button()
        print("🔵 [AdSettingsView] __init__ completed")