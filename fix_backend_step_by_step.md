# Детальная инструкция: Исправление backend на сервере

## Проблема
1. Ошибка `KeyError: 'ContainerConfig'` - баг docker-compose при пересоздании контейнера
2. В parser нет PYTHONPATH
3. depends_on использует service_healthy вместо service_started

## Решение

### ШАГ 1: Удалить старый контейнер вручную
```bash
cd /root/rentsense

# Остановить контейнер
docker stop rentsense_backend_1

# Удалить контейнер
docker rm rentsense_backend_1

# Проверить, что контейнер удален
docker ps -a | grep backend
```

### ШАГ 2: Открыть docker-compose.prod.yml для редактирования
```bash
nano docker-compose.prod.yml
```

### ШАГ 3: Исправить backend секцию

Найдите секцию `backend:` (примерно строка 138-165)

**Изменить:**
1. В `depends_on` заменить `condition: service_healthy` на `condition: service_started` (строка 152)
2. PYTHONPATH уже есть (строка 143) - оставить как есть

**Должно быть:**
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
    depends_on:
      mysql:
        condition: service_started
    volumes:
      - ./:/app
      - ./logs:/app/logs
      - ./data:/app/data
    healthcheck:
       test: ["CMD-SHELL", "ps aux | grep -q '[p]ython.*app/main.py' || exit 1"]
       interval: 30s
       timeout: 10s
       retries: 5
       start_period: 120s
    ports:
      - "8000:8000"
    command: python app/main.py
```

### ШАГ 4: Добавить PYTHONPATH в parser секцию

Найдите секцию `parser:` (примерно строка 188-206)

**Добавить `PYTHONPATH: /app` после `TZ: Europe/Moscow`**

**Должно быть:**
```yaml
  parser:
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
    depends_on:
      mysql:
        condition: service_started
    volumes:
      - ./:/app
      - ./logs:/app/logs
      - ./data:/app/data
    command: python -m app.scheduler.crontab
```

**ВАЖНО:** 
- В parser тоже изменить `condition: service_healthy` на `condition: service_started`

### ШАГ 5: Сохранить файл
- `Ctrl + O` → `Enter` → `Ctrl + X`

### ШАГ 6: Проверить изменения
```bash
# Проверить backend
grep -A 15 "^  backend:" docker-compose.prod.yml | head -20

# Проверить parser
grep -A 15 "^  parser:" docker-compose.prod.yml | head -20

# Проверить PYTHONPATH в обоих
grep "PYTHONPATH" docker-compose.prod.yml
```

Должно быть 2 строки с `PYTHONPATH: /app`

### ШАГ 7: Запустить backend
```bash
docker-compose -f docker-compose.prod.yml up -d backend
```

### ШАГ 8: Подождать и проверить
```bash
# Подождать 15 секунд
sleep 15

# Проверить статус
docker-compose -f docker-compose.prod.yml ps backend

# Проверить логи
docker-compose -f docker-compose.prod.yml logs backend | tail -40
```

**Успех:** Не должно быть `ModuleNotFoundError: No module named 'app'`

### ШАГ 9: Проверить health endpoint
```bash
curl http://localhost:8000/health
```

**Ожидаемый результат:** `{"status":"ok"}`

---

## Альтернатива: Автоматическое исправление через sed

Если не хотите редактировать вручную:

```bash
cd /root/rentsense

# Создать резервную копию
cp docker-compose.prod.yml docker-compose.prod.yml.bak

# Удалить старый контейнер
docker stop rentsense_backend_1 2>/dev/null
docker rm rentsense_backend_1 2>/dev/null

# Исправить depends_on в backend (service_healthy -> service_started)
sed -i 's/condition: service_healthy/condition: service_started/g' docker-compose.prod.yml

# Добавить PYTHONPATH в parser (после TZ)
sed -i '/parser:/,/command:/ {
  /TZ: Europe\/Moscow/a\      PYTHONPATH: /app
}' docker-compose.prod.yml

# Или проще - заменить всю секцию environment в parser
# (но это сложнее, лучше вручную)

# Проверить изменения
grep -A 2 "PYTHONPATH" docker-compose.prod.yml
grep "condition:" docker-compose.prod.yml

# Запустить
docker-compose -f docker-compose.prod.yml up -d backend

# Проверить через 15 секунд
sleep 15
docker-compose -f docker-compose.prod.yml logs backend | tail -30
```

