# 🚀 Быстрый старт - ваш сервер готов!

## ✅ Ваши данные

**Сервер VDSina:**
- IP: `89.110.92.128`
- Hostname: `v3017595.hosted-by-vdsina.ru`

**Yandex Object Storage:**
- Bucket: `rentsense-bucket`
- Access Key: `YCAJEhxLcNZ_zudb0rzs9Vo7o`
- Secret Key: `YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq`

## 📋 Пошаговая инструкция

### 1️⃣ Подключение к серверу

```bash
ssh root@89.110.92.128
# Пароль от VDSina (пришел на email)
```

### 2️⃣ Загрузка проекта (выберите один вариант)

**Вариант А: Через PowerShell скрипт (Windows)**

На вашем компьютере:
```powershell
cd F:\hw_hse\Diploma\RentSense
.\upload_to_server.ps1
```

**Вариант Б: Вручную (проще, если есть проблемы)**

На вашем компьютере:
```powershell
cd F:\hw_hse\Diploma\RentSense

# Скопировать проект
scp -r app ml tests docker-compose.prod.yml Dockerfile requirements.txt *.sh create_database.py .env.server root@89.110.92.128:/root/rentsense/

# Переименовать .env.server в .env на сервере
ssh root@89.110.92.128 "cd /root/rentsense && mv .env.server .env"
```

### 3️⃣ Настройка на сервере

```bash
# Подключиться к серверу
ssh root@89.110.92.128

# Перейти в директорию
cd /root/rentsense

# Установить Docker (если еще не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
apt install docker-compose -y

# Установить зависимости
apt update && apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget git

# ⚠️ ВАЖНО: Заменить пароли в .env!
nano .env
# Найдите "CHANGE_THIS_TO_STRONG_PASSWORD" (2 раза)
# Замените на надежный пароль (запомните его!)
# Сохраните: Ctrl+X, Y, Enter

# Создать директории
mkdir -p logs backups data/raw data/processed

# Запустить
docker-compose -f docker-compose.prod.yml up -d --build

# Подождать 60 секунд пока MySQL запустится
sleep 60

# Инициализировать БД
docker-compose -f docker-compose.prod.yml exec backend python create_database.py
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db

# Настроить бэкапы
chmod +x backup_to_cloud.sh
mv backup_to_cloud.sh backup_db.sh
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -

# Тестовый бэкап
./backup_db.sh
```

### 4️⃣ Проверка

```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Тест парсера
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import apartPage
result = apartPage(['311739319'], dbinsert=True)
print('Result:', result)
"

# Проверка данных (замените YOUR_PASSWORD на ваш пароль из .env)
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_PASSWORD rentsense -e "SELECT COUNT(*) FROM offers;"

# Проверка бэкапов в облаке
docker run --rm \
    -e AWS_ACCESS_KEY_ID=YCAJEhxLcNZ_zudb0rzs9Vo7o \
    -e AWS_SECRET_ACCESS_KEY=YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq \
    amazon/aws-cli s3 ls s3://rentsense-bucket/rentsense/ \
    --endpoint-url=https://storage.yandexcloud.net
```

## 🎯 Готово!

После выполнения всех шагов:
- ✅ Сервер настроен
- ✅ БД работает
- ✅ Парсер готов
- ✅ Бэкапы настроены (ежедневно в 3:00 в облако)

## 📊 Что дальше?

1. **Запустить парсинг:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python -c "
   from app.parser.main import listPages, apartPage
   for page in range(1, 10):
       ids = listPages(page)
       if ids == 'END':
           break
       apartPage(ids, dbinsert=True)
       print(f'Page {page}: {len(ids)} offers')
   "
   ```

2. **Мониторить ресурсы:**
   ```bash
   free -h  # Память
   df -h    # Диск
   docker stats  # Использование Docker
   ```

3. **Следить за логами:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f parser
   ```

## ⚠️ Важно помнить

- **Пароль из .env** - сохраните в надежном месте!
- **Бэкапы** - проверяйте, что они загружаются в облако
- **Ресурсы** - мониторьте использование (1 GB RAM может быть мало)

## 🆘 Если что-то не работает

```bash
# Логи всех сервисов
docker-compose -f docker-compose.prod.yml logs

# Перезапуск
docker-compose -f docker-compose.prod.yml restart

# Полная перезагрузка
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

