#!/bin/bash
# Бэкап БД в облако (Yandex Object Storage)

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
echo "$(date '+%Y-%m-%d %H:%M:%S') | Backup created: ${FILENAME} (Size: ${BACKUP_SIZE})"

# Загрузка в Yandex Object Storage (если настроено)
if [ "$BACKUP_TYPE" = "yandex" ] && [ -n "$YANDEX_ACCESS_KEY" ] && [ -n "$YANDEX_SECRET_KEY" ] && [ -n "$YANDEX_BUCKET" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | Uploading to Yandex Object Storage..."
    
    # Используем абсолютный путь для mount
    docker run --rm \
        -v /root/rentsense/backups:/backup:ro \
        -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
        -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
        amazon/aws-cli s3 cp \
        /backup/${FILENAME} \
        s3://${YANDEX_BUCKET}/${FILENAME} \
        --endpoint-url=https://storage.yandexcloud.net 2>&1
    
    UPLOAD_EXIT_CODE=$?
    if [ $UPLOAD_EXIT_CODE -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Uploaded to Yandex Object Storage: s3://${YANDEX_BUCKET}/${FILENAME}"
        UPLOAD_SUCCESS=true
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ⚠️ Upload failed (exit code: $UPLOAD_EXIT_CODE)"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | Локальный бэкап сохранен: ${BACKUP_DIR}/${FILENAME}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | Проверьте права доступа к bucket в Yandex Cloud Console"
        UPLOAD_SUCCESS=false
    fi
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') | Cloud backup skipped (not configured)"
    UPLOAD_SUCCESS=false
fi

# Очистка старых локальных бэкапов (храним последние 7 дней)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
echo "$(date '+%Y-%m-%d %H:%M:%S') | Old local backups cleaned"

# Итого
echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Backup completed:"
echo "  Local: ${BACKUP_DIR}/${FILENAME} (${BACKUP_SIZE})"
if [ "$UPLOAD_SUCCESS" = "true" ]; then
    echo "  Cloud: ✓ Uploaded to Yandex Object Storage"
else
    echo "  Cloud: ✗ Upload failed (check bucket permissions)"
fi
