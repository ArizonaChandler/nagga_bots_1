"""Генерация embed со списками участников"""
import discord
from datetime import datetime

def create_registration_embed(main_list: list, reserve_list: list) -> discord.Embed:
    """Создать embed с основным и резервным списками"""
    
    # Форматируем основной список
    main_text = ""
    if main_list:
        for i, (user_id, user_name) in enumerate(main_list, 1):
            main_text += f"{i}. <@{user_id}> — {user_name}\n"
    else:
        main_text = "❌ Пока нет участников"
    
    # Форматируем резервный список
    reserve_text = ""
    if reserve_list:
        for i, (user_id, user_name) in enumerate(reserve_list, 1):
            reserve_text += f"{i}. <@{user_id}> — {user_name}\n"
    else:
        reserve_text = "⏳ Пока нет участников"
    
    # Создаём embed
    embed = discord.Embed(
        title="🎯 **РЕГИСТРАЦИЯ НА CAPT**",
        color=0xff0000,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🔴 **ОСНОВНОЙ СОСТАВ**",
        value=main_text,
        inline=False
    )
    
    embed.add_field(
        name="🟡 **РЕЗЕРВ**",
        value=reserve_text,
        inline=False
    )
    
    # Статистика
    total = len(main_list) + len(reserve_list)
    embed.add_field(
        name="📊 **Статистика**",
        value=f"👥 Всего: **{total}**\n"
              f"🔴 Основной: **{len(main_list)}**\n"
              f"🟡 Резерв: **{len(reserve_list)}**",
        inline=False
    )
    
    embed.set_footer(text="Обновляется автоматически • Нажмите кнопки для участия")
    return embed