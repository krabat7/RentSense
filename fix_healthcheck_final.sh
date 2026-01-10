cd /root/rentsense && \
echo "=== Исправление docker-compose.prod.yml ===" && \
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
        
        # Найти неправильный healthcheck (с портом)
        if 'healthcheck:' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            if '"8000:8000"' in next_line or '"8000"' in next_line:
                # Пропустить этот неправильный healthcheck и порт
                i += 2
                continue
        
        # Найти правильный healthcheck (с curl)
        if 'healthcheck:' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            if 'test: ["CMD", "curl"' in next_line:
                # Это правильный healthcheck, но нужно проверить его позицию
                # Он должен быть после ports:, но перед command:
                new_lines.append(line)
                i += 1
                # Добавить весь блок healthcheck
                while i < len(lines) and (lines[i].strip().startswith('test:') or 
                                          lines[i].strip().startswith('interval:') or
                                          lines[i].strip().startswith('timeout:') or
                                          lines[i].strip().startswith('retries:') or
                                          lines[i].strip().startswith('start_period:') or
                                          lines[i].strip() == ''):
                    new_lines.append(lines[i])
                    i += 1
                continue
        
        # Если нашли ports: в backend, добавить его и healthcheck после
        if 'ports:' in line and in_backend:
            new_lines.append(line)
            i += 1
            # Добавить порты
            while i < len(lines) and (lines[i].strip().startswith('-') or lines[i].strip().startswith('"') or lines[i].strip() == ''):
                if '"8000:8000"' in lines[i] or '"8000"' in lines[i]:
                    new_lines.append(lines[i])
                i += 1
            # Добавить healthcheck после ports
            new_lines.append('    healthcheck:\n')
            new_lines.append('      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]\n')
            new_lines.append('      interval: 30s\n')
            new_lines.append('      timeout: 10s\n')
            new_lines.append('      retries: 5\n')
            new_lines.append('      start_period: 40s\n')
            continue
    
    new_lines.append(line)
    i += 1

with open('docker-compose.prod.yml', 'w') as f:
    f.writelines(new_lines)

print('✓ docker-compose.prod.yml исправлен')
EOF
echo "" && \
echo "=== Проверка исправленного файла ===" && \
grep -A 10 "backend:" docker-compose.prod.yml | head -20 && \
echo "" && \
echo "=== Перезапуск backend ===" && \
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend && \
sleep 60 && \
echo "=== Проверка статуса ===" && \
docker-compose -f docker-compose.prod.yml ps backend

