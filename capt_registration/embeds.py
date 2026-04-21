"""Генерация embed со списками участников"""
import discord
from datetime import datetime
from core.config import CONFIG

def split_list_into_fields(name_prefix: str, items: list, emoji: str, max_length: int = 1000):
    """Разбить длинный список на несколько полей (на всякий случай)"""
    fields = []
    
    if not items:
        return [(f"{emoji} **{name_prefix}**", "*Список пуст*")]
    
    current_text = ""
    start_index = 1
    
    for i, (reg_id, user_id, user_name) in enumerate(items, 1):
        # Короткая версия с номером и тегом
        line = f"`{i:02d}` <@{user_id}>\n"
        
        if len(current_text) + len(line) > max_length:
            field_name = f"{emoji} **{name_prefix}** (часть {len(fields) + 1})"
            fields.append((field_name, current_text))
            current_text = line
            start_index = i
        else:
            current_text += line
    
    if current_text:
        if len(fields) == 0:
            field_name = f"{emoji} **{name_prefix}** ({len(items)})"
        else:
            field_name = f"{emoji} **{name_prefix}** (часть {len(fields) + 1})"
        fields.append((field_name, current_text))
    
    return fields

def create_registration_embed(main_list: list, reserve_list: list, capt_info: dict = None) -> discord.Embed:
    """Создать embed с тегами и номерами участников"""
    
    # Основной список - с номерами
    if main_list:
        main_lines = []
        for i, (_, user_id, _) in enumerate(main_list, 1):
            main_lines.append(f"`{i:02d}` <@{user_id}>")
        main_text = "\n".join(main_lines)
    else:
        main_text = "*Список пуст*"
    
    # Резервный список - с номерами
    if reserve_list:
        reserve_lines = []
        for i, (_, user_id, _) in enumerate(reserve_list, 1):
            reserve_lines.append(f"`{i:02d}` <@{user_id}>")
        reserve_text = "\n".join(reserve_lines)
    else:
        reserve_text = "*Список пуст*"
    
    # Создаём embed
    embed = discord.Embed(
        title="🎯 **РЕГИСТРАЦИЯ НА CAPT**",
        color=0xff0000,
        timestamp=datetime.now()
    )
    
    # Если есть информация о CAPT, добавляем её компактно
    if capt_info:
        info_text = f"👊 {capt_info['enemy']} | ⏰ {capt_info['teleport_time']} | 👤 {capt_info['started_by']}"
        if capt_info['additional_info'] != "Нет":
            info_text += f"\n📝 {capt_info['additional_info']}"
        embed.description = info_text
    
    # Проверяем длину основного списка
    if len(main_text) > 1000:
        main_fields = split_list_into_fields("ОСНОВНОЙ", main_list, "❌")
        for name, value in main_fields:
            embed.add_field(name=name, value=value, inline=False)
    else:
        embed.add_field(
            name=f"❌ **ОСНОВНОЙ** ({len(main_list)})",
            value=main_text,
            inline=False
        )
    
    # Проверяем длину резервного списка
    if len(reserve_text) > 1000:
        reserve_fields = split_list_into_fields("РЕЗЕРВ", reserve_list, "⏳")
        for name, value in reserve_fields:
            embed.add_field(name=name, value=value, inline=False)
    else:
        embed.add_field(
            name=f"⏳ **РЕЗЕРВ** ({len(reserve_list)})",
            value=reserve_text,
            inline=False
        )
    
    # Простой футер
    total = len(main_list) + len(reserve_list)
    family = CONFIG.get('family_name', 'Семья')
    embed.set_footer(text=f"👥 {total} • {family}")
    return embed
    
    return embed