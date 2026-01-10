cd /root/rentsense && \
echo "=== Исправление docker-compose.prod.yml (правильная структура) ===" && \
python3 << 'EOF'
with open('docker-compose.prod.yml', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
in_backend = False

while i < len(lines):
    line = lines[i]
    
    # Найти начало секции backend
    if line.strip().startswith('backend:'):
        in_backend = True
        new_lines.append(line)
        i += 1
        continue
    
    # Если внутри секции backend
    if in_backend:
        # Проверить, что следующая секция (mysql:)
        if line.strip().startswith('mysql:'):
            in_backend = False
            new_lines.append(line)
            i += 1
            continue
        
        # Пропустить неправильный healthcheck с портом
        if line.strip() == 'healthcheck:' and i + 1 < len(lines):
            next_line = lines[i + 1]
            if '"8000:8000"' in next_line or '8000:8000' in next_line:
                # Это неправильный healthcheck - заменить на ports:
                new_lines.append('    ports:\n')
                new_lines.append('      - "8000:8000"\n')
                i += 2  # пропустить healthcheck: и строку с портом
                continue
        
        # Если встретили правильный healthcheck, пропустить его (добавим позже)
        if line.strip() == 'healthcheck:' and i + 1 < len(lines):
            next_line = lines[i + 1]
            if 'test: ["CMD", "curl"' in next_line:
                # Пропустить весь блок healthcheck (мы добавим его после ports)
                while i < len(lines) and not (lines[i].strip().startswith('command:') or lines[i].strip().startswith('mysql:')):
                    if 'start_period:' in lines[i]:
                        i += 1
                        break
                    i += 1
                continue
    
    new_lines.append(line)
    i += 1

# Теперь нужно вставить правильный healthcheck после ports в backend
result = []
i = 0
found_ports = False

while i < len(new_lines):
    line = new_lines[i]
    result.append(line)
    
    if 'ports:' in line and 'backend' in '\n'.join(result[-10:]):  # В секции backend
        found_ports = True
        i += 1
        # Добавить порт, если его нет
        if i < len(new_lines) and '"8000:8000"' in new_lines[i]:
            result.append(new_lines[i])
            i += 1
        # После ports добавить healthcheck (если еще не добавлен)
        if i < len(new_lines) and 'healthcheck:' not in new_lines[i]:
            result.append('    healthcheck:\n')
            result.append('      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]\n')
            result.append('      interval: 30s\n')
            result.append('      timeout: 10s\n')
            result.append('      retries: 5\n')
            result.append('      start_period: 40s\n')
        continue
    
    i += 1

with open('docker-compose.prod.yml', 'w') as f:
    f.writelines(result)

print('✓ docker-compose.prod.yml исправлен')
EOF
echo "" && \
echo "=== Проверка исправленного файла ===" && \
sed -n '/^  backend:/,/^  mysql:/p' docker-compose.prod.yml && \
echo "" && \
echo "=== Проверка логов backend ===" && \
docker-compose -f docker-compose.prod.yml logs backend | tail -30 && \
echo "" && \
echo "=== Перезапуск backend ===" && \
docker-compose -f docker-compose.prod.yml stop backend && \
docker-compose -f docker-compose.prod.yml rm -f backend && \
docker-compose -f docker-compose.prod.yml up -d backend && \
sleep 60 && \
echo "=== Проверка статуса ===" && \
docker-compose -f docker-compose.prod.yml ps backend

