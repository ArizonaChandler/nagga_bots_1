"""Утилиты для системы временных комнат"""
import re


def format_room_name(name: str) -> str:
    """Отформатировать название комнаты для безопасности"""
    # Удаляем недопустимые символы
    name = re.sub(r'[^\w\sа-яА-Я\-]', '', name)
    # Ограничиваем длину
    if len(name) > 32:
        name = name[:29] + "..."
    return name.strip()