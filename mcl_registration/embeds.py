"""Embed для MCL регистрации"""
import discord
from datetime import datetime
from core.database import db


def split_list_into_fields(name_prefix: str, items: list, emoji: str, max_length: int = 1000):
    fields = []
    if not items:
        return [(f"{emoji} **{name_prefix}**", "*Список пуст*")]
    
    current_text = ""
    for i, (reg_id, user_id, user_name) in enumerate(items, 1):
        line = f"`{i:02d}` <@{user_id}>\n"
        if len(current_text) + len(line) > max_length:
            field_name = f"{emoji} **{name_prefix}** (часть {len(fields) + 1})"
            fields.append((field_name, current_text))
            current_text = line
        else:
            current_text += line
    
    if current_text:
        field_name = f"{emoji} **{name_prefix}** ({len(items)})" if not fields else f"{emoji} **{name_prefix}** (часть {len(fields) + 1})"
        fields.append((field_name, current_text))
    
    return fields


def create_registration_embed(main_list: list, reserve_list: list, session_info: dict = None) -> discord.Embed:
    """Создать embed с информацией о регистрации"""
    if main_list:
        main_lines = [f"`{i:02d}` <@{user_id}>" for i, (_, user_id, _) in enumerate(main_list, 1)]
        main_text = "\n".join(main_lines)
    else:
        main_text = "*Список пуст*"
    
    if reserve_list:
        reserve_lines = [f"`{i:02d}` <@{user_id}>" for i, (_, user_id, _) in enumerate(reserve_list, 1)]
        reserve_text = "\n".join(reserve_lines)
    else:
        reserve_text = "*Список пуст*"
    
    embed = discord.Embed(
        title="🎯 **РЕГИСТРАЦИЯ НА MCL/ВЗМ**",
        color=0xffa500,
        timestamp=datetime.now()
    )
    
    if session_info:
        info_text = f"📋 {session_info.get('event_name', 'Мероприятие')} | ⏰ {session_info.get('event_time', 'Время не указано')} | 👤 {session_info.get('started_by_name', 'Организатор')}"
        if session_info.get('additional_info'):
            info_text += f"\n📝 {session_info['additional_info']}"
        embed.description = info_text
    
    if len(main_text) > 1000:
        for name, value in split_list_into_fields("ОСНОВНОЙ", main_list, "❌"):
            embed.add_field(name=name, value=value, inline=False)
    else:
        embed.add_field(name=f"❌ **ОСНОВНОЙ** ({len(main_list)})", value=main_text, inline=False)
    
    if len(reserve_text) > 1000:
        for name, value in split_list_into_fields("РЕЗЕРВ", reserve_list, "⏳"):
            embed.add_field(name=name, value=value, inline=False)
    else:
        embed.add_field(name=f"⏳ **РЕЗЕРВ** ({len(reserve_list)})", value=reserve_text, inline=False)
    
    embed.set_footer(text=f"👥 Всего: {len(main_list) + len(reserve_list)}")
    return embed