"""
Скрипт для скачивания фотографий объявлений.
Используется для подготовки данных к LLM анализу.
"""
import logging
import os
import requests
import time
from pathlib import Path
from sqlalchemy import and_
from datetime import datetime
from .database import DB, Photos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_photo(url: str, save_path: Path, timeout: int = 30) -> bool:
    """Скачивает одну фотографию по URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Создаем директорию, если её нет
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файл
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading photo from {url}: {e}")
        return False


def download_photos_for_offer(cian_id: int, photos_base_dir: Path, limit: int = None) -> int:
    """
    Скачивает все фотографии для одного объявления.
    
    Args:
        cian_id: ID объявления на CIAN
        photos_base_dir: Базовая директория для сохранения фото (data/photos/)
        limit: Максимальное количество фото для скачивания (None = все)
    
    Returns:
        Количество успешно скачанных фото
    """
    session = DB.Session()
    try:
        # Получаем все фото для этого объявления, которые еще не скачаны
        query = session.query(Photos).filter(
            and_(
                Photos.cian_id == cian_id,
                Photos.is_downloaded == False
            )
        ).order_by(Photos.order_index)
        
        if limit:
            query = query.limit(limit)
        
        photos = query.all()
        
        if not photos:
            logger.info(f"No photos to download for offer {cian_id}")
            return 0
        
        downloaded_count = 0
        offer_dir = photos_base_dir / str(cian_id)
        
        for photo in photos:
            # Определяем расширение файла из URL или используем .jpg по умолчанию
            url_lower = photo.url.lower()
            if '.jpg' in url_lower or 'jpeg' in url_lower:
                ext = '.jpg'
            elif '.png' in url_lower:
                ext = '.png'
            elif '.webp' in url_lower:
                ext = '.webp'
            else:
                ext = '.jpg'  # По умолчанию
            
            filename = f"{photo.order_index or 0}{ext}"
            save_path = offer_dir / filename
            
            # Пропускаем, если файл уже существует
            if save_path.exists():
                logger.info(f"Photo already exists: {save_path}")
                # Обновляем запись в БД
                try:
                    relative_path = str(save_path.relative_to(photos_base_dir.parent))
                except ValueError:
                    relative_path = str(save_path)
                
                photo.local_path = relative_path
                photo.is_downloaded = True
                photo.downloaded_at = datetime.now()
                session.commit()
                downloaded_count += 1
                continue
            
            # Скачиваем фото
            if download_photo(photo.url, save_path):
                # Обновляем запись в БД (сохраняем путь относительно data/)
                # Если photos_base_dir = data/photos, то relative_path = photos/12345/0.jpg
                try:
                    relative_path = str(save_path.relative_to(photos_base_dir.parent))
                except ValueError:
                    # Если не удается вычислить относительный путь, сохраняем полный
                    relative_path = str(save_path)
                
                photo.local_path = relative_path
                photo.is_downloaded = True
                photo.downloaded_at = datetime.now()
                session.commit()
                downloaded_count += 1
                logger.info(f"Downloaded photo {downloaded_count}/{len(photos)} for offer {cian_id}")
                # Небольшая задержка, чтобы не нагружать сервер
                time.sleep(0.5)
            else:
                logger.warning(f"Failed to download photo {photo.id} from {photo.url[:50]}...")
        
        return downloaded_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error downloading photos for offer {cian_id}: {e}", exc_info=True)
        return 0
    finally:
        session.close()


def download_all_photos(photos_base_dir: Path = None, limit_per_offer: int = None, max_offers: int = None) -> dict:
    """
    Скачивает фотографии для всех объявлений, у которых есть фото, но они не скачаны.
    
    Args:
        photos_base_dir: Базовая директория (по умолчанию: data/photos/)
        limit_per_offer: Максимальное количество фото на объявление (None = все)
        max_offers: Максимальное количество объявлений для обработки (None = все)
    
    Returns:
        Статистика: {'total_offers': int, 'total_photos': int, 'downloaded_photos': int}
    """
    if photos_base_dir is None:
        # Определяем базовую директорию относительно корня проекта
        base_path = Path(__file__).parent.parent.parent
        photos_base_dir = base_path / 'data' / 'photos'
    
    photos_base_dir.mkdir(parents=True, exist_ok=True)
    
    session = DB.Session()
    try:
        # Получаем список объявлений с непройденными фото
        from .database import Offers
        query = session.query(Offers.cian_id).join(Photos).filter(
            Photos.is_downloaded == False
        ).distinct()
        
        if max_offers:
            query = query.limit(max_offers)
        
        offers = [row[0] for row in query.all()]
        
        logger.info(f"Found {len(offers)} offers with undownloaded photos")
        
        total_downloaded = 0
        processed = 0
        
        for cian_id in offers:
            downloaded = download_photos_for_offer(cian_id, photos_base_dir, limit_per_offer)
            total_downloaded += downloaded
            processed += 1
            
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(offers)} offers, downloaded {total_downloaded} photos")
        
        # Получаем общую статистику
        total_photos = session.query(Photos).count()
        downloaded_photos = session.query(Photos).filter(Photos.is_downloaded == True).count()
        
        stats = {
            'total_offers': len(offers),
            'total_photos': total_photos,
            'downloaded_photos': downloaded_photos,
            'newly_downloaded': total_downloaded
        }
        
        logger.info(f"Download complete. Stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in download_all_photos: {e}", exc_info=True)
        return {'error': str(e)}
    finally:
        session.close()


if __name__ == '__main__':
    # Пример использования
    import sys
    
    if len(sys.argv) > 1:
        # Скачать фото для конкретного объявления
        cian_id = int(sys.argv[1])
        base_path = Path(__file__).parent.parent.parent
        photos_dir = base_path / 'data' / 'photos'
        count = download_photos_for_offer(cian_id, photos_dir)
        print(f"Downloaded {count} photos for offer {cian_id}")
    else:
        # Скачать фото для всех объявлений
        stats = download_all_photos()
        print(f"Download stats: {stats}")

