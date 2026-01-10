Write-Host "Настройка локального окружения..."

Write-Host "1. Запуск PostgreSQL в Docker..."
docker-compose up -d postgres

Write-Host "2. Ожидание запуска БД..."
Start-Sleep -Seconds 5

Write-Host "3. Инициализация БД..."
python app/parser/init_db.py

Write-Host "Готово! БД запущена локально на localhost:5432"


