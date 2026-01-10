# Исправление healthcheck для backend

## Проблема
Backend показывает `Up (unhealthy)`, хотя health endpoint работает.

## Решение

### ШАГ 1: Проверить текущий healthcheck на сервере
```bash
cd /root/rentsense
cat docker-compose.prod.yml | grep -A 10 "healthcheck" | head -15
```

### ШАГ 2: Открыть файл для редактирования
```bash
nano docker-compose.prod.yml
```

### ШАГ 3: Найти секцию backend и добавить healthcheck

**Найти строки (примерно после строки 20):**
```yaml
    ports:
      - "8000:8000"
    command: python app/main.py
```

**Добавить перед `command:` (после `ports:`):**
```yaml
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    command: python app/main.py
```

**Важно:** Отступы должны быть одинаковые (4 пробела перед `healthcheck:`)

### ШАГ 4: Сохранить файл
`Ctrl+O` → `Enter` → `Ctrl+X`

### ШАГ 5: Перезапустить backend
```bash
docker-compose -f docker-compose.prod.yml up -d backend

# Подождать 60 секунд (start_period + проверки)
sleep 60

# Проверить статус
docker-compose -f docker-compose.prod.yml ps backend
```

### ШАГ 6: Проверить parser процесс

```bash
# Проверить, что parser запущен
docker exec rentsense_parser_1 ps aux

# Проверить логи parser
docker-compose -f docker-compose.prod.yml logs parser | tail -50

# Если процесса нет, перезапустить parser
docker-compose -f docker-compose.prod.yml restart parser
sleep 5
docker exec rentsense_parser_1 ps aux | grep python
```

