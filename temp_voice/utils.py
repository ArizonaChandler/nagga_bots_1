"""Утилиты для системы временных комнат"""
import re


def format_room_name(name: str) -> str:
    """Отформатировать название комнаты для безопасности"""
    name = re.sub(r'[^\w\sа-яА-Я\-]', '', name)
    if len(name) > 32:
        name = name[:29] + "..."
    return name.strip()