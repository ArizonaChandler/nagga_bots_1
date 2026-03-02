"""MCL Views - Настройки DUAL MCL"""
import discord
from core.menus import BaseMenuView
from core.database import db
from core.config import CONFIG
from core.utils import format_mention
from mcl.modals import SetMclChannelModal, SetDualColorModal

class MclSettingsView(BaseMenuView):
    """Настройки DUAL MCL"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        channel_btn = discord.ui.Button(label="💬 Установить канал", style=discord.ButtonStyle.secondary)
        async def channel_cb(i):
            await i.response.send_modal(SetMclChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)
        
        color_btn = discord.ui.Button(label="🎨 Установить цвета", style=discord.ButtonStyle.secondary)
        async def color_cb(i):
            await i.response.send_modal(SetDualColorModal())
        color_btn.callback = color_cb
        self.add_item(color_btn)
        
        self.add_back_button()