"""Files Core - Система хранения и выдачи полезных файлов"""
import os
import hashlib
import time
from pathlib import Path
from core.database import db

FILES_STORAGE = Path(__file__).parent / "storage"
FILES_STORAGE.mkdir(exist_ok=True)

class FileManager:
    def __init__(self):
        self.storage_path = FILES_STORAGE
        self.init_database()
        print("📁 Files Core инициализирован")
    
    def init_database(self):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS useful_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    filename TEXT NOT NULL,
                    filesize INTEGER,
                    file_hash TEXT UNIQUE,
                    uploaded_by TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    downloads INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
    
    async def save_file(self, interaction, name: str, description: str, attachment):
        try:
            file_ext = attachment.filename.split('.')[-1] if '.' in attachment.filename else 'bin'
            timestamp = int(time.time())
            unique_filename = f"{timestamp}_{hashlib.md5(name.encode()).hexdigest()[:8]}.{file_ext}"
            file_path = self.storage_path / unique_filename
            
            await attachment.save(file_path)
            file_size = os.path.getsize(file_path)
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO useful_files 
                    (name, description, filename, filesize, uploaded_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, description, unique_filename, file_size, str(interaction.user.id)))
                conn.commit()
                file_id = cursor.lastrowid
            
            db.log_action(str(interaction.user.id), "FILE_UPLOAD", 
                         f"ID: {file_id}, Название: {name}, Размер: {file_size} байт")
            
            return file_id, None
        except Exception as e:
            return None, str(e)
    
    def get_files(self, page: int = 1, per_page: int = 5):
        offset = (page - 1) * per_page
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM useful_files WHERE is_active = 1')
            total = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT id, name, description, filesize, uploaded_by, uploaded_at, downloads
                FROM useful_files 
                WHERE is_active = 1 
                ORDER BY uploaded_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            files = cursor.fetchall()
            return files, total
    
    async def send_file(self, interaction, file_id: int):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filename, name, description, filesize
                FROM useful_files WHERE id = ? AND is_active = 1
            ''', (file_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Файл не найден"
            
            filename, name, description, filesize = result
            file_path = self.storage_path / filename
            
            if not file_path.exists():
                return False, "Файл отсутствует на сервере"
            
            cursor.execute('UPDATE useful_files SET downloads = downloads + 1 WHERE id = ?', (file_id,))
            conn.commit()
        
        try:
            await interaction.user.send(
                content=f"📁 **{name}**\n{description}",
                file=discord.File(file_path)
            )
            db.log_action(str(interaction.user.id), "FILE_DOWNLOAD", f"ID: {file_id}, Название: {name}")
            return True, None
        except discord.Forbidden:
            await interaction.channel.send(
                content=f"📁 **{name}**\n{description}",
                file=discord.File(file_path)
            )
            return True, "ЛС закрыты, файл отправлен в чат"
        except Exception as e:
            return False, str(e)
    
    def delete_file(self, file_id: int, user_id: str) -> tuple[bool, str]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE useful_files SET is_active = 0 WHERE id = ?', (file_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                db.log_action(user_id, "FILE_DELETE", f"ID: {file_id}")
                return True, "Файл удалён"
            return False, "Файл не найден"

file_manager = FileManager()