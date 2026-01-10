"""
Миграция: Добавление таблицы photos в БД.
Запускается один раз для создания новой таблицы.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.parser.database import DB, Photos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Создает таблицу photos, если её еще нет."""
    try:
        logger.info("Creating photos table...")
        DB.create_tables()
        logger.info("✓ Photos table created/verified successfully")
        
        # Проверяем, что таблица существует
        existing_tables = DB.get_existing_tables()
        if 'photos' in existing_tables:
            logger.info("✓ Photos table exists in database")
            
            # Проверяем структуру
            session = DB.Session()
            try:
                count = session.query(Photos).count()
                logger.info(f"✓ Photos table contains {count} records")
            except Exception as e:
                logger.error(f"Error checking photos table: {e}")
            finally:
                session.close()
        else:
            logger.warning("⚠ Photos table not found in existing tables list")
            
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        return False
    
    return True


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

