#!/bin/bash
# Восстановление БД из облачного бэкапа

if [ -z "$BACKUP_TYPE" ]; then
    echo "ERROR: BACKUP_TYPE not set in .env"
    exit 1
fi

BACKUP_DIR="./backups"
mkdir -p ${BACKUP_DIR}

echo "=== Восстановление из облака ==="
echo ""

case $BACKUP_TYPE in
    "yandex")
        if [ -z "$YANDEX_ACCESS_KEY" ] || [ -z "$YANDEX_SECRET_KEY" ] || [ -z "$YANDEX_BUCKET" ]; then
            echo "ERROR: Yandex credentials not configured"
            exit 1
        fi
        
        echo "Список доступных бэкапов:"
        docker run --rm \
            -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
            -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
            amazon/aws-cli s3 ls s3://${YANDEX_BUCKET}/rentsense/ \
            --endpoint-url=https://storage.yandexcloud.net
        
        read -p "Введите имя файла для восстановления: " BACKUP_FILE
        
        echo "Скачивание бэкапа..."
        docker run --rm \
            -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
            -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
            -v $(pwd)/backups:/backup \
            amazon/aws-cli s3 cp \
            s3://${YANDEX_BUCKET}/rentsense/${BACKUP_FILE} \
            /backup/${BACKUP_FILE} \
            --endpoint-url=https://storage.yandexcloud.net
        ;;
    
    "s3")
        echo "Список доступных бэкапов:"
        docker run --rm \
            -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
            -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
            amazon/aws-cli s3 ls s3://${AWS_BUCKET}/rentsense/
        
        read -p "Введите имя файла для восстановления: " BACKUP_FILE
        
        docker run --rm \
            -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
            -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
            -v $(pwd)/backups:/backup \
            amazon/aws-cli s3 cp \
            s3://${AWS_BUCKET}/rentsense/${BACKUP_FILE} \
            /backup/${BACKUP_FILE}
        ;;
    
    *)
        echo "ERROR: Unsupported backup type: $BACKUP_TYPE"
        exit 1
        ;;
esac

if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found"
    exit 1
fi

echo ""
echo "Распаковка..."
gunzip -f ${BACKUP_DIR}/${BACKUP_FILE}
SQL_FILE="${BACKUP_DIR}/${BACKUP_FILE%.gz}"

echo ""
echo "ВНИМАНИЕ: Это перезапишет текущую БД!"
read -p "Продолжить? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Отменено"
    exit 0
fi

# Загрузка переменных из .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

echo ""
echo "Восстановление БД..."
docker-compose -f docker-compose.prod.yml exec -T mysql \
    mysql -uroot -p${DB_PASSWORD} rentsense < ${SQL_FILE}

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ БД успешно восстановлена!"
    echo "Файл: ${SQL_FILE}"
else
    echo ""
    echo "✗ Ошибка восстановления"
    exit 1
fi

