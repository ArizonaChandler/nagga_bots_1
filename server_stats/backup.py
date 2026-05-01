"""Бекап базы данных"""
import os
import shutil
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


def create_backup(db_path='bot_data.db') -> str:
    """Создать бекап базы данных"""
    try:
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now(MSK_TZ).strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Бекап создан: {backup_name}")
            return backup_path
        else:
            logger.error(f"❌ База данных {db_path} не найдена")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания бекапа: {e}")
        return None


def restore_backup(backup_path: str, db_path='bot_data.db') -> bool:
    """Восстановить базу данных из бекапа"""
    try:
        if not os.path.exists(backup_path):
            logger.error(f"❌ Файл бекапа {backup_path} не найден")
            return False
        
        # Создаём резервную копию текущей БД перед восстановлением
        temp_backup = f"{db_path}.temp_backup"
        if os.path.exists(db_path):
            shutil.copy2(db_path, temp_backup)
        
        # Восстанавливаем
        shutil.copy2(backup_path, db_path)
        logger.info(f"✅ База данных восстановлена из {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления из бекапа: {e}")
        return False