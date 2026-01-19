"""
Конфигурация MLflow для проекта RentSense.
"""
import os
import mlflow
from pathlib import Path

# Получаем путь к корню проекта (на 2 уровня выше от этого файла)
PROJECT_ROOT = Path(__file__).parent.parent

# Настройка tracking URI из переменной окружения или по умолчанию
# На Windows используем просто путь, на Linux/Mac - file://
_default_uri = str(PROJECT_ROOT / 'mlruns')
if os.name == 'nt':  # Windows
    # На Windows используем просто путь или SQLite
    MLFLOW_TRACKING_URI = os.getenv(
        'MLFLOW_TRACKING_URI',
        f'sqlite:///{PROJECT_ROOT}/mlflow.db'
    )
else:  # Linux/Mac
    MLFLOW_TRACKING_URI = os.getenv(
        'MLFLOW_TRACKING_URI',
        f'file://{_default_uri}'
    )

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Имя эксперимента
EXPERIMENT_NAME = "rentsense-rent-prediction"

def get_or_create_experiment(experiment_name: str = EXPERIMENT_NAME):
    """
    Получить или создать эксперимент MLflow.
    
    Args:
        experiment_name: Имя эксперимента
        
    Returns:
        experiment_id: ID эксперимента
    """
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
        print(f"[OK] Создан новый эксперимент: {experiment_name} (ID: {experiment_id})")
    except Exception as e:
        # Эксперимент уже существует
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            raise Exception(f"Не удалось создать или найти эксперимент: {e}")
        experiment_id = experiment.experiment_id
        print(f"[OK] Используется существующий эксперимент: {experiment_name} (ID: {experiment_id})")
    
    mlflow.set_experiment(experiment_name)
    return experiment_id


def init_mlflow():
    """
    Инициализация MLflow для проекта.
    """
    experiment_id = get_or_create_experiment()
    print(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"Эксперимент: {EXPERIMENT_NAME}")
    return experiment_id


if __name__ == "__main__":
    # Тестирование конфигурации
    print("=== Тестирование MLflow конфигурации ===")
    try:
        experiment_id = init_mlflow()
        print(f"[OK] MLflow настроен успешно! Experiment ID: {experiment_id}")
        
        # Тест записи в MLflow
        with mlflow.start_run(run_name="test_run"):
            mlflow.log_param("test_param", "test_value")
            mlflow.log_metric("test_metric", 0.95)
            print("[OK] Тестовая запись в MLflow создана успешно!")
            
    except Exception as e:
        print(f"[ERROR] Ошибка настройки MLflow: {e}")
        import traceback
        traceback.print_exc()

