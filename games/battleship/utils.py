"""Утилиты для морского боя"""
from PIL import Image, ImageDraw
import io


def generate_board_image(board, show_ships=True):
    """Сгенерировать картинку поля"""
    img = Image.new('RGB', (500, 550), color='white')
    draw = ImageDraw.Draw(img)

    for i in range(11):
        draw.line([(50, 50 + i * 40), (450, 50 + i * 40)], fill='black', width=2)
        draw.line([(50 + i * 40, 50), (50 + i * 40, 450)], fill='black', width=2)

    for i in range(10):
        draw.text((55 + i * 40, 25), chr(65 + i), fill='black')
        draw.text((25, 55 + i * 40), str(i + 1), fill='black')

    for i in range(10):
        for j in range(10):
            x, y = 50 + j * 40, 50 + i * 40

            if board[i][j] == 1 and show_ships:
                draw.rectangle([(x + 2, y + 2), (x + 38, y + 38)], fill='blue')
            elif board[i][j] == 2:
                draw.rectangle([(x + 2, y + 2), (x + 38, y + 38)], fill='red')
                draw.line([(x + 10, y + 10), (x + 30, y + 30)], fill='white', width=3)
                draw.line([(x + 30, y + 10), (x + 10, y + 30)], fill='white', width=3)
            elif board[i][j] == 3:
                draw.ellipse([(x + 15, y + 15), (x + 25, y + 25)], fill='black')

    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer