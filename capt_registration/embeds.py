"""Генерация embed со списками участников"""
import discord
from datetime import datetime

def split_list_into_fields(name_prefix: str, items: list, emoji: str, max_length: int = 1000):
    """Разбить длинный список на несколько полей"""
    fields = []
    
    if not items:
        return [(f"{emoji} **{name_prefix}**", "*Список пуст*")]
    
    current_text = ""
    current_count = 0
    start_index = 1
    
    for i, (reg_id, user_id, user_name) in enumerate(items, 1):
        line = f"{emoji} **{i}.** <@{user_id}> — {user_name}\n"
        
        if len(current_text) + len(line) > max_length:
            # Добавляем текущее поле
            field_name = f"{emoji} **{name_prefix}** (часть {len(fields) + 1})"
            fields.append((field_name, current_text))
            
            # Начинаем новое поле
            current_text = line
            start_index = i
        else:
            current_text += line
    
    # Добавляем последнее поле
    if current_text:
        if len(fields) == 0:
            field_name = f"{emoji} **{name_prefix}** ({len(items)})"
        else:
            field_name = f"{emoji} **{name_prefix}** (часть {len(fields) + 1}, {len(items)})"
        fields.append((field_name, current_text))
    
    return fields

def create_registration_embed(main_list: list, reserve_list: list, capt_info: dict = None) -> discord.Embed:
    """Создать embed с основным и резервным списками и информацией о CAPT"""
    
    # Создаём embed
    embed = discord.Embed(
        title="🎯 **РЕГИСТРАЦИЯ НА CAPT**",
        color=0xff0000,
        timestamp=datetime.now()
    )
    
    # Если есть информация о CAPT, добавляем её в начало
    if capt_info:
        info_text = f"👊 **Противник:** {capt_info['enemy']}\n"
        info_text += f"⏰ **Телепорт:** {capt_info['teleport_time']} МСК\n"
        if capt_info['additional_info'] != "Нет":
            info_text += f"📝 **Доп:** {capt_info['additional_info']}\n"
        info_text += f"👤 **Набрал:** {capt_info['started_by']}"
        
        embed.description = info_text
        embed.add_field(name="\u200b", value="—" * 30, inline=False)
    
    # Разбиваем основной список на поля
    main_fields = split_list_into_fields("ОСНОВНОЙ СОСТАВ", main_list, "❌")
    for name, value in main_fields:
        embed.add_field(name=name, value=value, inline=False)
    
    # Разбиваем резервный список на поля
    reserve_fields = split_list_into_fields("РЕЗЕРВ", reserve_list, "⏳")
    for name, value in reserve_fields:
        embed.add_field(name=name, value=value, inline=False)
    
    # Подсчёт участников для футера
    total = len(main_list) + len(reserve_list)
    embed.set_footer(text=f"👥 Всего участников: {total} • Обновляется автоматически")
    
    return embed