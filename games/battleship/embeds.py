"""Embed для морского боя"""
import discord
from datetime import datetime
from core.database import db


def get_rules_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎮 **МОРСКОЙ БОЙ**",
        description="Классическая игра на уничтожение кораблей противника.",
        color=0x00bfff
    )
    embed.add_field(
        name="📜 **ПРАВИЛА**",
        value="└ У каждого игрока поле 10×10 с 10 кораблями\n"
              "└ Цель: уничтожить все корабли противника\n"
              "└ Корабли расставляются автоматически",
        inline=False
    )
    embed.add_field(
        name="🎯 **КАК СТРЕЛЯТЬ**",
        value="└ Выберите ряд (A-J) и колонку (1-10)\n"
              "└ При попадании — ход продолжается\n"
              "└ При промахе — ход переходит к противнику",
        inline=False
    )
    embed.add_field(
        name="⏭️ **ПРОПУСК ХОДА**",
        value="└ После 3 пропусков подряд — поражение",
        inline=False
    )
    embed.add_field(
        name="🏆 **РЕЙТИНГ**",
        value="└ За победу +1 в статистику\n"
              "└ Топ-3 игрока в канале лобби",
        inline=False
    )
    embed.set_footer(text="Управление через личные сообщения с ботом")
    return embed


def get_top_embed() -> discord.Embed:
    top = db.get_top_players(3)
    embed = discord.Embed(
        title="🏆 **ТОП ИГРОКОВ**",
        color=discord.Color.gold()
    )
    medals = ["🥇", "🥈", "🥉"]
    if not top:
        embed.description = "✨ Пока нет игроков. Сыграйте первую игру!"
    else:
        for i, (name, wins, losses, played) in enumerate(top):
            winrate = (wins / played * 100) if played > 0 else 0
            embed.add_field(
                name=f"{medals[i]} {name}",
                value=f"🏅 Побед: {wins}\n💀 Поражений: {losses}\n📈 Винрейт: {winrate:.1f}%\n🎮 Игр: {played}",
                inline=False
            )
    embed.set_footer(text="Обновляется после каждой игры")
    return embed


def get_lobby_embed(waiting_list: list, active_games: list) -> discord.Embed:
    """Создать embed для лобби с очередью и активными играми"""
    waiting_names = [f"👤 {u.display_name}" for u in waiting_list]
    waiting_text = "\n".join(waiting_names) if waiting_names else "*Никого нет*"
    
    active_text = "\n".join(active_games) if active_games else "*Нет активных игр*"
    
    embed = discord.Embed(
        title="🎮 МОРСКОЙ БОЙ",
        color=0x00bfff,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="⏳ В ОЧЕРЕДИ",
        value=f"━━━━━━━━━━━━━━━━━━━━━\n{waiting_text}\n━━━━━━━━━━━━━━━━━━━━━\n**Всего: {len(waiting_list)}**",
        inline=False
    )
    embed.add_field(
        name="⚔️ АКТИВНЫЕ ИГРЫ",
        value=f"━━━━━━━━━━━━━━━━━━━━━\n{active_text}\n━━━━━━━━━━━━━━━━━━━━━\n**Всего: {len(active_games)}**",
        inline=False
    )
    embed.set_footer(text="Нажмите «Войти в очередь» чтобы найти соперника")
    return embed