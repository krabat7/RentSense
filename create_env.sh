#!/bin/bash
# Создать .env файл на сервере

cat > /root/rentsense/.env << 'EOF'
DB_TYPE=mysql+pymysql
DB_LOGIN=root
DB_PASS=CHANGE_THIS_TO_STRONG_PASSWORD
DB_IP=mysql
DB_PORT=3306
DB_NAME=rentsense

MYSQL_ROOT_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
MYSQL_PASSWORD=rentsense

PROXY1=http://gPrh7mayd7:cDs82GsH8e@46.161.29.91:31638
PROXY2=http://gF5CdZ3tVh:WBF5P4a7uW@46.161.29.212:36095
PROXY3=http://Y34xbQACPJ:pQVJx66wc2@83.171.240.229:32844
PROXY4=http://Tz8am3:EY5U7F@209.127.142.50:9709
PROXY5=http://Tz8am3:EY5U7F@168.196.238.113:9267

BACKUP_TYPE=yandex
YANDEX_ACCESS_KEY=YCAJEhxLcNZ_zudb0rzs9Vo7o
YANDEX_SECRET_KEY=YCONmXbp4fD1YH_p_lb547nc0Le2UXfy6F_3-8nq
YANDEX_BUCKET=rentsense-bucket

MLFLOW_TRACKING_URI=http://localhost:5000
EOF

echo ".env file created. Now edit it:"
echo "nano /root/rentsense/.env"
echo "Replace CHANGE_THIS_TO_STRONG_PASSWORD with a strong password (2 times)"

