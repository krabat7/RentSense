#!/bin/bash
# Оптимизация для сервера с 1 GB RAM

echo "Оптимизация конфигурации для сервера с 1 GB RAM..."

# Обновление docker-compose.prod.yml для ограничения ресурсов
cat > docker-compose.prod.yml << 'EOF'
services:
  backend:
    build: .
    restart: unless-stopped
    environment:
      TZ: Europe/Moscow
      DB_TYPE: mysql+pymysql
      DB_LOGIN: root
      DB_PASS: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      DB_IP: mysql
      DB_PORT: 3306
      DB_NAME: rentsense
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./:/app
      - ./logs:/app/logs
      - ./data:/app/data
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 300M
        reservations:
          memory: 200M
    ports:
      - "8000:8000"
    command: python app/main.py

  mysql:
    image: mysql:8.0
    restart: unless-stopped
    environment:
      TZ: Europe/Moscow
      MYSQL_DATABASE: rentsense
      MYSQL_USER: rentsense
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-rentsense}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./backups:/backups
    ports:
      - "3306:3306"
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 500M
        reservations:
          memory: 300M
    command: >
      --default-authentication-plugin=mysql_native_password
      --innodb-buffer-pool-size=256M
      --max-connections=50
      --query-cache-size=0
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-rootpassword}"]
      interval: 5s
      timeout: 3s
      retries: 10

  parser:
    build: .
    restart: "no"
    environment:
      TZ: Europe/Moscow
      DB_TYPE: mysql+pymysql
      DB_LOGIN: root
      DB_PASS: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      DB_IP: mysql
      DB_PORT: 3306
      DB_NAME: rentsense
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./:/app
      - ./logs:/app/logs
      - ./data:/app/data
    deploy:
      resources:
        limits:
          cpus: '0.3'
          memory: 400M
        reservations:
          memory: 300M
    command: python -m app.scheduler.crontab

volumes:
  mysql_data:
    driver: local
EOF

echo "✓ Конфигурация обновлена для 1 GB RAM"
echo ""
echo "Настройки MySQL оптимизированы:"
echo "  - innodb-buffer-pool-size: 256M (вместо дефолтных 512M)"
echo "  - max-connections: 50 (вместо дефолтных 151)"
echo "  - query-cache отключен (экономит память)"
echo ""
echo "Парсер ограничен:"
echo "  - CPU: 0.3 core"
echo "  - RAM: 400M"
echo ""
echo "Рекомендации:"
echo "  1. Запускать парсер по расписанию (cron), а не постоянно"
echo "  2. Регулярно очищать старые данные (старше 6 месяцев)"
echo "  3. Мониторить использование: docker stats"
echo "  4. При необходимости увеличить swap: fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile"

