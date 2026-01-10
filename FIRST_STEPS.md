# Первые шаги после аренды сервера

## ✅ Ваши данные

**Сервер:**
- IP: `89.110.92.128`
- Hostname: `v3017595.hosted-by-vdsina.ru`
- ОС: Ubuntu 24.04
- Ресурсы: 1 core / 1 GB RAM / 10 GB диск

**Yandex Object Storage:**
- Bucket: `rentsense-bucket`
- Access Key: `YCAJEhxLcNZ_zudb0rzs9Vo7o`
- Secret Key: `YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq`

## 🚀 Быстрый старт

### Шаг 1: Подключение к серверу

На вашем компьютере (PowerShell или Terminal):

```bash
ssh root@89.110.92.128
# Введите пароль, который пришел на email от VDSina
```

### Шаг 2: Загрузка проекта

**Вариант А: Через PowerShell скрипт (Windows)**

На вашем компьютере:
```powershell
cd F:\hw_hse\Diploma\RentSense
.\upload_to_server.ps1
```

**Вариант Б: Вручную через SCP**

На вашем компьютере:
```powershell
cd F:\hw_hse\Diploma\RentSense

# Создать директорию на сервере
ssh root@89.110.92.128 "mkdir -p /root/rentsense"

# Скопировать основные файлы
scp -r app root@89.110.92.128:/root/rentsense/
scp -r ml root@89.110.92.128:/root/rentsense/
scp -r tests root@89.110.92.128:/root/rentsense/
scp docker-compose.prod.yml root@89.110.92.128:/root/rentsense/
scp Dockerfile root@89.110.92.128:/root/rentsense/
scp requirements.txt root@89.110.92.128:/root/rentsense/
scp .env.server root@89.110.92.128:/root/rentsense/.env
scp create_database.py root@89.110.92.128:/root/rentsense/
scp *.sh root@89.110.92.128:/root/rentsense/
```

### Шаг 3: Настройка на сервере

**На сервере:**

```bash
# 1. Перейти в директорию проекта
cd /root/rentsense

# 2. Установить Docker (если еще не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
apt install docker-compose -y

# 3. Установить системные зависимости
apt update
apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 wget git

# 4. Настроить .env (заменить пароли!)
nano .env
# Найдите CHANGE_THIS_TO_STRONG_PASSWORD и замените на надежный пароль
# Сохраните: Ctrl+X, Y, Enter

# 5. Создать необходимые директории
mkdir -p logs backups data/raw data/processed

# 6. Запустить сервисы
docker-compose -f docker-compose.prod.yml up -d --build

# 7. Подождать запуска MySQL (30-60 секунд)
sleep 60

# 8. Инициализировать БД
docker-compose -f docker-compose.prod.yml exec backend python create_database.py
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db

# 9. Настроить бэкапы
chmod +x backup_to_cloud.sh
mv backup_to_cloud.sh backup_db.sh
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh >> logs/backup.log 2>&1") | crontab -

# 10. Тестовый бэкап
./backup_db.sh
```

### Шаг 4: Проверка

```bash
# Проверить контейнеры
docker-compose -f docker-compose.prod.yml ps

# Проверить логи
docker-compose -f docker-compose.prod.yml logs -f

# Тест парсера
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import apartPage
result = apartPage(['311739319'], dbinsert=True)
print('Result:', result)
"

# Проверить данные
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_PASSWORD rentsense -e "SELECT COUNT(*) FROM offers;"
```

## 📋 Чеклист

- [ ] Подключился к серверу (ssh root@89.110.92.128)
- [ ] Загрузил проект на сервер
- [ ] Установил Docker и Docker Compose
- [ ] Настроил .env (заменил пароли!)
- [ ] Запустил docker-compose
- [ ] Инициализировал БД
- [ ] Настроил бэкапы
- [ ] Протестировал парсер
- [ ] Проверил бэкап в облако

## ⚠️ Важно

1. **Замените пароли** в `.env` на надежные!
2. **Сохраните пароли** в надежном месте (менеджер паролей)
3. **Проверьте бэкапы** - они должны загружаться в Yandex Object Storage

## 📞 Если что-то пошло не так

```bash
# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Перезапуск
docker-compose -f docker-compose.prod.yml restart

# Проверка ресурсов
free -h
df -h
docker stats
```

