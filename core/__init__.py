from core.database import db
from core.config import CONFIG, load_config, save_config, SUPER_ADMIN_ID
from core.utils import format_mention, get_server_name, has_access, is_admin, is_super_admin
from core.menus import BaseMenuView  # Добавить эту строку