#!/bin/bash
# Бэкап БД в облако (Yandex Object Storage / S3 / Google Drive)

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="rentsense_backup_${DATE}.sql"
LOCAL_FILE="${BACKUP_DIR}/${FILENAME}"

mkdir -p ${BACKUP_DIR}

# Загрузка переменных из .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

# Создание локального бэкапа
echo "Creating local backup..."
docker-compose -f docker-compose.prod.yml exec -T mysql \
    mysqldump -uroot -p"${DB_PASSWORD}" rentsense > ${LOCAL_FILE}

if [ $? -ne 0 ]; then
    echo "ERROR: Backup failed!"
    exit 1
fi

# Сжатие
gzip ${LOCAL_FILE}
LOCAL_FILE_GZ="${LOCAL_FILE}.gz"

echo "Backup created: ${FILENAME}.gz"

# Загрузка в облако
BACKUP_TYPE=${BACKUP_TYPE:-"yandex"}

case $BACKUP_TYPE in
    "yandex")
        # Yandex Object Storage (самое дешевое в России)
        if [ -z "$YANDEX_ACCESS_KEY" ] || [ -z "$YANDEX_SECRET_KEY" ] || [ -z "$YANDEX_BUCKET" ]; then
            echo "WARNING: Yandex Object Storage not configured (YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY, YANDEX_BUCKET)"
        else
            echo "Uploading to Yandex Object Storage..."
            docker run --rm -v $(pwd):/backup \
                -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
                -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
                amazon/aws-cli s3 cp \
                /backup/${LOCAL_FILE_GZ} \
                s3://${YANDEX_BUCKET}/rentsense/${FILENAME}.gz \
                --endpoint-url=https://storage.yandexcloud.net
            echo "Uploaded to Yandex Object Storage"
        fi
        ;;
    
    "s3")
        # AWS S3 или совместимое
        if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_BUCKET" ]; then
            echo "WARNING: S3 not configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET)"
        else
            echo "Uploading to S3..."
            docker run --rm -v $(pwd):/backup \
                -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
                -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
                amazon/aws-cli s3 cp \
                /backup/${LOCAL_FILE_GZ} \
                s3://${AWS_BUCKET}/rentsense/${FILENAME}.gz
            echo "Uploaded to S3"
        fi
        ;;
    
    "rsync")
        # Rsync на другой сервер
        if [ -z "$RSYNC_HOST" ] || [ -z "$RSYNC_USER" ] || [ -z "$RSYNC_PATH" ]; then
            echo "WARNING: Rsync not configured (RSYNC_HOST, RSYNC_USER, RSYNC_PATH)"
        else
            echo "Uploading via rsync..."
            rsync -avz ${LOCAL_FILE_GZ} ${RSYNC_USER}@${RSYNC_HOST}:${RSYNC_PATH}/
            echo "Uploaded via rsync"
        fi
        ;;
    
    "none")
        echo "Cloud backup disabled (BACKUP_TYPE=none)"
        ;;
esac

# Очистка старых локальных бэкапов (храним последние 7 дней)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
echo "Old local backups cleaned"

# Итого
echo ""
echo "✓ Backup completed:"
echo "  Local: ${LOCAL_FILE_GZ}"
if [ "$BACKUP_TYPE" != "none" ]; then
    echo "  Cloud: Uploaded (if configured)"
fi

