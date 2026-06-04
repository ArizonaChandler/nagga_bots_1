"""Admin Views - Единое меню с навигацией"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import format_mention, get_server_name, is_super_admin, has_access
from core.menus import BaseMenuView
from core.module_views import ModulesControlPanel
from admin.modals import *
from files.core import file_manager
from files.views import FilesView
from events.views import EventInfoView
from core.module_views import ModulesControlPanel


class MainView(BaseMenuView):
    """Главное меню !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Кнопка файлов
        files_btn = discord.ui.Button(
            label="📁 Полезные файлы",
            style=discord.ButtonStyle.secondary,
            emoji="📁",
            row=0
        )
        async def files_cb(i):
            files, total = file_manager.get_files(page=1)
            
            if total == 0:
                await i.response.send_message("📁 **Пока нет доступных файлов**", ephemeral=True)
                return
            
            view = FilesView(str(i.user.id), page=1, previous_view=self, previous_embed=self.get_current_embed())
            await view.send_initial(i)
        files_btn.callback = files_cb
        self.add_item(files_btn)
        
        # Кнопка мероприятий
        events_btn = discord.ui.Button(
            label="📅 Мероприятия",
            style=discord.ButtonStyle.secondary,
            emoji="📅",
            row=0
        )
        async def events_cb(i):
            view = EventInfoView(self.user_id, self.guild, self, self.get_current_embed())
            embed = discord.Embed(
                title="📅 **МЕРОПРИЯТИЯ**",
                description="Информация о сегодняшних мероприятиях",
                color=0x7289da
            )
            await i.response.edit_message(embed=embed, view=view)
        events_btn.callback = events_cb
        self.add_item(events_btn)
    
    def get_current_embed(self):
        embed = discord.Embed(
            title="🤖 **MANAGEMENT SYSTEM**",
            color=0x7289da
        )
        embed.set_footer(text="📁 Полезные файлы доступны всем")
        return embed


class SettingsView(BaseMenuView):
    """Главное меню настроек (!settings)"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # 🌍 Глобальные
        global_btn = discord.ui.Button(
            label="🌍 Глобальные", 
            style=discord.ButtonStyle.secondary, 
            emoji="🌍", 
            row=0
        )
        async def global_cb(i):
            view = GlobalSettingsView(self.user_id, self.guild, self, self.get_current_embed())
            server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
            embed = discord.Embed(
                title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
                description=f"**Текущие настройки:**\n"
                           f"🌍 Сервер: {server_name}",
                color=0x7289da
            )
            await i.response.edit_message(embed=embed, view=view)
        global_btn.callback = global_cb
        self.add_item(global_btn)
        
        # 🎛️ Управление модулями
        modules_btn = discord.ui.Button(
            label="🎛️ Управление модулями",
            style=discord.ButtonStyle.danger,
            emoji="🎛️",
            row=0
        )
        async def modules_cb(i):
            print("🔍 [DEBUG] modules_cb вызван")
            try:
                from core.module_views import ModulesControlPanel
                print("✅ [DEBUG] ModulesControlPanel импортирован")
                embed = discord.Embed(
                    title="🎛️ **УПРАВЛЕНИЕ МОДУЛЯМИ**",
                    description="Включение и выключение систем бота",
                    color=0xff0000
                )
                view = ModulesControlPanel(i.client)
                print("✅ [DEBUG] View создан")
                await i.response.edit_message(embed=embed, view=view)
                print("✅ [DEBUG] Сообщение обновлено")
            except Exception as e:
                print(f"❌ [DEBUG] Ошибка: {e}")
                import traceback
                traceback.print_exc()
        
        # ✅ КНОПКА "НАЗАД"
        back_btn = discord.ui.Button(
            label="◀ Назад",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4
        )
        async def back_cb(i):
            from commands.settings import AdminSettingsView
            embed = discord.Embed(
                title="⚙️ **ПАНЕЛЬ АДМИНИСТРАТОРА**",
                description="Выберите раздел для настройки:",
                color=0x7289da,
                timestamp=datetime.now()
            )
            view = AdminSettingsView(self.user_id, self.guild)
            await i.response.edit_message(embed=embed, view=view)
        back_btn.callback = back_cb
        self.add_item(back_btn)
    
    def get_current_embed(self):
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ СИСТЕМЫ**",
            description="Выберите раздел для настройки:",
            color=0x7289da
        )
        return embed


class AccessView(BaseMenuView):
    """Управление доступом пользователей"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
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
            
            await i.response.edit_message(embed=embed, view=self)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        self.add_back_button()


class AdminView(BaseMenuView):
    """Управление администраторами"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
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
            
            await i.response.edit_message(embed=embed, view=self)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        self.add_back_button()


class GlobalSettingsView(BaseMenuView):
    """Глобальные настройки (только основные)"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # РЯД 0: ОСНОВНЫЕ НАСТРОЙКИ СЕРВЕРА
        server_btn = discord.ui.Button(
            label="🌍 Установить сервер",
            style=discord.ButtonStyle.primary,
            emoji="🌍",
            row=0
        )
        async def server_cb(i):
            await i.response.send_modal(SetServerModal())
        server_btn.callback = server_cb
        self.add_item(server_btn)
        
        # РЯД 1: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
        users_btn = discord.ui.Button(
            label="👥 Управление доступом",
            style=discord.ButtonStyle.secondary,
            emoji="👥",
            row=1
        )
        async def users_cb(i):
            view = AccessView(self.user_id, self.guild, self, await self.get_current_embed())
            embed = discord.Embed(title="👥 **УПРАВЛЕНИЕ ДОСТУПОМ**", color=0x7289da)
            await i.response.edit_message(embed=embed, view=view)
        users_btn.callback = users_cb
        self.add_item(users_btn)
        
        admin_btn = discord.ui.Button(
            label="👑 Управление админами",
            style=discord.ButtonStyle.secondary,
            emoji="👑",
            row=1
        )
        async def admin_cb(i):
            if not await is_super_admin(str(i.user.id)):
                await i.response.send_message("❌ Только супер-администратор", ephemeral=True)
                return
            view = AdminView(self.user_id, self.guild, self, await self.get_current_embed())
            embed = discord.Embed(title="👑 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**", color=0xffd700)
            await i.response.edit_message(embed=embed, view=view)
        admin_btn.callback = admin_cb
        self.add_item(admin_btn)
        
        # РЯД 2: НАСТРОЙКИ НАЗВАНИЯ СЕМЬИ
        family_name_btn = discord.ui.Button(
            label="🏷️ Название семьи",
            style=discord.ButtonStyle.secondary,
            emoji="🏷️",
            row=2
        )
        async def family_name_cb(i):
            await i.response.send_modal(SetFamilyNameModal())
        family_name_btn.callback = family_name_cb
        self.add_item(family_name_btn)

        settings_channel_btn = discord.ui.Button(
            label="🎛️ Канал управления модулями",
            style=discord.ButtonStyle.primary,
            emoji="🎛️",
            row=2
        )
        async def settings_channel_cb(i):
            await i.response.send_modal(SetGlobalSettingsChannelModal())
        settings_channel_btn.callback = settings_channel_cb
        self.add_item(settings_channel_btn)
        
        # КНОПКА НАЗАД
        self.add_back_button(row=3)
    
    async def get_current_embed(self):
        server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
        
        embed = discord.Embed(
            title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
            description="Настройка основных параметров бота",
            color=0x7289da
        )
        
        users_count = len(db.get_users())
        admins_count = len(db.get_admins())
        
        embed.add_field(
            name="👥 Пользователи",
            value=f"Доступ: `{users_count}`\nАдмины: `{admins_count}`",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Система модулей",
            value="Управление вкл/выкл через 🎛️ Управление модулями",
            inline=True
        )
        
        embed.set_footer(text="Настройки каналов производятся после включения модуля")
        return embed