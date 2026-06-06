"""Менеджер модулей — централизованное управление всеми системами бота"""
import discord
from core.database import db
from core.config import CONFIG, save_config


MODULES = {
    "capt": {
        "name": "🎯 CAPT Регистрация",
        "description": "Система регистрации на CAPT",
        "enabled": False,
        "channels": ["capt_reg_main_channel", "capt_reg_reserve_channel", "capt_alert_channel", "capt_log_channel"],
        "settings_channels": ["capt_settings_channel"],
        "initializer": "capt_registration.manager",
        "initialize_method": "initialize_buttons",
        "toggleable": True
    },
    "mcl": {
        "name": "🎯 MCL/ВЗМ Регистрация",
        "description": "Система регистрации на MCL/ВЗМ",
        "enabled": False,
        "channels": ["mcl_reg_main_channel", "mcl_reg_reserve_channel", "mcl_error_channel", "mcl_announcement_channel"],
        "settings_channels": ["mcl_settings_channel"],
        "initializer": "mcl_registration.manager",
        "initialize_method": "initialize_buttons",
        "toggleable": True
    },
    "applications": {
        "name": "📝 Заявки в семью",
        "description": "Система подачи и модерации заявок",
        "enabled": False,
        "channels": ["submit_channel", "applications_channel", "applications_log_channel"],
        "settings_channels": ["applications_settings_channel"],
        "initializer": "applications.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "events": {
        "name": "🔔 Мероприятия",
        "description": "Автоматические напоминания о мероприятиях",
        "enabled": False,
        "channels": ["alarm_channels", "announce_channels"],
        "settings_channels": ["events_settings_channel"],
        "initializer": "events.scheduler",
        "initialize_method": "setup",
        "toggleable": True
    },
    "afk": {
        "name": "🛌 AFK система",
        "description": "Уход в AFK с автоматическим возвратом",
        "enabled": False,
        "channels": ["afk_channel", "afk_log_channel"],
        "settings_channels": ["afk_settings_channel"],
        "initializer": "afk.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "tier": {
        "name": "🌟 Tier система",
        "description": "Повышение уровня (Tier 1/2/3)",
        "enabled": False,
        "channels": ["tier_submit_channel", "tier_applications_channel", "tier_log_channel", "tier_info_channel"],
        "settings_channels": ["tier_settings_channel"],
        "initializer": "tier.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "vacation": {
        "name": "🏖️ Отпуска",
        "description": "Система отпусков с автоматическим возвратом",
        "enabled": False,
        "channels": ["vacation_public_channel", "vacation_applications_channel", "vacation_log_channel"],
        "settings_channels": ["vacation_settings_channel"],
        "initializer": "vacation.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "games": {
        "name": "🎮 Игры",
        "description": "Игры Discord (морской бой и другие)",
        "enabled": False,
        "channels": ["games_rules_channel", "games_lobby_channel", "games_log_channel", "games_category_id"],
        "settings_channels": ["games_settings_channel"],
        "initializer": "games.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "birthday": {
        "name": "🎂 Дни рождения",
        "description": "Система дней рождения с поздравлениями",
        "enabled": False,
        "channels": ["birthday_channel", "birthday_greeting_channel"],
        "settings_channels": ["birthday_settings_channel"],
        "initializer": "birthday.initializer",
        "initialize_method": "setup",
        "toggleable": True
    },
    "advertising": {
        "name": "📢 Авто-реклама",
        "description": "Автоматическая рассылка рекламы",
        "enabled": False,
        "channels": [],
        "settings_channels": ["ad_settings_channel"],
        "initializer": "advertising.core",
        "initialize_method": "setup",
        "toggleable": True
    },
    "files": {
        "name": "📁 Полезные файлы",
        "description": "Хранилище файлов для участников",
        "enabled": True,
        "channels": [],
        "settings_channels": [],
        "initializer": None,
        "toggleable": False
    }
}


class ModuleManager:
    def __init__(self, bot):
        self.bot = bot
        self.settings_channel_id = None
        self.load_modules_state()

    def load_modules_state(self):
        for module_key in MODULES:
            value = db.get_module_setting(module_key)
            if value is not None:
                MODULES[module_key]["enabled"] = value == "1"
            else:
                db.set_module_setting(module_key, "0")
                MODULES[module_key]["enabled"] = False

    def save_module_state(self, module_key: str):
        db.set_module_setting(module_key, "1" if MODULES[module_key]["enabled"] else "0")

    def is_enabled(self, module_key: str) -> bool:
        return MODULES.get(module_key, {}).get("enabled", False)

    async def set_enabled(self, module_key: str, enabled: bool, user_id: str) -> tuple:
        if module_key not in MODULES:
            return False, "Модуль не найден"
        if not MODULES[module_key].get("toggleable", True):
            return False, f"Модуль {MODULES[module_key]['name']} нельзя отключить"
        if MODULES[module_key]["enabled"] == enabled:
            return False, f"Модуль уже {'включён' if enabled else 'выключен'}"

        MODULES[module_key]["enabled"] = enabled
        self.save_module_state(module_key)

        action = "ВКЛЮЧЁН" if enabled else "ВЫКЛЮЧЁН"
        db.log_action(user_id, f"MODULE_{action}", f"{module_key}")

        if enabled:
            await self._enable_module(module_key)
        else:
            await self._disable_module(module_key)

        # Обновляем единую панель настроек
        await self.update_settings_panel()

        return True, f"Модуль **{MODULES[module_key]['name']}** {'включён' if enabled else 'выключен'}"

    async def _enable_module(self, module_key: str):
        module = MODULES[module_key]
        initializer_path = module.get("initializer")
        
        if not initializer_path:
            print(f"⚠️ [MODULE] {module['name']} не имеет инициализатора")
            return
        
        parts = initializer_path.split('.')
        module_name = '.'.join(parts[:-1]) if len(parts) > 1 else initializer_path
        attr_name = parts[-1] if len(parts) > 1 else None
        
        try:
            imported = __import__(module_name, fromlist=[attr_name] if attr_name else [])
            
            if attr_name:
                obj = getattr(imported, attr_name, None)
            else:
                obj = imported
            
            if obj is None:
                print(f"❌ [MODULE] Не найден объект для {module['name']}")
                return
            
            if module_key in ['capt', 'mcl']:
                if hasattr(obj, 'initialize_buttons'):
                    await obj.initialize_buttons(self.bot)
                    print(f"✅ [MODULE] {module['name']} инициализирован")
            else:
                if hasattr(obj, 'initialize_all'):
                    await obj.initialize_all()
                    print(f"✅ [MODULE] {module['name']} инициализирован")
                elif hasattr(obj, 'setup'):
                    await obj.setup(self.bot)
                    print(f"✅ [MODULE] {module['name']} инициализирован")
                else:
                    print(f"❌ [MODULE] У {module['name']} нет метода инициализации")
                    
        except Exception as e:
            print(f"❌ [MODULE] Ошибка инициализации {module['name']}: {e}")
            import traceback
            traceback.print_exc()

    async def _disable_module(self, module_key: str):
        module = MODULES[module_key]
        initializer_path = module.get("initializer")
        
        # 1. Останавливаем фоновые задачи
        if initializer_path:
            parts = initializer_path.split('.')
            module_name = '.'.join(parts[:-1]) if len(parts) > 1 else initializer_path
            attr_name = parts[-1] if len(parts) > 1 else None
            
            try:
                imported = __import__(module_name, fromlist=[attr_name] if attr_name else [])
                
                if attr_name:
                    obj = getattr(imported, attr_name, None)
                else:
                    obj = imported
                
                if obj and hasattr(obj, 'stop'):
                    await obj.stop()
                    print(f"✅ [MODULE] {module['name']} остановлен")
            except Exception as e:
                print(f"⚠️ [MODULE] Ошибка остановки {module['name']}: {e}")
        
        # 2. Отключаем все embed в каналах модуля
        await self._disable_all_embeds(module_key)

    async def _disable_all_embeds(self, module_key: str):
        module = MODULES[module_key]
        all_keys = module.get("channels", []) + module.get("settings_channels", [])
        
        for channel_key in all_keys:
            channel_id = db.get_setting(channel_key)
            
            # === ОБРАБОТКА JSON-МАССИВА ===
            if channel_id and channel_id.startswith('['):
                try:
                    import json
                    channel_list = json.loads(channel_id)
                    if channel_list:
                        channel_id = channel_list[0]  # берём первый канал
                except:
                    pass
            
            if not channel_id or channel_id == 'null' or channel_id == '[]':
                continue
            
            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    continue
            except (ValueError, TypeError):
                print(f"⚠️ [MODULE] Неверный ID канала для {channel_key}: {channel_id}")
                continue
            
            try:
                async for msg in channel.history(limit=50):
                    if msg.author == self.bot.user:
                        # Если есть embed — заменяем его на сообщение об отключении
                        if msg.embeds:
                            # Проверяем, что это наше сообщение (содержит кнопки или специфичный заголовок)
                            if msg.components or self._is_module_embed(msg, module_key):
                                embed = discord.Embed(
                                    title=f"⛔ {module['name']}",
                                    description="**Система отключена администратором**\nОбратитесь к администрации для включения.",
                                    color=0x808080
                                )
                                await msg.edit(embed=embed, view=None)
                                print(f"✅ [MODULE] Отключён embed в #{channel.name} ({channel_key})")
                                break
            except Exception as e:
                print(f"❌ [MODULE] Ошибка отключения {channel_key}: {e}")

    def _is_module_embed(self, msg, module_key: str) -> bool:
        """Проверяет, относится ли embed к данному модулю"""
        if not msg.embeds:
            return False
        
        title = msg.embeds[0].title or ""
        
        # Карта заголовков для каждого модуля
        module_titles = {
            "capt": ["РЕГИСТРАЦИЯ НА CAPT", "CAPT"],
            "mcl": ["РЕГИСТРАЦИЯ НА MCL", "MCL", "ВЗМ"],
            "applications": ["ПОДАЧА ЗАЯВОК", "ЗАЯВКИ В СЕМЬЮ", "ЗАЯВКА"],
            "events": ["МЕРОПРИЯТИЯ", "МП", "НАПОМИНАНИЕ"],
            "afk": ["AFK", "СИСТЕМА AFK"],
            "tier": ["TIER", "СИСТЕМА TIER", "ЗАЯВКИ НА TIER"],
            "vacation": ["ОТПУСК", "СИСТЕМА ОТПУСКОВ"],
            "games": ["МОРСКОЙ БОЙ", "ИГРЫ"],
            "birthday": ["ДНИ РОЖДЕНИЯ", "BIRTHDAY"],
            "advertising": ["АВТО-РЕКЛАМА", "РЕКЛАМА"]
        }
        
        titles = module_titles.get(module_key, [])
        for t in titles:
            if t in title:
                return True
        return False

    async def initialize_all_enabled_modules(self):
        print("📋 [MODULE] Инициализация включённых модулей...")
        for module_key, module in MODULES.items():
            if module["enabled"]:
                print(f"🔍 [MODULE] Пытаюсь инициализировать {module['name']}...")
                await self._enable_module(module_key)
            else:
                print(f"⏭️ [MODULE] {module['name']} выключен, пропускаем")
        print("📋 [MODULE] Инициализация завершена")

    async def update_settings_panel(self):
        """Обновить единую панель настроек (добавить/убрать кнопки модулей)"""
        channel_id = db.get_setting('global_settings_channel')
        if not channel_id:
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return
        
        from core.settings_panel import GlobalSettingsPanel
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.edit(view=GlobalSettingsPanel(self.bot))
                return
        
        embed = discord.Embed(
            title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
            description="Настройка всех модулей бота.\n\n"
                        "Здесь отображаются кнопки только для **включённых** систем.\n"
                        "Чтобы включить/выключить модуль, используйте 🎛️ Управление модулями в !settings.",
            color=0x7289da
        )
        await channel.send(embed=embed, view=GlobalSettingsPanel(self.bot))

    async def restore_global_settings_panel(self):
        """Восстановить глобальную панель настроек после перезапуска"""
        channel_id = db.get_setting('global_settings_channel_id')
        message_id = db.get_setting('global_settings_message_id')
        
        if not channel_id or not message_id or channel_id == 'null' or message_id == 'null':
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(int(message_id))
            
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.\n\n"
                            "Здесь отображаются кнопки только для **включённых** систем.\n"
                            "Чтобы включить/выключить модуль, используйте 🎛️ Управление модулями в !settings.",
                color=0x7289da
            )
            await message.edit(embed=embed, view=GlobalSettingsPanel(self.bot))
            print("✅ Восстановлена глобальная панель настроек")
        except Exception as e:
            print(f"⚠️ Не удалось восстановить панель настроек: {e}")


module_manager = None

async def setup(bot):
    global module_manager
    module_manager = ModuleManager(bot)
    await module_manager.initialize_all_enabled_modules()
    await module_manager.restore_global_settings_panel()
    return module_manager