# Детальная инструкция по исправлению backend на сервере

## Проблема
Backend контейнер не может найти модуль `app` из-за отсутствия `PYTHONPATH`.

## Решение: Добавить PYTHONPATH в docker-compose.prod.yml

### Шаг 1: Открыть файл для редактирования
```bash
cd /root/rentsense
nano docker-compose.prod.yml
```

### Шаг 2: Найти секцию backend
В файле найдите секцию `backend:` (примерно строка 2-23)

Должно выглядеть так:
```yaml
  backend:
    build: .
    restart: unless-stopped
    environment:
      TZ: Europe/Moscow
      DB_TYPE: mysql+pymysql
      DB_LOGIN: root
      ...
```

### Шаг 3: Добавить PYTHONPATH
В секции `environment:` добавьте строку `PYTHONPATH: /app` после `TZ: Europe/Moscow`

**Должно стать:**
```yaml
  backend:
    build: .
    restart: unless-stopped
    environment:
      TZ: Europe/Moscow
      PYTHONPATH: /app
      DB_TYPE: mysql+pymysql
      DB_LOGIN: root
      DB_PASS: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      DB_IP: mysql
      DB_PORT: 3306
      DB_NAME: rentsense
```

**ВАЖНО:** Отступы должны быть одинаковые! Используйте пробелы, а не табы.

### Шаг 4: Сохранить и выйти из nano
- Нажмите `Ctrl + O` (сохранить)
- Нажмите `Enter` (подтвердить имя файла)
- Нажмите `Ctrl + X` (выйти)

### Шаг 5: Проверить изменения
```bash
grep -A 3 "environment:" docker-compose.prod.yml | head -10
```

Должна быть строка `PYTHONPATH: /app`

### Шаг 6: Остановить старый контейнер
```bash
docker-compose -f docker-compose.prod.yml down backend
```

### Шаг 7: Удалить старый контейнер (если нужно)
```bash
docker-compose -f docker-compose.prod.yml rm -f backend
```

### Шаг 8: Запустить backend с новой конфигурацией
```bash
docker-compose -f docker-compose.prod.yml up -d backend
```

### Шаг 9: Подождать 10 секунд
```bash
sleep 10
```

### Шаг 10: Проверить статус
```bash
docker-compose -f docker-compose.prod.yml ps backend
```

Должно быть `Up` (не `Restarting`)

### Шаг 11: Проверить логи
```bash
docker-compose -f docker-compose.prod.yml logs backend | tail -30
```

**Успех:** Не должно быть ошибок `ModuleNotFoundError: No module named 'app'`

### Шаг 12: Проверить health endpoint
```bash
curl http://localhost:8000/health
```

**Ожидаемый результат:** `{"status":"ok"}`

---

## Альтернативный способ (через sed)

Если не хотите редактировать вручную, можно использовать sed:

```bash
cd /root/rentsense

# Создать резервную копию
cp docker-compose.prod.yml docker-compose.prod.yml.bak

# Добавить PYTHONPATH после TZ
sed -i '/TZ: Europe\/Moscow/a\      PYTHONPATH: /app' docker-compose.prod.yml

# Проверить изменения
grep -A 2 "TZ:" docker-compose.prod.yml | head -5

# Пересоздать контейнер
docker-compose -f docker-compose.prod.yml down backend
docker-compose -f docker-compose.prod.yml up -d backend

# Проверить логи через 10 секунд
sleep 10
docker-compose -f docker-compose.prod.yml logs backend | tail -20
```

---

## Если что-то пошло не так

### Восстановить из резервной копии:
```bash
cp docker-compose.prod.yml.bak docker-compose.prod.yml
```

### Посмотреть текущую конфигурацию контейнера:
```bash
docker inspect rentsense_backend_1 | grep -A 20 "Env"
```

Должна быть строка с `PYTHONPATH=/app`

