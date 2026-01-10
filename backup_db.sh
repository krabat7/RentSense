#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="rentsense_backup_${DATE}.sql"

mkdir -p ${BACKUP_DIR}

docker-compose -f docker-compose.prod.yml exec -T mysql \
    mysqldump -uroot -prootpassword rentsense > ${BACKUP_DIR}/${FILENAME}

if [ $? -eq 0 ]; then
    gzip ${BACKUP_DIR}/${FILENAME}
    echo "Backup created: ${FILENAME}.gz"
    
    find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
    echo "Old backups cleaned"
else
    echo "Backup failed!"
    exit 1
fi

