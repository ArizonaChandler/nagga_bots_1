"""Генерация embed со списками участников"""
import discord
from datetime import datetime

def create_registration_embed(main_list: list, reserve_list: list) -> discord.Embed:
    """Создать embed с основным и резервным списками"""
    
    # Основной список
    if main_list:
        main_lines = []
        for i, (user_id, user_name) in enumerate(main_list, 1):
            main_lines.append(f"❌ **{i}.** <@{user_id}> — {user_name}")
        main_text = "\n".join(main_lines)
    else:
        main_text = "*Список пуст*"
    
    # Резервный список
    if reserve_list:
        reserve_lines = []
        for i, (user_id, user_name) in enumerate(reserve_list, 1):
            reserve_lines.append(f"⏳ **{i}.** <@{user_id}> — {user_name}")
        reserve_text = "\n".join(reserve_lines)
    else:
        reserve_text = "*Список пуст*"
    
    # Создаём embed
    embed = discord.Embed(
        title="🎯 **РЕГИСТРАЦИЯ НА CAPT**",
        color=0xff0000,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="❌ **ОСНОВНОЙ СОСТАВ**",
        value=main_text,
        inline=False
    )
    
    embed.add_field(
        name="⏳ **РЕЗЕРВ**",
        value=reserve_text,
        inline=False
    )
    
    # Подсчёт участников для футера
    total = len(main_list) + len(reserve_list)
    embed.set_footer(text=f"👥 Всего участников: {total} • Обновляется автоматически")
    
    return embed