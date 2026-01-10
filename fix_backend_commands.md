# Команды для исправления backend

## ШАГ 1: Удалить старый контейнер по ID
```bash
cd /root/rentsense

# Удалить контейнер по ID
docker rm 59fc61d29058

# Или удалить все остановленные контейнеры backend
docker ps -a | grep backend | awk '{print $1}' | xargs docker rm

# Проверить, что удален
docker ps -a | grep backend
```

## ШАГ 2: Открыть файл для редактирования
```bash
nano docker-compose.prod.yml
```

## ШАГ 3: Исправить файл

### В секции backend (строка ~152):
Заменить `condition: service_healthy` на `condition: service_started`

### В секции parser (строка ~192):
Добавить после `TZ: Europe/Moscow`:
```
      PYTHONPATH: /app
```

### В секции parser (строка ~201):
Заменить `condition: service_healthy` на `condition: service_started`

## ШАГ 4: Сохранить (Ctrl+O, Enter, Ctrl+X)

## ШАГ 5: Проверить и запустить
```bash
# Проверить изменения
grep "PYTHONPATH" docker-compose.prod.yml
grep "condition:" docker-compose.prod.yml

# Запустить
docker-compose -f docker-compose.prod.yml up -d backend

# Подождать и проверить
sleep 15
docker-compose -f docker-compose.prod.yml ps backend
docker-compose -f docker-compose.prod.yml logs backend | tail -40
curl http://localhost:8000/health
```

