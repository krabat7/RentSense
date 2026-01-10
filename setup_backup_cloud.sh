#!/bin/bash
# Скрипт для быстрой настройки облачных бэкапов

echo "=== Настройка облачных бэкапов ==="
echo ""

echo "Выберите тип облачного хранилища:"
echo "1. Yandex Object Storage (рекомендуется, ~20-50₽/мес)"
echo "2. AWS S3"
echo "3. Rsync на другой сервер"
echo "4. Отключить облачные бэкапы (только локально)"
read -p "Выбор (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Настройка Yandex Object Storage:"
        echo "1. Зайдите на https://console.cloud.yandex.ru"
        echo "2. Создайте bucket (хранилище)"
        echo "3. Создайте сервисный аккаунт и ключи доступа"
        echo ""
        read -p "Access Key ID: " ACCESS_KEY
        read -p "Secret Access Key: " SECRET_KEY
        read -p "Bucket name: " BUCKET
        
        # Добавить в .env
        cat >> .env << EOF

# Cloud Backup Settings
BACKUP_TYPE=yandex
YANDEX_ACCESS_KEY=${ACCESS_KEY}
YANDEX_SECRET_KEY=${SECRET_KEY}
YANDEX_BUCKET=${BUCKET}
EOF
        
        echo ""
        echo "✓ Настройки добавлены в .env"
        ;;
    
    2)
        read -p "AWS Access Key ID: " ACCESS_KEY
        read -p "AWS Secret Access Key: " SECRET_KEY
        read -p "AWS Bucket name: " BUCKET
        
        cat >> .env << EOF

# Cloud Backup Settings
BACKUP_TYPE=s3
AWS_ACCESS_KEY_ID=${ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${SECRET_KEY}
AWS_BUCKET=${BUCKET}
EOF
        
        echo "✓ Настройки добавлены в .env"
        ;;
    
    3)
        read -p "Rsync host (user@host): " RSYNC_HOST
        read -p "Rsync path (/backups/): " RSYNC_PATH
        
        cat >> .env << EOF

# Cloud Backup Settings
BACKUP_TYPE=rsync
RSYNC_HOST=${RSYNC_HOST}
RSYNC_USER=$(echo ${RSYNC_HOST} | cut -d'@' -f1)
RSYNC_PATH=${RSYNC_PATH}
EOF
        
        echo "✓ Настройки добавлены в .env"
        ;;
    
    4)
        cat >> .env << EOF

# Cloud Backup Settings
BACKUP_TYPE=none
EOF
        
        echo "✓ Облачные бэкапы отключены"
        ;;
esac

echo ""
echo "Обновление скрипта бэкапа..."
cp backup_to_cloud.sh backup_db.sh
chmod +x backup_db.sh

echo ""
echo "Добавление в cron (ежедневно в 3:00)..."
(crontab -l 2>/dev/null; echo "0 3 * * * cd $(pwd) && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -

echo ""
echo "=== Настройка завершена ==="
echo ""
echo "Проверка:"
echo "  - Настройки: cat .env | grep BACKUP"
echo "  - Тестовый бэкап: ./backup_db.sh"
echo "  - Логи: tail -f logs/backup.log"

