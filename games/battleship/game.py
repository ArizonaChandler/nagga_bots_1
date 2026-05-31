"""Логика игры Морской бой"""
import discord
import json
import random
from games.base import BaseGame
from games.battleship.utils import generate_board_image
from games.battleship.views import BattleshipView


class BattleshipGame(BaseGame):
    """Морской бой"""

    def __init__(self, game_id: str, player1: discord.Member, player2: discord.Member, channel: discord.TextChannel):
        super().__init__(game_id, player1, player2, channel)

        self.board1 = [[0 for _ in range(10)] for _ in range(10)]
        self.board2 = [[0 for _ in range(10)] for _ in range(10)]
        self.ships1 = self._place_ships()
        self.ships2 = self._place_ships()
        self.passes = {str(player1.id): 0, str(player2.id): 0}

        for ship in self.ships1:
            for x, y in ship:
                self.board1[x][y] = 1
        for ship in self.ships2:
            for x, y in ship:
                self.board2[x][y] = 1

        # Хранилище ID сообщений для обновления (чтобы не флудить)
        self.player_messages = {
            str(player1.id): {"my_board": None, "enemy_board": None},
            str(player2.id): {"my_board": None, "enemy_board": None}
        }

    def _place_ships(self):
        """Разместить корабли на поле"""
        ships = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        placed = []

        for ship_len in ships:
            placed_flag = False
            attempts = 0
            while not placed_flag and attempts < 1000:
                attempts += 1
                horizontal = random.choice([True, False])
                if horizontal:
                    x = random.randint(0, 9)
                    y = random.randint(0, 9 - ship_len)
                    coords = [(x, y + i) for i in range(ship_len)]
                else:
                    x = random.randint(0, 9 - ship_len)
                    y = random.randint(0, 9)
                    coords = [(x + i, y) for i in range(ship_len)]

                valid = True
                for cx, cy in coords:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < 10 and 0 <= ny < 10:
                                for ship in placed:
                                    if (nx, ny) in ship:
                                        valid = False
                                        break
                            if not valid:
                                break
                        if not valid:
                            break
                    if not valid:
                        break

                if valid:
                    placed.append(coords)
                    placed_flag = True

            if not placed_flag:
                return self._place_ships()

        return placed

    async def make_move(self, user: discord.Member, data: dict) -> tuple:
        """Сделать ход. Возвращает (success, message, update_for_opponent)"""
        row, col = data['row'], data['col']

        if self.game_over:
            return False, "Игра уже закончена!", ""

        if user == self.player1:
            target_board = self.board2
            target_ships = self.ships2
        else:
            target_board = self.board1
            target_ships = self.ships1

        if target_board[row][col] in [2, 3]:
            return False, "Вы уже стреляли в эту клетку!", ""

        if target_board[row][col] == 0:
            target_board[row][col] = 3
            self.passes[str(user.id)] = 0
            self.current_turn = self.get_opponent(user)
            return True, "❌ Мимо!", f"❌ {user.display_name} промахнулся!"

        elif target_board[row][col] == 1:
            target_board[row][col] = 2

            ship_killed = False
            for ship in target_ships:
                if (row, col) in ship:
                    if all(target_board[cx][cy] == 2 for cx, cy in ship):
                        ship_killed = True
                    break

            all_sunk = True
            for ship in target_ships:
                if not all(target_board[cx][cy] == 2 for cx, cy in ship):
                    all_sunk = False
                    break

            if all_sunk:
                self.game_over = True
                self.winner = user
                return True, "💥 Попадание! Корабль уничтожен!\n🎉 **ПОБЕДА!**", f"💥 {user.display_name} уничтожил последний корабль и победил!"

            if ship_killed:
                return True, "💥 Попадание! Корабль уничтожен! Стреляйте ещё раз!", f"💥 {user.display_name} уничтожил ваш корабль!"
            else:
                return True, "💢 Попадание! Стреляйте ещё раз!", f"💢 {user.display_name} попал в ваш корабль!"

        return False, "Ошибка!", ""

    def get_state(self) -> dict:
        """Получить состояние игры для сохранения"""
        return {
            'board1': self.board1,
            'board2': self.board2,
            'ships1': self.ships1,
            'ships2': self.ships2,
            'passes': self.passes,
            'current_turn_id': str(self.current_turn.id),
            'player1_id': str(self.player1.id),
            'player2_id': str(self.player2.id),
            'game_over': self.game_over,
            'winner_id': str(self.winner.id) if self.winner else None,
            'player_messages': self.player_messages  # ← сохраняем ID сообщений
        }

    @classmethod
    def from_state(cls, game_data: dict, bot):
        """Восстановить игру из сохранённого состояния"""
        data = json.loads(game_data['game_data'])

        player1 = bot.get_user(int(data['player1_id']))
        player2 = bot.get_user(int(data['player2_id']))
        channel = bot.get_channel(int(game_data['channel_id']))

        if not player1 or not player2 or not channel:
            return None

        game = cls(game_data['game_id'], player1, player2, channel)
        game.board1 = data['board1']
        game.board2 = data['board2']
        game.ships1 = data['ships1']
        game.ships2 = data['ships2']
        game.passes = data['passes']
        game.game_over = data['game_over']
        
        # Восстанавливаем ID сообщений
        if 'player_messages' in data:
            game.player_messages = data['player_messages']

        for p in [player1, player2]:
            if str(p.id) == data['current_turn_id']:
                game.current_turn = p
                break

        if data.get('winner_id'):
            for p in [player1, player2]:
                if str(p.id) == data['winner_id']:
                    game.winner = p
                    break

        return game

    async def get_display(self, player: discord.Member) -> tuple:
        """Получить embed и файлы для отображения игроку"""
        is_player1 = player == self.player1

        my_board = self.board1 if is_player1 else self.board2
        enemy_board = self.board2 if is_player1 else self.board1

        img_my = generate_board_image(my_board, show_ships=True)
        img_enemy = generate_board_image(enemy_board, show_ships=False)

        embed = discord.Embed(
            title="🎮 **МОРСКОЙ БОЙ**",
            description=f"**Ваш ход:** {'✅ ДА' if self.current_turn.id == player.id else '❌ НЕТ'}",
            color=0x00ff00 if self.current_turn.id == player.id else 0xff0000
        )

        embed.add_field(name="📊 Пропусков", value=f"{self.passes.get(str(player.id), 0)}/3", inline=True)

        return embed, [discord.File(img_my, "my_board.png"), discord.File(img_enemy, "enemy_board.png")]

    def get_view(self, player: discord.Member):
        """Получить View для управления игрой"""
        return BattleshipView(self, player)