"""Менеджер модулей — централизованное управление всеми системами бота"""
import discord
from core.database import db
from core.config import CONFIG, save_config


MODULES = {
    "capt": {
        "name": "🎯 CAPT Регистрация",
        "description": "Система регистрации на CAPT с рассылкой в ЛС",
        "enabled": False,
        "channels": ["capt_reg_main_channel", "capt_reg_reserve_channel", "capt_alert_channel", "capt_log_channel"],
        "settings_channels": ["capt_settings_channel"],
        "initializer": "capt_registration.manager.capt_reg_manager",
        "initialize_method": "initialize_buttons",
        "toggleable": True
    },
    "mcl": {
        "name": "🎯 MCL/ВЗМ Регистрация",
        "description": "Система регистрации на MCL/ВЗМ с рассылкой",
        "enabled": False,
        "channels": ["mcl_reg_main_channel", "mcl_reg_reserve_channel", "mcl_error_channel", "mcl_announcement_channel"],
        "settings_channels": ["mcl_settings_channel"],
        "initializer": "mcl_registration.manager.mcl_manager",
        "initialize_method": "initialize_buttons",
        "toggleable": True
    },
    "applications": {
        "name": "📝 Заявки в семью",
        "description": "Система подачи и модерации заявок",
        "enabled": False,
        "channels": ["submit_channel", "applications_channel", "applications_log_channel"],
        "settings_channels": ["applications_settings_channel"],
        "initializer": "applications.initializer.initializer",
        "initialize_method": "initialize_all",
        "toggleable": True
    },
    "events": {
        "name": "🔔 Мероприятия",
        "description": "Автоматические напоминания о мероприятиях",
        "enabled": False,
        "channels": ["alarm_channels", "announce_channels"],
        "settings_channels": ["events_settings_channel"],
        "initializer": "events.scheduler.scheduler",
        "initialize_method": "start",
        "toggleable": True
    },
    "afk": {
        "name": "🛌 AFK система",
        "description": "Уход в AFK с автоматическим возвратом",
        "enabled": False,
        "channels": ["afk_channel", "afk_log_channel"],
        "settings_channels": ["afk_settings_channel"],
        "initializer": "afk.initializer.initializer",
        "initialize_method": "initialize_all",
        "toggleable": True
    },
    "tier": {
        "name": "🌟 Tier система",
        "description": "Повышение уровня (Tier 1/2/3)",
        "enabled": False,
        "channels": ["tier_submit_channel", "tier_applications_channel", "tier_log_channel", "tier_info_channel"],
        "settings_channels": ["tier_settings_channel"],
        "initializer": "tier.initializer.initializer",
        "initialize_method": "initialize_all",
        "toggleable": True
    },
    "vacation": {
        "name": "🏖️ Отпуска",
        "description": "Система отпусков с автоматическим возвратом",
        "enabled": False,
        "channels": ["vacation_public_channel", "vacation_applications_channel", "vacation_log_channel"],
        "settings_channels": ["vacation_settings_channel"],
        "initializer": "vacation.initializer.initializer",
        "initialize_method": "initialize_all",
        "toggleable": True
    },
    "games": {
        "name": "🎮 Игры",
        "description": "Игры Discord (морской бой и другие)",
        "enabled": False,
        "channels": ["games_rules_channel", "games_lobby_channel", "games_log_channel", "games_category_id"],
        "settings_channels": ["games_settings_channel"],
        "initializer": "games.manager.game_manager",
        "initialize_method": "initialize",
        "toggleable": True
    },
    "birthday": {
        "name": "🎂 Дни рождения",
        "description": "Система дней рождения с поздравлениями",
        "enabled": False,
        "channels": ["birthday_channel", "birthday_greeting_channel"],
        "settings_channels": ["birthday_settings_channel"],
        "initializer": "birthday.initializer.initializer",
        "initialize_method": "initialize_all",
        "toggleable": True
    },
    "advertising": {
        "name": "📢 Авто-реклама",
        "description": "Автоматическая рассылка рекламы",
        "enabled": False,
        "channels": [],
        "settings_channels": ["ad_settings_channel"],
        "initializer": "advertising.core.advertiser",
        "initialize_method": "initialize_settings_channel",
        "toggleable": True
    },
    "server_stats": {
        "name": "📊 Статистика сервера",
        "description": "Сбор и отображение статистики",
        "enabled": False,
        "channels": ["stats_channel"],
        "settings_channels": ["stats_settings_channel"],
        "initializer": "server_stats.stat_collector.collector",
        "initialize_method": "start",
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

        return True, f"Модуль **{MODULES[module_key]['name']}** {'включён' if enabled else 'выключен'}"

    async def _enable_module(self, module_key: str):
        module = MODULES[module_key]
        initializer_path = module.get("initializer")
        initialize_method = module.get("initialize_method", "initialize_all")
        if initializer_path:
            await self._call_module_method(initializer_path, initialize_method)

    async def _disable_module(self, module_key: str):
        await self._disable_all_embeds(module_key)

    async def _call_module_method(self, module_path: str, method_name: str):
        """Универсальный вызов метода модуля с передачей bot если нужно"""
        try:
            parts = module_path.split('.')
            module_name = '.'.join(parts[:-1])
            attr_name = parts[-1]
            
            imported = __import__(module_name, fromlist=[attr_name])
            instance = getattr(imported, attr_name, None)
            
            if instance and hasattr(instance, method_name):
                method = getattr(instance, method_name)
                
                # Проверяем сигнатуру метода
                import inspect
                sig = inspect.signature(method)
                
                # Если метод требует аргумент 'bot', передаём его
                if 'bot' in sig.parameters:
                    await method(self.bot)
                else:
                    await method()
                
                print(f"✅ [MODULE] {module_path}.{method_name}() вызван")
        except Exception as e:
            print(f"❌ [MODULE] Ошибка вызова {method_name} для {module_path}: {e}")
            import traceback
            traceback.print_exc()

    async def _disable_all_embeds(self, module_key: str):
        module = MODULES[module_key]
        all_keys = module.get("channels", []) + module.get("settings_channels", [])
        for channel_key in all_keys:
            channel_id = db.get_setting(channel_key)
            if not channel_id:
                continue
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                continue
            try:
                async for msg in channel.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        if not msg.components or len(msg.components) == 0:
                            await msg.edit(
                                embed=discord.Embed(
                                    title=f"{module['name']}",
                                    description="⛔ **Система отключена администратором**\nОбратитесь к администрации для включения.",
                                    color=0x808080
                                ),
                                view=None
                            )
                            break
            except Exception as e:
                print(f"❌ [MODULE] Ошибка отключения {channel_key}: {e}")

    async def initialize_all_enabled_modules(self):
        print("📋 [MODULE] Инициализация включённых модулей...")
        for module_key, module in MODULES.items():
            if module["enabled"]:
                initializer_path = module.get("initializer")
                initialize_method = module.get("initialize_method", "initialize_all")
                if initializer_path:
                    await self._call_module_method(initializer_path, initialize_method)
                    print(f"✅ [MODULE] {module['name']} инициализирован")
        print("📋 [MODULE] Инициализация завершена")


module_manager = None

async def setup(bot):
    global module_manager
    module_manager = ModuleManager(bot)
    await module_manager.initialize_all_enabled_modules()
    return module_manager