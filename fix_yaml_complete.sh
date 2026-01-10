cd /root/rentsense && \
echo "=== Восстановление docker-compose.prod.yml ===" && \
cat > docker-compose.prod.yml << 'EOF'
services:
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
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
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
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-rootpassword}"]
      interval: 5s
      timeout: 3s
      retries: 10
    command: --default-authentication-plugin=mysql_native_password

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

volumes:
  mysql_data:
    driver: local
EOF
echo "✓ docker-compose.prod.yml восстановлен" && \
echo "" && \
echo "=== Проверка YAML синтаксиса ===" && \
python3 -c "import yaml; yaml.safe_load(open('docker-compose.prod.yml'))" && echo "✓ YAML синтаксис корректен" || echo "❌ Ошибка YAML" && \
echo "" && \
echo "=== Перезапуск backend ===" && \
docker-compose -f docker-compose.prod.yml stop backend && \
docker-compose -f docker-compose.prod.yml rm -f backend && \
docker-compose -f docker-compose.prod.yml up -d backend && \
sleep 60 && \
echo "" && \
echo "=== Проверка статуса ===" && \
docker-compose -f docker-compose.prod.yml ps && \
echo "" && \
echo "=== Проверка health endpoint ===" && \
curl -f http://localhost:8000/health && echo "" && \
echo "✓ Все исправлено!"

