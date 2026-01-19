# Настройка автоматического pull на сервере

## Вариант 1: Через cron (простой, рекомендованный)

### Шаги:

1. **Подключитесь к серверу:**
   ```bash
   ssh root@89.110.92.128
   ```

2. **Перейдите в директорию проекта:**
   ```bash
   cd /root/RentSense  # или путь, где находится ваш проект
   ```

3. **Настройте автоматический pull каждые 5 минут:**
   ```bash
   crontab -e
   ```
   
   Добавьте строку:
   ```cron
   */5 * * * * cd /root/RentSense && /usr/bin/git pull origin main >> /var/log/git-pull.log 2>&1
   ```
   
   Или используйте готовый скрипт:
   ```bash
   # Скачайте скрипт на сервер
   curl -o setup_auto_pull.sh https://raw.githubusercontent.com/krabat7/RentSense/main/setup_auto_pull.sh
   chmod +x setup_auto_pull.sh
   ./setup_auto_pull.sh
   ```

4. **Проверьте, что задача добавлена:**
   ```bash
   crontab -l
   ```

5. **Просмотр логов:**
   ```bash
   tail -f /var/log/git-pull.log
   ```

### Настройка интервалов:

- **Каждую минуту:** `* * * * *`
- **Каждые 5 минут:** `*/5 * * * *`
- **Каждые 10 минут:** `*/10 * * * *`
- **Каждый час:** `0 * * * *`
- **Каждые 2 часа:** `0 */2 * * *`

---

## Вариант 2: Через GitHub webhook (моментально)

### Преимущества:
- ✅ Моментальное обновление при push
- ✅ Не нагружает сервер постоянными проверками

### Недостатки:
- ⚠️ Требует открытого порта на сервере
- ⚠️ Более сложная настройка

### Шаги:

1. **Установите webhook сервер на сервер:**
   ```bash
   ssh root@89.110.92.128
   cd /root
   wget https://github.com/adnanh/webhook/releases/latest/download/webhook-linux-amd64.tar.gz
   tar -xzf webhook-linux-amd64.tar.gz
   sudo mv webhook-linux-amd64/webhook /usr/local/bin/webhook
   rm -rf webhook-linux-amd64*
   ```

2. **Создайте скрипт для обработки webhook:**
   ```bash
   mkdir -p /root/RentSense/hooks
   cat > /root/RentSense/hooks/git-pull.sh << 'EOF'
   #!/bin/bash
   cd /root/RentSense
   git pull origin main
   # Перезапустить контейнеры, если нужно
   cd /root/RentSense && docker-compose -f docker-compose.prod.yml restart
   EOF
   chmod +x /root/RentSense/hooks/git-pull.sh
   ```

3. **Создайте конфигурацию webhook:**
   ```bash
   cat > /root/RentSense/hooks.json << EOF
   [
     {
       "id": "git-pull",
       "execute-command": "/root/RentSense/hooks/git-pull.sh",
       "command-working-directory": "/root/RentSense"
     }
   ]
   EOF
   ```

4. **Запустите webhook сервер:**
   ```bash
   # Для теста (в foreground)
   webhook -hooks /root/RentSense/hooks.json -verbose -port 9000
   
   # Или через systemd (для постоянной работы)
   cat > /etc/systemd/system/webhook.service << EOF
   [Unit]
   Description=Webhook server
   After=network.target
   
   [Service]
   Type=simple
   User=root
   ExecStart=/usr/local/bin/webhook -hooks /root/RentSense/hooks.json -verbose -port 9000
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   EOF
   
   systemctl daemon-reload
   systemctl enable webhook
   systemctl start webhook
   ```

5. **Откройте порт в файрволе (если есть):**
   ```bash
   # Для ufw
   ufw allow 9000/tcp
   
   # Для iptables
   iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
   ```

6. **Настройте webhook в GitHub:**
   - Перейдите в Settings → Webhooks → Add webhook
   - Payload URL: `http://89.110.92.128:9000/hooks/git-pull`
   - Content type: `application/json`
   - Secret: (опционально, создайте случайную строку)
   - Events: выберите "Just the push event"
   - Active: ✓

---

## Вариант 3: Через systemd timer (альтернатива cron)

Создайте сервис и таймер:

```bash
# Создайте сервис
cat > /etc/systemd/system/git-pull.service << EOF
[Unit]
Description=Git pull for RentSense
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/RentSense
ExecStart=/usr/bin/git pull origin main
StandardOutput=append:/var/log/git-pull.log
StandardError=append:/var/log/git-pull.log
EOF

# Создайте таймер
cat > /etc/systemd/system/git-pull.timer << EOF
[Unit]
Description=Git pull timer for RentSense
Requires=git-pull.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# Активируйте
systemctl daemon-reload
systemctl enable git-pull.timer
systemctl start git-pull.timer
```

---

## Рекомендации

**Для начала используйте вариант 1 (cron)** - он самый простой и надежный.

**Если нужен мгновенный обновление** - используйте вариант 2 (webhook).

**Для production** рекомендуется комбинировать:
- Webhook для быстрого обновления
- Cron как fallback (на случай, если webhook не сработал)

---

## Проверка работы

После настройки проверьте:

```bash
# Проверьте логи cron
tail -f /var/log/git-pull.log

# Или проверьте crontab
crontab -l

# Проверьте последний pull
cd /root/RentSense && git log -1
```

## Важно!

Если вы используете Docker, после git pull может понадобиться перезапуск контейнеров:

```bash
cd /root/RentSense
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

Можно автоматизировать это в скрипте pull.

