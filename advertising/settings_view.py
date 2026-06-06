"""Панель управления авто-рекламой с постоянными кнопками"""
import discord
import logging
import os
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from advertising.base import PermanentView

logger = logging.getLogger(__name__)

AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_IMAGE_FILE = "/home/discordbot/discord-bot/ad_image.txt"
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"


class AdSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки авто-рекламы"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        text_btn = discord.ui.Button(label="📝 Установить текст", style=discord.ButtonStyle.primary, emoji="📝", row=0, custom_id="ad_text")
        text_btn.callback = self.set_text
        self.add_item(text_btn)
        
        image_btn = discord.ui.Button(label="🖼️ Установить картинку", style=discord.ButtonStyle.primary, emoji="🖼️", row=0, custom_id="ad_image")
        image_btn.callback = self.set_image
        self.add_item(image_btn)
        
        channel_btn = discord.ui.Button(label="📢 Установить канал", style=discord.ButtonStyle.primary, emoji="📢", row=1, custom_id="ad_channel")
        channel_btn.callback = self.set_channel
        self.add_item(channel_btn)
        
        send_btn = discord.ui.Button(label="🚀 ЗАПУСТИТЬ СЕЙЧАС", style=discord.ButtonStyle.success, emoji="🚀", row=2, custom_id="ad_send")
        send_btn.callback = self.send_ad_now
        self.add_item(send_btn)
        
        show_btn = discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, emoji="📊", row=3, custom_id="ad_show")
        show_btn.callback = self.show_settings
        self.add_item(show_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=1,
            custom_id="games_back_to_global"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.\n\n"
                            "Здесь отображаются кнопки только для **включённых** систем.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)

    async def set_text(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAdTextModal())

    async def set_image(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAdImageModal())

    async def set_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAdChannelModal())

    async def send_ad_now(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            from advertising.core import advertiser
            if not advertiser:
                await interaction.followup.send("❌ Ошибка: рекламная система не инициализирована", ephemeral=True)
                return
            channel_id = None
            try:
                with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                    channel_id = f.read().strip()
            except:
                pass
            if not channel_id:
                await interaction.followup.send("❌ Сначала настройте канал для отправки рекламы!", ephemeral=True)
                return
            await interaction.followup.send("🔄 Отправка рекламы...", ephemeral=True)
            from datetime import datetime
            await advertiser.send_ad(datetime.now())
        except Exception as e:
            logger.error(f"Ошибка при запуске рекламы: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 ТЕКУЩИЕ НАСТРОЙКИ АВТО-РЕКЛАМЫ", color=0x00ff00)
        guild = interaction.guild
        try:
            with open(AD_TEXT_FILE, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            embed.add_field(name="📝 Текст", value=f"```\n{text[:200]}{'...' if len(text) > 200 else ''}\n```", inline=False)
        except:
            embed.add_field(name="📝 Текст", value="❌ Не установлен", inline=False)
        try:
            with open(AD_IMAGE_FILE, 'r', encoding='utf-8') as f:
                image_url = f.read().strip()
            if image_url:
                embed.add_field(name="🖼️ Картинка", value=f"[Ссылка]({image_url})", inline=True)
            else:
                embed.add_field(name="🖼️ Картинка", value="❌ Нет", inline=True)
        except:
            embed.add_field(name="🖼️ Картинка", value="❌ Нет", inline=True)
        try:
            with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                channel_id = f.read().strip()
            if channel_id:
                channel_mention = format_mention(guild, channel_id, 'channel')
                embed.add_field(name="📢 Канал", value=channel_mention, inline=True)
            else:
                embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        except:
            embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        embed.add_field(name="⏱️ Интервал", value="65 минут", inline=True)
        from advertising.core import advertiser
        if advertiser and advertiser.last_sent_time:
            from datetime import timedelta
            last = advertiser.last_sent_time.strftime("%d.%m.%Y %H:%M")
            next_time = advertiser.last_sent_time + timedelta(minutes=65)
            next_str = next_time.strftime("%H:%M")
            embed.add_field(name="🕐 Последняя отправка", value=last, inline=True)
            embed.add_field(name="⏰ Следующая", value=f"~{next_str} МСК", inline=True)
        else:
            embed.add_field(name="🕐 Статус", value="⏳ Ожидание первой отправки", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetAdTextModal(discord.ui.Modal, title="📝 УСТАНОВИТЬ ТЕКСТ РЕКЛАМЫ"):
    text = discord.ui.TextInput(label="Текст рекламы", placeholder="Введите текст рекламного сообщения", style=discord.TextStyle.paragraph, max_length=1000, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            with open(AD_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(self.text.value)
            embed = discord.Embed(title="✅ Текст рекламы сохранен", description=f"```\n{self.text.value[:200]}{'...' if len(self.text.value) > 200 else ''}\n```", color=0x00ff00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAdImageModal(discord.ui.Modal, title="🖼️ УСТАНОВИТЬ КАРТИНКУ"):
    url = discord.ui.TextInput(label="URL картинки", placeholder="https://example.com/image.jpg", max_length=500, required=False)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        if self.url.value and not (self.url.value.startswith('http://') or self.url.value.startswith('https://')):
            await interaction.response.send_message("❌ URL должен начинаться с http:// или https://", ephemeral=True)
            return
        try:
            with open(AD_IMAGE_FILE, 'w', encoding='utf-8') as f:
                f.write(self.url.value or "")
            if self.url.value:
                embed = discord.Embed(title="✅ URL картинки сохранен", description=self.url.value, color=0x00ff00)
                embed.set_image(url=self.url.value)
            else:
                embed = discord.Embed(title="✅ Картинка удалена", description="Теперь реклама будет отправляться без картинки", color=0x00ff00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAdChannelModal(discord.ui.Modal, title="📢 УСТАНОВИТЬ КАНАЛ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            with open(AD_CHANNEL_FILE, 'w', encoding='utf-8') as f:
                f.write(self.channel_id.value)
            await interaction.response.send_message(f"✅ Канал для рекламы установлен: `{self.channel_id.value}`\n⚠️ Убедитесь, что у пользовательского токена есть доступ к этому каналу.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)