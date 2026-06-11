"""Менеджер игр"""
import discord
import uuid
import asyncio
import json
import logging
from datetime import datetime
from core.database import db
from games.battleship.game import BattleshipGame
from games.battleship.embeds import get_top_embed
from games.battleship.views import GameLobbyView

logger = logging.getLogger(__name__)


class GameManager:
    """Управление всеми играми"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.waiting_players = {}
        self.player_games = {}
        self.log_channel_id = None
        self.lobby_channel_id = None

    async def initialize(self):
        """Восстановить игры после перезапуска"""
        logger.info("🔄 Восстановление активных игр...")
        print("🎮 [Games] Восстановление активных игр...")

        self.log_channel_id = db.get_setting('games_log_channel')
        self.lobby_channel_id = db.get_setting('games_lobby_channel')

        active_games = db.get_all_active_games()
        restored_count = 0

        for game_data in active_games:
            try:
                game_type = game_data['game_type']
                if game_type == "battleship":
                    game = BattleshipGame.from_state(game_data, self.bot)
                    if game:
                        self.active_games[game_data['game_id']] = game
                        self.player_games[str(game.player1.id)] = game_data['game_id']
                        self.player_games[str(game.player2.id)] = game_data['game_id']
                        restored_count += 1
                        logger.info(f"✅ Восстановлена игра {game_data['game_id']}")
                    else:
                        db.delete_active_game(game_data['game_id'])
            except Exception as e:
                logger.error(f"❌ Ошибка восстановления: {e}")
                db.delete_active_game(game_data['game_id'])

        await self.update_lobby()

        logger.info(f"✅ Восстановлено игр: {restored_count}")
        print(f"🎮 [Games] Восстановлено игр: {restored_count}")

    async def create_game(self, game_type: str, player1: discord.Member, player2: discord.Member) -> bool:
        """Создать новую игру"""
        logger.info(f"🎮 Создание игры между {player1.display_name} и {player2.display_name}")

        if str(player1.id) in self.player_games or str(player2.id) in self.player_games:
            logger.warning(f"Один из игроков уже в игре")
            return False

        guild = player1.guild
        category_id = db.get_setting('games_category_id')
        category = guild.get_channel(int(category_id)) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            player1: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            player2: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"🎮-{player1.display_name[:8]}-{player2.display_name[:8]}"
        
        try:
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Игра: {game_type}"
            )
            logger.info(f"✅ Канал создан: #{channel.name}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания канала: {e}")
            return False

        game_id = uuid.uuid4().hex
        game = BattleshipGame(game_id, player1, player2, channel)

        self.active_games[game_id] = game
        self.player_games[str(player1.id)] = game_id
        self.player_games[str(player2.id)] = game_id

        db.save_active_game(
            game_id=game_id,
            game_type=game_type,
            channel_id=str(channel.id),
            player1_id=str(player1.id),
            player2_id=str(player2.id),
            game_data=json.dumps(game.get_state()),
            current_turn=str(game.current_turn.id)
        )

        embed = discord.Embed(
            title=f"🎮 МОРСКОЙ БОЙ",
            description=f"Игра между {player1.mention} и {player2.mention}\n\n"
                        f"**Управление через личные сообщения с ботом**\n"
                        f"Канал будет удалён через 1 минуту после завершения игры.",
            color=0x00ff00
        )
        await channel.send(embed=embed)

        for player in [player1, player2]:
            await self.send_game_interface(player, game, is_update=False)

        await self.log(f"🎮 Новая игра между {player1.display_name} и {player2.display_name}")
        return True

    async def send_game_interface(self, player: discord.Member, game, is_update: bool = False):
        """Отправить или обновить интерфейс игры в ЛС"""
        embed, files = await game.get_display(player)
        
        player_id = str(player.id)
        messages = game.player_messages.get(player_id, {})
        last_images = game.last_images.get(player_id, {})
        
        # Для сравнения файлов используем их размер и буфер
        # Сохраняем буферы файлов при первом создании
        try:
            # Обновляем или отправляем моё поле
            if is_update and messages.get("my_board") and last_images.get("my") is not None:
                # Если есть сохранённый буфер, не обновляем (картинка не изменилась без хода)
                # При ходе always_update=True будет вызвано с is_update=True, но картинка изменилась
                # Для простоты — всегда обновляем при is_update, так как ход точно был
                try:
                    my_msg = await player.fetch_message(messages["my_board"])
                    await my_msg.edit(attachments=[files[0]])
                except:
                    new_msg = await player.send(file=files[0])
                    messages["my_board"] = new_msg.id
            elif is_update and messages.get("my_board"):
                try:
                    my_msg = await player.fetch_message(messages["my_board"])
                    await my_msg.edit(attachments=[files[0]])
                except:
                    new_msg = await player.send(file=files[0])
                    messages["my_board"] = new_msg.id
            else:
                new_msg = await player.send(file=files[0])
                messages["my_board"] = new_msg.id
            
            # Обновляем или отправляем поле противника
            if is_update and messages.get("enemy_board"):
                try:
                    enemy_msg = await player.fetch_message(messages["enemy_board"])
                    await enemy_msg.edit(attachments=[files[1]])
                except:
                    new_msg = await player.send(file=files[1])
                    messages["enemy_board"] = new_msg.id
            else:
                new_msg = await player.send(file=files[1])
                messages["enemy_board"] = new_msg.id
            
            # Обновляем View (кнопки)
            if is_update and messages.get("view_msg"):
                try:
                    view_msg = await player.fetch_message(messages["view_msg"])
                    await view_msg.edit(embed=embed, view=game.get_view(player))
                except:
                    view_msg = await player.send(embed=embed, view=game.get_view(player))
                    messages["view_msg"] = view_msg.id
            else:
                view_msg = await player.send(embed=embed, view=game.get_view(player))
                messages["view_msg"] = view_msg.id
            
            game.player_messages[player_id] = messages
            
        except discord.Forbidden:
            await self.log(f"❌ Не могу отправить ЛС {player.display_name}")
            await self.end_game(game.game_id, None, None, force_end=True)
        except Exception as e:
            await self.log(f"❌ Ошибка отправки ЛС {player.display_name}: {e}")

    async def make_move(self, user: discord.Member, game_id: str, move_data: dict):
        """Обработать ход игрока"""
        game = self.active_games.get(game_id)
        if not game or game.game_over:
            await user.send("❌ Игра не найдена или уже завершена.")
            return

        if game.current_turn.id != user.id:
            await user.send("❌ Сейчас не ваш ход!")
            return

        success, message, update_for_opponent, hit = await game.make_move(user, move_data)

        if success:
            # Сохраняем состояние
            db.save_active_game(
                game_id=game.game_id,
                game_type="battleship",
                channel_id=str(game.channel.id),
                player1_id=str(game.player1.id),
                player2_id=str(game.player2.id),
                game_data=json.dumps(game.get_state()),
                current_turn=str(game.current_turn.id)
            )

            # Обновляем интерфейс текущему игроку
            await self.send_game_interface(user, game, is_update=True)
            
            # Если был хит (попадание) и игра не окончена, ход не переходит
            if hit and not game.game_over:
                await user.send(message)
                return
            
            # Обновляем интерфейс противнику
            opponent = game.get_opponent(user)
            await self.send_game_interface(opponent, game, is_update=True)
            
            # Отправляем сообщения о результате
            await user.send(message)
            if update_for_opponent:
                await opponent.send(update_for_opponent)
            
            await game.channel.send(f"🎯 {user.display_name} сделал ход. {message}")

            if game.game_over and game.winner:
                await self.end_game(game_id, game.winner, game.get_opponent(game.winner))
        else:
            await user.send(f"❌ {message}")

    async def end_game(self, game_id: str, winner: discord.Member, loser: discord.Member, force_end: bool = False):
        """Завершить игру"""
        game = self.active_games.get(game_id)
        if not game:
            return

        if winner and loser and not force_end:
            db.update_game_stats(str(winner.id), winner.display_name, True)
            db.update_game_stats(str(loser.id), loser.display_name, False)

            await winner.send(f"🏆 **Поздравляем! Вы победили!**")
            await loser.send(f"💔 **Вы проиграли. Попробуйте снова!**")
            await game.channel.send(f"🏆 **Победитель: {winner.mention}**")
            await self.log(f"🏆 Победитель: {winner.display_name}")

        await self.update_lobby()

        await asyncio.sleep(60)
        await game.channel.delete()

        del self.active_games[game_id]
        del self.player_games[str(game.player1.id)]
        del self.player_games[str(game.player2.id)]
        db.delete_active_game(game_id)

    async def update_lobby(self):
        """Обновить лобби (топ игроков)"""
        if not self.lobby_channel_id:
            return

        channel = self.bot.get_channel(int(self.lobby_channel_id))
        if not channel:
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.edit(embed=get_top_embed(), view=GameLobbyView())
                return

    async def log(self, message: str):
        """Отправить лог"""
        if self.log_channel_id:
            channel = self.bot.get_channel(int(self.log_channel_id))
            if channel:
                embed = discord.Embed(
                    title="🎮 Лог игр",
                    description=message,
                    color=0x7289da,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)

    def get_player_game(self, user_id: str) -> str:
        return self.player_games.get(user_id)


game_manager = None

async def setup(bot):
    global game_manager
    game_manager = GameManager(bot)
    await game_manager.initialize()
    return game_manager