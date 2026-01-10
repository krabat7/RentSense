# Развертывание на сервере - Краткая инструкция

## Быстрый старт

### 1. Аренда сервера (рекомендуется)
- **Hetzner Cloud**: https://hetzner.com/cloud (~500₽/мес, 4GB RAM)
- **Selectel**: https://selectel.ru/vps/ (~800₽/мес)
- **Yandex Cloud**: https://cloud.yandex.ru/ (~1000₽/мес)

### 2. Установка на сервере

```bash
# Подключение
ssh root@your-server-ip

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
apt install docker-compose -y

# Клонирование проекта (или загрузка через scp)
git clone <your-repo> rentsense
cd rentsense

# Настройка .env (скопируйте из .env.example и заполните пароли)
cp .env.example .env
nano .env  # Замените YOUR_STRONG_PASSWORD_HERE

# Запуск
docker-compose -f docker-compose.prod.yml up -d --build

# Инициализация БД
docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db
```

### 3. Автоматические бэкапы

```bash
chmod +x backup_db.sh
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/rentsense && ./backup_db.sh") | crontab -
```

## Преимущества сервера

✅ **Данные сохраняются** - БД в Docker volume, не потеряется при перезагрузке  
✅ **Работает 24/7** - парсинг идет автоматически  
✅ **Автоматические бэкапы** - данные защищены  
✅ **Мониторинг** - можно отслеживать процесс  
✅ **Масштабируемость** - легко увеличить ресурсы

## Стоимость

- **Сервер**: ~500-1000₽/мес
- **Прокси**: у вас уже есть
- **Итого**: ~500-1000₽/мес

## Что дальше?

После развертывания на сервере можно:
1. Настроить автоматический парсинг (cron)
2. Настроить бэкапы БД
3. Начать собирать данные для модели

Полная инструкция: см. `DEPLOY.md`

