#!/bin/bash
# Исправить версию DVC на сервере

cd /root/rentsense

# Проверить текущую версию
echo "Текущая версия dvc в requirements.txt:"
grep "dvc==" requirements.txt

# Исправить
sed -i 's/dvc==3.32.2/dvc==3.66.0/' requirements.txt

# Проверить результат
echo "Обновленная версия dvc:"
grep "dvc==" requirements.txt

# Пересобрать без кеша
echo "Пересборка образа без кеша..."
docker-compose -f docker-compose.prod.yml build --no-cache backend

# Запустить
docker-compose -f docker-compose.prod.yml up -d

