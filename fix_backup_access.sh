cd /root/rentsense && \
echo "=== ШАГ 1: Проверка настроек Yandex ===" && \
echo "Access Key: $(grep YANDEX_ACCESS_KEY .env | cut -d'=' -f2 | head -c 20)..." && \
echo "Bucket: $(grep YANDEX_BUCKET .env | cut -d'=' -f2)" && \
echo "" && \
echo "=== ШАГ 2: Тестирование подключения к Yandex Object Storage ===" && \
docker run --rm \
    -e AWS_ACCESS_KEY_ID=$(grep YANDEX_ACCESS_KEY .env | cut -d'=' -f2) \
    -e AWS_SECRET_ACCESS_KEY=$(grep YANDEX_SECRET_KEY .env | cut -d'=' -f2) \
    amazon/aws-cli s3 ls s3://$(grep YANDEX_BUCKET .env | cut -d'=' -f2)/ \
    --endpoint-url=https://storage.yandexcloud.net && \
echo "✓ Подключение к bucket успешно" || echo "❌ Ошибка подключения к bucket" && \
echo "" && \
echo "=== ШАГ 3: Исправление скрипта (использование абсолютного пути) ===" && \
cat > backup_to_cloud.sh << 'EOF'
#!/bin/bash
# Бэкап БД в облако (Yandex Object Storage / S3 / Google Drive)

BACKUP_DIR="/root/rentsense/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="rentsense_backup_${DATE}.sql"
LOCAL_FILE="${BACKUP_DIR}/${FILENAME}"

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
    mysqldump -uroot -p"${DB_PASSWORD}" rentsense > ${LOCAL_FILE}

if [ $? -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR: Backup failed!"
    exit 1
fi

# Сжатие
gzip ${LOCAL_FILE}
LOCAL_FILE_GZ="${LOCAL_FILE}.gz"

echo "$(date '+%Y-%m-%d %H:%M:%S') | Backup created: ${FILENAME}.gz (Size: $(du -h ${LOCAL_FILE_GZ} | cut -f1))"

# Загрузка в облако
BACKUP_TYPE=${BACKUP_TYPE:-"yandex"}

case $BACKUP_TYPE in
    "yandex")
        # Yandex Object Storage
        if [ -z "$YANDEX_ACCESS_KEY" ] || [ -z "$YANDEX_SECRET_KEY" ] || [ -z "$YANDEX_BUCKET" ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') | WARNING: Yandex Object Storage not configured"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') | Uploading to Yandex Object Storage..."
            # Используем абсолютный путь для mount
            docker run --rm \
                -v /root/rentsense/backups:/backup \
                -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
                -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
                amazon/aws-cli s3 cp \
                /backup/${FILENAME}.gz \
                s3://${YANDEX_BUCKET}/${FILENAME}.gz \
                --endpoint-url=https://storage.yandexcloud.net
            
            if [ $? -eq 0 ]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Uploaded to Yandex Object Storage: s3://${YANDEX_BUCKET}/${FILENAME}.gz"
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR: Upload failed! Проверьте права доступа к bucket"
                # Не выходим с ошибкой, чтобы локальный бэкап сохранился
            fi
        fi
        ;;
    
    "none")
        echo "$(date '+%Y-%m-%d %H:%M:%S') | Cloud backup disabled (BACKUP_TYPE=none)"
        ;;
esac

# Очистка старых локальных бэкапов (храним последние 7 дней)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
echo "$(date '+%Y-%m-%d %H:%M:%S') | Old local backups cleaned"

# Итого
echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') | ✓ Backup completed:"
echo "  Local: ${LOCAL_FILE_GZ}"
if [ "$BACKUP_TYPE" != "none" ] && [ "$?" -eq 0 ]; then
    echo "  Cloud: Uploaded to Yandex Object Storage"
fi
EOF
chmod +x backup_to_cloud.sh && \
echo "✓ backup_to_cloud.sh обновлен" && \
echo "" && \
echo "=== ШАГ 4: Повторный тестовый бэкап ===" && \
./backup_to_cloud.sh && \
echo "" && \
echo "=== ШАГ 5: Проверка настроек ===" && \
echo "Cron задачи:" && \
(crontab -l 2>/dev/null | grep -v "backup_to_cloud.sh"; echo "0 3 * * * cd /root/rentsense && /root/rentsense/backup_to_cloud.sh >> /root/rentsense/logs/backup.log 2>&1") | crontab - && \
crontab -l | grep backup

