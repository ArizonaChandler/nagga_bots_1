"""Утилиты и проверки прав"""
import re
from core.database import db
from core.config import CONFIG, SUPER_ADMIN_ID

def format_mention(guild, id_str: str, mention_type: str = 'user'):
    if not id_str:
        return "`Не установлено`"
    try:
        if mention_type == 'channel':
            return f"<#{id_str}>"
        elif mention_type == 'role':
            return f"<@&{id_str}>"
        elif mention_type == 'user':
            return f"<@{id_str}>"
        else:
            return f"`{id_str}`"
    except:
        return f"`{id_str}`"

async def get_server_name(guild, server_id: str) -> str:
    if not server_id:
        return "`Не установлен`"
    try:
        if guild and str(guild.id) == server_id:
            return f"**{guild.name}**"
        else:
            return f"`{server_id}`"
    except:
        return f"`{server_id}`"

async def has_access(user_id: str) -> bool:
    return db.user_exists(user_id)

async def is_admin(user_id: str) -> bool:
    return db.is_admin(user_id)

async def is_super_admin(user_id: str) -> bool:
    return user_id == SUPER_ADMIN_ID or db.is_super_admin(user_id)