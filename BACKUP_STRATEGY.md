# Стратегия бэкапов - защита от потери данных

## ⚠️ Проблема: Что если сервер снесут?

**Риски:**
- Сервер могут удалить (неоплата, технические проблемы)
- Хардвер может сломаться
- Данные могут быть потеряны безвозвратно

**Решение: Автоматические бэкапы в облако**

## Варианты облачных хранилищ

### 1. ✅ Yandex Object Storage (рекомендуется для России)

**Цена:** ~20-50₽/мес за 10-50 GB  
**Скорость:** Высокая из России  
**Простота:** Очень простая настройка

**Настройка:**
1. Зарегистрироваться: https://cloud.yandex.ru/services/storage
2. Создать bucket (хранилище)
3. Создать сервисный аккаунт и ключи доступа
4. Добавить в `.env`:
   ```env
   BACKUP_TYPE=yandex
   YANDEX_ACCESS_KEY=your-access-key
   YANDEX_SECRET_KEY=your-secret-key
   YANDEX_BUCKET=your-bucket-name
   ```

### 2. AWS S3 / MinIO

**Цена:** ~$0.023/GB/мес (для S3)  
**Скорость:** Высокая  
**Подходит для:** Международных проектов

### 3. Google Drive API

**Цена:** Бесплатно до 15 GB  
**Простота:** Средняя (нужен OAuth)

### 4. Rsync на другой сервер

**Цена:** Зависит от второго сервера  
**Надежность:** Очень высокая

## Настройка автоматических бэкапов в облако

### Шаг 1: Установка AWS CLI (для Yandex/S3)

```bash
# На сервере
apt install docker.io -y
# AWS CLI уже будет в Docker образе
```

### Шаг 2: Создание bucket в Yandex Object Storage

1. Зайти в https://console.cloud.yandex.ru
2. Создать bucket (например: `rentsense-backups`)
3. В настройках bucket → "Сервисный аккаунт" → Создать
4. Создать ключи доступа (Static keys)
5. Скопировать Access Key ID и Secret Access Key

### Шаг 3: Настройка .env на сервере

```bash
nano .env
```

Добавить:
```env
BACKUP_TYPE=yandex
YANDEX_ACCESS_KEY=your-access-key-id
YANDEX_SECRET_KEY=your-secret-access-key
YANDEX_BUCKET=rentsense-backups
```

### Шаг 4: Обновить backup_db.sh

Заменить текущий скрипт на `backup_to_cloud.sh`:
```bash
mv backup_to_cloud.sh backup_db.sh
chmod +x backup_db.sh
```

### Шаг 5: Настроить cron

```bash
# Ежедневно в 3:00 - бэкап в облако
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -

# Также можно добавить еженедельный бэкап в воскресенье в 4:00
(crontab -l 2>/dev/null; echo "0 4 * * 0 cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -
```

## Восстановление из облака

Если сервер снесли:

```bash
# На новом сервере после настройки

# 1. Установить зависимости
apt install docker.io docker-compose -y

# 2. Настроить .env с теми же ключами доступа

# 3. Скачать последний бэкап из облака
docker run --rm \
    -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
    -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
    -v $(pwd)/backups:/backup \
    amazon/aws-cli s3 ls s3://${YANDEX_BUCKET}/rentsense/ \
    --endpoint-url=https://storage.yandexcloud.net \
    | tail -1

# 4. Скачать конкретный файл
LATEST_BACKUP=$(docker run --rm \
    -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
    -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
    amazon/aws-cli s3 ls s3://${YANDEX_BUCKET}/rentsense/ \
    --endpoint-url=https://storage.yandexcloud.net \
    | tail -1 | awk '{print $4}')

docker run --rm \
    -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
    -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
    -v $(pwd)/backups:/backup \
    amazon/aws-cli s3 cp \
    s3://${YANDEX_BUCKET}/rentsense/${LATEST_BACKUP} \
    /backup/${LATEST_BACKUP} \
    --endpoint-url=https://storage.yandexcloud.net

# 5. Восстановить БД
gunzip backups/${LATEST_BACKUP}
docker-compose exec mysql mysql -uroot -p rentsense < backups/${LATEST_BACKUP%.gz}
```

## Стоимость бэкапов

### Yandex Object Storage:
- **Хранение:** ~0.3₽/GB/мес
- **Запросы:** Бесплатно до 10000/мес
- **Итого:** ~10-30₽/мес (для 10-30 GB бэкапов)

### Локальное хранение (на сервере):
- Включено в тариф
- **Риск:** Потеря при удалении сервера

## Рекомендация

**Используйте оба варианта:**

1. **Локальные бэкапы** (на сервере) - быстрый доступ
2. **Облачные бэкапы** (Yandex Object Storage) - защита от потери сервера

**Расписание:**
- Ежедневно в 3:00 - бэкап в облако
- Локально храним последние 7 дней
- В облаке храним последние 30 дней (настроить в Yandex Object Storage)

## Мониторинг бэкапов

```bash
# Проверка последнего бэкапа
ls -lh backups/ | tail -1

# Проверка логов
tail -20 logs/backup.log

# Проверка облачных бэкапов
docker run --rm \
    -e AWS_ACCESS_KEY_ID=$YANDEX_ACCESS_KEY \
    -e AWS_SECRET_ACCESS_KEY=$YANDEX_SECRET_KEY \
    amazon/aws-cli s3 ls s3://${YANDEX_BUCKET}/rentsense/ \
    --endpoint-url=https://storage.yandexcloud.net
```

