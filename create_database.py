import pymysql
from dotenv import dotenv_values
from pathlib import Path

env_path = Path(__file__).parent / '.env'
env = dotenv_values(env_path)
host = env.get('DB_IP') or 'localhost'
port = int(env.get('DB_PORT') or '3307')
user = env.get('DB_LOGIN') or 'root'
password = env.get('DB_PASS') or 'rootpassword'
dbname = env.get('DB_NAME') or 'rentsense'

import time
max_retries = 10
for i in range(max_retries):
    try:
        connection = pymysql.connect(host=host, port=port, user=user, password=password, connect_timeout=5)
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {dbname} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            print(f"База данных {dbname} создана успешно")
        connection.close()
        break
    except Exception as e:
        if i < max_retries - 1:
            print(f"Повтор {i+1}/{max_retries}: MySQL не готов, ожидание...")
            time.sleep(5)
        else:
            print(f"Ошибка создания базы данных: {e}")

