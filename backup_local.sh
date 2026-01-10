#!/bin/bash
# Локальный бэкап БД (с возможностью загрузки в облако при настройке прав)

BACKUP_DIR="/root/rentsense/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="rentsense_backup_${DATE}.sql.gz"

mkdir -p ${BACKUP_DIR}

# Загрузка переменных из .env
cd /root/rentsense
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DB_PASSWORD=${MYSQL_ROOT_PASSWORD:-RentSense2025!Secure}

# Создание локального бэкапа
echo "$(date '+%Y-%m-%d %H:%M:%S') | Creating local backup..."
docker-compose -f docker-compose.prod.yml exec -T mysql \
    mysqldump -uroot -p"${DB_PASSWORD}" rentsense 2>/dev/null | gzip > ${BACKUP_DIR}/${FILENAME}

if [ $? -ne 0 ] || [ ! -f ${BACKUP_DIR}/${FILENAME} ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR: Backup failed!"
    exit 1
fi

BACKUP_SIZE=$(du -h ${BACKUP_DIR}/${FILENAME} | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Backup created: ${FILENAME} (Size: ${BACKUP_SIZE})"

# Попытка загрузки в Yandex Object Storage (если настроено и права есть)
if [ "$BACKUP_TYPE" = "yandex" ] && [ -n "$YANDEX_ACCESS_KEY" ] && [ -n "$YANDEX_SECRET_KEY" ] && [ -n "$YANDEX_BUCKET" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | Attempting upload to Yandex Object Storage..."
    
    docker run --rm \
        -v /root/rentsense/backups:/backup:ro \
        -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
        -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
        amazon/aws-cli s3 cp \
        /backup/${FILENAME} \
        s3://${YANDEX_BUCKET}/${FILENAME} \
        --endpoint-url=https://storage.yandexcloud.net >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Uploaded to Yandex Object Storage"
        UPLOAD_SUCCESS=true
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ⚠️ Upload failed (check bucket permissions) - локальный бэкап сохранен"
        UPLOAD_SUCCESS=false
    fi
else
    UPLOAD_SUCCESS=false
fi

# Очистка старых локальных бэкапов (храним последние 30 дней для безопасности)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete
BACKUP_COUNT=$(ls -1 ${BACKUP_DIR}/*.sql.gz 2>/dev/null | wc -l)
echo "$(date '+%Y-%m-%d %H:%M:%S') | Old backups cleaned. Total backups: ${BACKUP_COUNT}"

# Итого
echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Backup completed:"
echo "  Local: ${BACKUP_DIR}/${FILENAME} (${BACKUP_SIZE})"
echo "  Total backups stored: ${BACKUP_COUNT}"
if [ "$UPLOAD_SUCCESS" = "true" ]; then
    echo "  Cloud: ✓ Uploaded to Yandex Object Storage"
fi
