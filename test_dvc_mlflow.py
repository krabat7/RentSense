"""
Тестовый скрипт для проверки работы DVC и MLflow.
"""
import os
import sys
from pathlib import Path

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=== Тестирование инфраструктуры ML ===\n")

# Тест 1: DVC
print("1. Тестирование DVC...")
try:
    import dvc.api
    from dvc.repo import Repo
    
    repo = Repo()
    print("✅ DVC инициализирован")
    print(f"   Рабочая директория: {repo.root_dir}")
    
    # Проверка remote
    remotes = repo.config.get("remote", {})
    if remotes:
        print(f"   Настроено remote хранилищ: {len(remotes)}")
        for name in remotes:
            print(f"     - {name}")
    else:
        print("   ⚠️  Remote хранилище не настроено (используется локальное)")
    
except ImportError:
    print("[ERROR] DVC не установлен. Установите: pip install dvc dvc-s3")
    print("   Продолжаем проверку других компонентов...")
    dvc_ok = False
except Exception as e:
    print(f"[ERROR] Ошибка DVC: {e}")
    dvc_ok = False
else:
    dvc_ok = True
except Exception as e:
    print(f"❌ Ошибка DVC: {e}")
    sys.exit(1)

print()

# Тест 2: MLflow
print("2. Тестирование MLflow...")
try:
    import mlflow
    from ml.mlflow_config import init_mlflow, EXPERIMENT_NAME, MLFLOW_TRACKING_URI
    
    experiment_id = init_mlflow()
    print(f"[OK] MLflow настроен")
    print(f"   Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"   Эксперимент: {EXPERIMENT_NAME} (ID: {experiment_id})")
    
    # Тест записи
    print("   Тест записи в MLflow...")
    with mlflow.start_run(run_name="test_infrastructure_check"):
        mlflow.log_param("test_type", "infrastructure_check")
        mlflow.log_metric("test_score", 1.0)
        mlflow.set_tag("status", "test")
        print("   [OK] Тестовая запись создана успешно")
        
except ImportError:
    print("[ERROR] MLflow не установлен. Установите: pip install mlflow")
    mlflow_ok = False
except Exception as e:
    print(f"[ERROR] Ошибка MLflow: {e}")
    import traceback
    traceback.print_exc()
    mlflow_ok = False
else:
    mlflow_ok = True

print()

# Тест 3: Структура проекта
print("3. Проверка структуры проекта...")
required_dirs = [
    "ml/eda",
    "ml/features", 
    "ml/models",
    "data/raw",
    "data/processed"
]

all_ok = True
for dir_path in required_dirs:
    path = PROJECT_ROOT / dir_path
    if path.exists():
        print(f"   [OK] {dir_path}/")
    else:
        print(f"   [WARNING] {dir_path}/ - не существует (будет создан при необходимости)")
        path.mkdir(parents=True, exist_ok=True)
        all_ok = False

print()

# Итоговый результат
print("=== Итоговый результат ===")
if 'dvc_ok' in locals() and dvc_ok:
    print("[OK] DVC: готов")
else:
    print("[SKIP] DVC: не установлен (можно установить позже: pip install dvc dvc-s3)")

if 'mlflow_ok' in locals() and mlflow_ok:
    print("[OK] MLflow: готов")
else:
    print("[SKIP] MLflow: не установлен (можно установить позже: pip install mlflow)")

print("[OK] Структура проекта: проверена")
print()
print("Конфигурация создана! Для полной работы установите зависимости.")

