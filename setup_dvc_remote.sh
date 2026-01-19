#!/bin/bash
# Скрипт для настройки DVC remote storage
# Использование: ./setup_dvc_remote.sh [s3|minio]

set -e

REMOTE_TYPE=${1:-"local"}

echo "=== Настройка DVC remote storage ==="
echo "Тип хранилища: $REMOTE_TYPE"

cd "$(dirname "$0")"

case $REMOTE_TYPE in
    s3)
        echo "Настройка S3 remote..."
        read -p "S3 bucket name: " BUCKET_NAME
        read -p "S3 endpoint (или оставьте пустым для AWS): " ENDPOINT
        
        if [ -z "$ENDPOINT" ]; then
            dvc remote add -d s3remote "s3://${BUCKET_NAME}/dvc"
        else
            dvc remote add -d s3remote "s3://${BUCKET_NAME}/dvc" --endpoint-url "$ENDPOINT"
        fi
        
        echo "✅ S3 remote настроен"
        echo "Не забудьте настроить AWS credentials:"
        echo "  aws configure"
        echo "  или"
        echo "  export AWS_ACCESS_KEY_ID=your_key"
        echo "  export AWS_SECRET_ACCESS_KEY=your_secret"
        ;;
        
    minio)
        echo "Настройка MinIO remote..."
        read -p "MinIO endpoint (например, http://localhost:9000): " ENDPOINT
        read -p "MinIO bucket name: " BUCKET_NAME
        read -p "MinIO access key: " ACCESS_KEY
        read -p "MinIO secret key: " SECRET_KEY
        
        dvc remote add -d minio "s3://${BUCKET_NAME}/dvc" \
            --endpoint-url "$ENDPOINT"
        
        dvc remote modify minio access_key_id "$ACCESS_KEY"
        dvc remote modify minio secret_access_key "$SECRET_KEY"
        
        echo "✅ MinIO remote настроен"
        ;;
        
    local|*)
        echo "Использование локального хранилища (по умолчанию)"
        echo "DVC будет хранить данные в .dvc/cache/"
        echo ""
        echo "Для настройки remote storage позже используйте:"
        echo "  dvc remote add -d s3remote s3://bucket-name/dvc"
        echo "  или"
        echo "  dvc remote add -d minio s3://bucket-name/dvc --endpoint-url http://minio:9000"
        ;;
esac

echo ""
echo "Текущая конфигурация DVC:"
dvc remote list

