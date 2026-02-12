"""Admin Views - Кнопочный интерфейс для администраторов"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import format_mention, get_server_name, is_super_admin, has_access
from capt.modals import CaptModal
from mcl.core import dual_mcl_core
from mcl.modals import SetMclChannelModal, SetDualColorModal
from admin.modals import *
from files.core import file_manager
from files.views import FilesView

class MainView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        
        if db.user_exists(user_id):
            capt_btn = discord.ui.Button(
                label="🚨 CAPT",
                style=discord.ButtonStyle.danger,
                emoji="🚨",
                row=0
            )
            async def capt_cb(i):
                if await has_access(str(i.user.id)):
                    await i.response.send_modal(CaptModal())
            capt_btn.callback = capt_cb
            self.add_item(capt_btn)
            
            mcl_btn = discord.ui.Button(
                label="🎨 DUAL MCL",
                style=discord.ButtonStyle.primary,
                emoji="🎨",
                row=0
            )
            async def mcl_cb(i):
                if not await has_access(str(i.user.id)):
                    return
                if not CONFIG['channel_id']:
                    await i.response.send_message("❌ Канал MCL не настроен", ephemeral=True)
                    return
                await dual_mcl_core.send_dual(i)
            mcl_btn.callback = mcl_cb
            self.add_item(mcl_btn)
            
            files_btn = discord.ui.Button(
                label="📁 Полезные файлы",
                style=discord.ButtonStyle.secondary,
                emoji="📁",
                row=1
            )
            async def files_cb(i):
                if not await has_access(str(i.user.id)):
                    return
                
                files, total = file_manager.get_files(page=1)
                
                if total == 0:
                    await i.response.send_message("📁 Пока нет доступных файлов", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="📁 **ПОЛЕЗНЫЕ ФАЙЛЫ**",
                    description=f"Всего доступно: **{total}** файлов\n"
                               f"Выберите файл для скачивания:",
                    color=0x00ff00
                )
                
                view = FilesView(str(i.user.id), page=1)
                await i.response.send_message(embed=embed, view=view, ephemeral=True)
            
            files_btn.callback = files_cb
            self.add_item(files_btn)


class SettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        capt_btn = discord.ui.Button(label="🚨 CAPT", style=discord.ButtonStyle.secondary, emoji="🚨", row=0)
        async def capt_cb(i):
            view = CaptSettingsView(self.user_id, self.guild)
            embed = discord.Embed(
                title="🚨 **НАСТРОЙКИ CAPT**",
                description=f"**Текущие настройки:**\n"
                           f"🎭 Роль: {format_mention(self.guild, CONFIG.get('capt_role_id'), 'role')}\n"
                           f"💬 Чат ошибок: {format_mention(self.guild, CONFIG.get('capt_channel_id'), 'channel')}",
                color=0xff0000
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        capt_btn.callback = capt_cb
        self.add_item(capt_btn)
        
        mcl_btn = discord.ui.Button(label="🎨 MCL", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
        async def mcl_cb(i):
            view = MclSettingsView(self.user_id, self.guild)
            colors = db.get_dual_colors()
            embed = discord.Embed(
                title="🎨 **НАСТРОЙКИ DUAL MCL**",
                description=f"**Текущие настройки:**\n"
                           f"💬 Канал: {format_mention(self.guild, CONFIG.get('channel_id'), 'channel')}\n"
                           f"🎨 Цвета: `{colors[0]}/{colors[1]}`",
                color=0x00ff00
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        mcl_btn.callback = mcl_cb
        self.add_item(mcl_btn)
        
        global_btn = discord.ui.Button(label="🌍 Глобальные", style=discord.ButtonStyle.secondary, emoji="🌍", row=0)
        async def global_cb(i):
            view = GlobalSettingsView(self.user_id, self.guild)
            server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
            embed = discord.Embed(
                title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
                description=f"**Текущие настройки:**\n"
                           f"🌍 Сервер: {server_name}",
                color=0x7289da
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        global_btn.callback = global_cb
        self.add_item(global_btn)


class CaptSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        role_btn = discord.ui.Button(label="🎭 Установить роль", style=discord.ButtonStyle.secondary)
        async def role_cb(i):
            await i.response.send_modal(SetRoleModal())
        role_btn.callback = role_cb
        self.add_item(role_btn)
        
        channel_btn = discord.ui.Button(label="💬 Установить чат ошибок", style=discord.ButtonStyle.secondary)
        async def channel_cb(i):
            await i.response.send_modal(SetCaptChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)


class MclSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
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


class GlobalSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        server_btn = discord.ui.Button(label="🌍 Установить сервер", style=discord.ButtonStyle.secondary)
        async def server_cb(i):
            await i.response.send_modal(SetServerModal())
        server_btn.callback = server_cb
        self.add_item(server_btn)
        
        users_btn = discord.ui.Button(label="👥 Управление доступом", style=discord.ButtonStyle.secondary)
        async def users_cb(i):
            view = AccessView(self.user_id, self.guild)
            embed = discord.Embed(title="👥 **УПРАВЛЕНИЕ ДОСТУПОМ**", color=0x7289da)
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        users_btn.callback = users_cb
        self.add_item(users_btn)
        
        admin_btn = discord.ui.Button(label="👑 Управление админами", style=discord.ButtonStyle.secondary)
        async def admin_cb(i):
            if not await is_super_admin(str(i.user.id)):
                await i.response.send_message("❌ Только супер-администратор", ephemeral=True)
                return
            view = AdminView(self.user_id, self.guild)
            embed = discord.Embed(title="👑 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**", color=0xffd700)
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        admin_btn.callback = admin_cb
        self.add_item(admin_btn)


class AccessView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        add_btn = discord.ui.Button(label="➕ Добавить пользователя", style=discord.ButtonStyle.success)
        async def add_cb(i):
            await i.response.send_modal(AddUserModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        remove_btn = discord.ui.Button(label="➖ Удалить пользователя", style=discord.ButtonStyle.danger)
        async def remove_cb(i):
            await i.response.send_modal(RemoveUserModal())
        remove_btn.callback = remove_cb
        self.add_item(remove_btn)
        
        list_btn = discord.ui.Button(label="📋 Список пользователей", style=discord.ButtonStyle.secondary)
        async def list_cb(i):
            users = db.get_users_with_details()
            embed = discord.Embed(
                title="📋 **ПОЛЬЗОВАТЕЛИ С ДОСТУПОМ**",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            if users:
                lines = []
                for uid, username, added_by, added_at, last_used, is_admin, is_super in users[:25]:
                    mention = format_mention(self.guild, uid, 'user')
                    if is_super:
                        icon = "👑👑"
                        role = "**Супер-админ**"
                    elif is_admin:
                        icon = "👑"
                        role = "Админ"
                    else:
                        icon = "👤"
                        role = "Пользователь"
                    
                    lines.append(f"{icon} {mention} • {role}")
                
                embed.description = "\n".join(lines)
                
                total = len(users)
                admins_count = sum(1 for u in users if u[5])
                supers_count = sum(1 for u in users if u[6])
                
                embed.set_footer(text=f"Всего: {total} • Админов: {admins_count} • Супер-админов: {supers_count}")
            else:
                embed.description = "❌ Нет пользователей с доступом"
            
            await i.response.send_message(embed=embed, ephemeral=True)
        list_btn.callback = list_cb
        self.add_item(list_btn)


class AdminView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        add_btn = discord.ui.Button(label="➕ Добавить администратора", style=discord.ButtonStyle.success)
        async def add_cb(i):
            await i.response.send_modal(AddAdminModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        remove_btn = discord.ui.Button(label="➖ Удалить администратора", style=discord.ButtonStyle.danger)
        async def remove_cb(i):
            await i.response.send_modal(RemoveAdminModal())
        remove_btn.callback = remove_cb
        self.add_item(remove_btn)
        
        list_btn = discord.ui.Button(label="📋 Список админов", style=discord.ButtonStyle.secondary)
        async def list_cb(i):
            admins = db.get_admins()
            embed = discord.Embed(
                title="👑 **АДМИНИСТРАТОРЫ**",
                color=0xffd700,
                timestamp=datetime.now()
            )
            
            if admins:
                lines = []
                for admin_id, added_by, added_at, is_super, username in admins:
                    mention = format_mention(self.guild, admin_id, 'user')
                    if is_super:
                        lines.append(f"👑👑 {mention} • **Супер-админ**")
                    else:
                        lines.append(f"👑 {mention}")
                embed.description = "\n".join(lines)
                embed.set_footer(text=f"Всего: {len(admins)}")
            else:
                embed.description = "❌ Нет администраторов"
            
            await i.response.send_message(embed=embed, ephemeral=True)
        list_btn.callback = list_cb
        self.add_item(list_btn)
