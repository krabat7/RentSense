cd /root/rentsense && \
echo "=== ШАГ 1: Проверка переменных окружения ===" && \
source .env && \
echo "YANDEX_ACCESS_KEY: ${YANDEX_ACCESS_KEY:0:20}..." && \
echo "YANDEX_BUCKET: $YANDEX_BUCKET" && \
echo "" && \
echo "=== ШАГ 2: Тестирование доступа к bucket (попытка создать тестовый файл) ===" && \
echo "test-backup-check" | docker run --rm -i \
    -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
    -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
    amazon/aws-cli s3 cp - s3://$YANDEX_BUCKET/test-backup-check.txt \
    --endpoint-url=https://storage.yandexcloud.net 2>&1 && \
echo "✓ Доступ к bucket есть" || echo "⚠️ Проблема с доступом к bucket" && \
echo "" && \
echo "=== ШАГ 3: Создание исправленного скрипта бэкапа ===" && \
cat > /root/rentsense/backup_to_cloud.sh << 'SCRIPT_EOF'
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

# Загрузка в Yandex Object Storage
if [ "$BACKUP_TYPE" = "yandex" ] && [ -n "$YANDEX_ACCESS_KEY" ] && [ -n "$YANDEX_SECRET_KEY" ] && [ -n "$YANDEX_BUCKET" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | Uploading to Yandex Object Storage..."
    
    # Используем pipe для загрузки напрямую (без промежуточного файла в Docker)
    docker run --rm \
        -v ${BACKUP_DIR}:/backup:ro \
        -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
        -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
        amazon/aws-cli s3 cp \
        /backup/${FILENAME} \
        s3://${YANDEX_BUCKET}/${FILENAME} \
        --endpoint-url=https://storage.yandexcloud.net 2>&1
    
    if [ $? -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Uploaded to Yandex Object Storage: s3://${YANDEX_BUCKET}/${FILENAME}"
        UPLOAD_SUCCESS=true
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ⚠️ Upload failed - проверьте права доступа к bucket"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | Локальный бэкап сохранен: ${BACKUP_DIR}/${FILENAME}"
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
fi
SCRIPT_EOF
chmod +x /root/rentsense/backup_to_cloud.sh && \
echo "✓ backup_to_cloud.sh создан" && \
echo "" && \
echo "=== ШАГ 4: Тестовый бэкап ===" && \
/root/rentsense/backup_to_cloud.sh && \
echo "" && \
echo "=== ШАГ 5: Настройка cron (ежедневно в 03:00) ===" && \
mkdir -p /root/rentsense/logs && \
(crontab -l 2>/dev/null | grep -v "backup_to_cloud.sh"; echo "0 3 * * * /root/rentsense/backup_to_cloud.sh >> /root/rentsense/logs/backup.log 2>&1") | crontab - && \
echo "✓ Cron настроен" && \
echo "" && \
echo "=== ШАГ 6: Проверка настроек ===" && \
echo "Cron задачи:" && \
crontab -l | grep backup && \
echo "" && \
echo "=== Проверка созданного бэкапа ===" && \
ls -lh /root/rentsense/backups/*.gz 2>/dev/null | tail -1

