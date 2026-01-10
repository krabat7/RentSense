#!/bin/bash
echo "Настройка локального окружения..."

echo "1. Запуск PostgreSQL в Docker..."
docker-compose up -d postgres

echo "2. Ожидание запуска БД..."
sleep 5

echo "3. Инициализация БД..."
python app/parser/init_db.py

echo "Готово! БД запущена локально на localhost:5432"


