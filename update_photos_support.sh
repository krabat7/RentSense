#!/bin/bash
# Скрипт для обновления файлов на сервере для поддержки фото
# Запускать на сервере в директории /root/rentsense

echo "Обновление поддержки фото в парсере..."

# Добавляем класс Photos в database.py (после класса Developers)
cat >> /tmp/add_photos_class.txt << 'PHOTOS_CLASS'
class Photos(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    url = Column(String(1000), nullable=False)  # URL оригинального фото
    local_path = Column(String(500), nullable=True)  # Путь к скачанному файлу (если скачано)
    order_index = Column(Integer, nullable=True)  # Порядковый номер фото (0, 1, 2...)
    is_downloaded = Column(Boolean, default=False)  # Скачано ли фото локально
    downloaded_at = Column(DateTime, nullable=True)  # Когда было скачано
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    
    offer = relationship("Offers", back_populates="photos")


PHOTOS_CLASS

# Находим строку "offer = relationship("Offers", back_populates="developer" и добавляем после нее
sed -i '/offer = relationship("Offers", back_populates="developer")/r /tmp/add_photos_class.txt' app/parser/database.py

# Обновляем relationship в Offers для photos
sed -i 's/developer = relationship("Developers", back_populates="offer", uselist=False, cascade="all, delete-orphan")/developer = relationship("Developers", back_populates="offer", uselist=False, cascade="all, delete-orphan")\n    photos = relationship("Photos", back_populates="offer", cascade="all, delete-orphan", order_by="Photos.order_index")/' app/parser/database.py

# Добавляем Photos в model_classes
sed -i 's/"developers": Developers,/"developers": Developers,\n    "photos": Photos,/' app/parser/database.py

echo "✓ database.py обновлен"

# Обновляем pagecheck.py - добавляем photos в data
sed -i '/developers = data.setdefault/a\    photos = data.setdefault('\''photos'\'', [])' app/parser/pagecheck.py

# Добавляем обработку фото после проверки oblId
cat > /tmp/add_photos_processing.txt << 'PHOTOS_PROCESSING'
    # Обработка фотографий
    if page.get('photos'):
        offers['photos_count'] = len(page['photos'])
        # Извлекаем URL фото - структура может быть разной, проверяем несколько вариантов
        for idx, photo in enumerate(page['photos']):
            photo_url = None
            # Варианты полей с URL в зависимости от структуры CIAN
            if isinstance(photo, str):
                photo_url = photo
            elif isinstance(photo, dict):
                photo_url = photo.get('fullUrl') or photo.get('url') or photo.get('full') or photo.get('src')
            
            if photo_url:
                photos.append({
                    'cian_id': cianid,
                    'url': photo_url,
                    'order_index': idx
                })
    else:
        offers['photos_count'] = None
PHOTOS_PROCESSING

# Заменяем старую строку с photos_count
sed -i 's/offers\['\''photos_count'\''\] = len(page\['\''photos'\''\]) if page.get('\''photos'\'') else None/REPLACE_PHOTOS_COUNT/' app/parser/pagecheck.py
sed -i '/REPLACE_PHOTOS_COUNT/r /tmp/add_photos_processing.txt' app/parser/pagecheck.py
sed -i '/REPLACE_PHOTOS_COUNT/d' app/parser/pagecheck.py

echo "✓ pagecheck.py обновлен"

# Обновляем main.py - добавляем обработку photos_data
# Это более сложное изменение, лучше использовать Python скрипт
python3 << 'PYUPDATE'
import re

with open('app/parser/main.py', 'r') as f:
    content = f.read()

# Ищем блок с pagecheck и добавляем обработку photos
if 'if data := pagecheck(pageJS):' in content:
    # Добавляем обработку photos_data перед if exist
    old_pattern = r'(if data := pagecheck\(pageJS\):.*?if not dbinsert:.*?return data.*?)if exist:'
    new_code = r'\1\n            # Обрабатываем фото отдельно (это массив объектов)\n            photos_data = data.pop(\'photos\', [])\n            \n            if exist:'
    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    
    # Добавляем обработку фото для exist=True
    old_update_block = r'(for model, update_values in instances:.*?DB\.update\(model, \{\'cian_id\': page\}, update_values\))'
    new_update_block = r'\1\n                \n                # Для фото: удаляем старые и вставляем новые\n                if photos_data:\n                    from .database import Photos\n                    # Удаляем старые фото для этого объявления\n                    session = DB.Session()\n                    try:\n                        session.query(Photos).filter(Photos.cian_id == page).delete()\n                        session.commit()\n                    except Exception as e:\n                        session.rollback()\n                        logging.error(f"Error deleting old photos for {page}: {e}")\n                    finally:\n                        session.close()\n                    \n                    # Вставляем новые фото\n                    photo_instances = [Photos(**photo) for photo in photos_data]\n                    if photo_instances:\n                        DB.insert(*photo_instances)\n                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")'
    content = re.sub(old_update_block, new_update_block, content, flags=re.DOTALL)
    
    # Добавляем обработку фото для exist=False
    old_insert_block = r'(logging\.info\(f"Apart page {page} is adding"\).*?DB\.insert\(\*instances\))'
    new_insert_block = r'\1\n                \n                # Добавляем фото для нового объявления\n                if photos_data:\n                    from .database import Photos\n                    photo_instances = [Photos(**photo) for photo in photos_data]\n                    if photo_instances:\n                        DB.insert(*photo_instances)\n                        logging.info(f"Apart page {page}: added {len(photo_instances)} photos")'
    content = re.sub(old_insert_block, new_insert_block, content, flags=re.DOTALL)

    with open('app/parser/main.py', 'w') as f:
        f.write(content)
    print("✓ main.py обновлен")
else:
    print("⚠ Не удалось найти блок pagecheck в main.py, обновите вручную")

PYUPDATE

rm -f /tmp/add_photos_class.txt /tmp/add_photos_processing.txt

echo ""
echo "✓ Обновление завершено!"
echo "Перезапустите парсер:"
echo "  docker-compose -f docker-compose.prod.yml restart parser"

