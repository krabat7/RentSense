#!/bin/bash
# Скрипт для добавления новых прокси в .env на сервере

echo "Добавление новых прокси в .env..."

# Новые прокси (11 штук)
cat >> .env << 'EOF'

# Новые прокси (добавлено 2026-01-15)
PROXY15=http://4D7D7f:mE9cRE@213.139.222.69:9010
PROXY16=http://4D7D7f:mE9cRE@213.139.222.149:9516
PROXY17=http://4D7D7f:mE9cRE@213.139.223.145:9193
PROXY18=http://4D7D7f:mE9cRE@213.139.222.227:9625
PROXY19=http://HrkB8A:GoTkpe@212.102.145.24:9687
PROXY20=http://HrkB8A:GoTkpe@212.102.144.77:9656
PROXY21=http://HrkB8A:GoTkpe@178.171.43.146:9912
PROXY22=http://okJ0KF:9LmuSc@194.67.219.124:9425
PROXY23=http://okJ0KF:9LmuSc@194.67.222.245:9817
PROXY24=http://okJ0KF:9LmuSc@194.67.223.76:9814
PROXY25=http://okJ0KF:9LmuSc@194.67.219.15:9043
EOF

echo "Прокси добавлены (PROXY15-PROXY25)"
echo "Всего прокси теперь: 25"

