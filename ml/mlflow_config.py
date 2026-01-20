"""
Конфигурация MLflow для проекта RentSense.
"""
import os
import mlflow
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
_default_uri = str(PROJECT_ROOT / 'mlruns')
if os.name == 'nt':
    MLFLOW_TRACKING_URI = os.getenv(
        'MLFLOW_TRACKING_URI',
        f'sqlite:///{PROJECT_ROOT}/mlflow.db'
    )
else:
    MLFLOW_TRACKING_URI = os.getenv(
        'MLFLOW_TRACKING_URI',
        f'file://{_default_uri}'
    )

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
EXPERIMENT_NAME = "rentsense-rent-prediction"

def get_or_create_experiment(experiment_name: str = EXPERIMENT_NAME):
    """Получить или создать эксперимент MLflow."""
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
        print(f"Создан новый эксперимент: {experiment_name} (ID: {experiment_id})")
    except Exception as e:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            raise Exception(f"Не удалось создать или найти эксперимент: {e}")
        experiment_id = experiment.experiment_id
        print(f"Используется существующий эксперимент: {experiment_name} (ID: {experiment_id})")
    
    mlflow.set_experiment(experiment_name)
    return experiment_id


def init_mlflow():
    """Инициализация MLflow для проекта."""
    experiment_id = get_or_create_experiment()
    print(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"Эксперимент: {EXPERIMENT_NAME}")
    return experiment_id


if __name__ == "__main__":
    print("Тестирование MLflow конфигурации...")
    try:
        experiment_id = init_mlflow()
        print(f"MLflow настроен успешно. Experiment ID: {experiment_id}")
        
        with mlflow.start_run(run_name="test_run"):
            mlflow.log_param("test_param", "test_value")
            mlflow.log_metric("test_metric", 0.95)
            print("Тестовая запись в MLflow создана успешно")
            
    except Exception as e:
        print(f"Ошибка настройки MLflow: {e}")
        import traceback
        traceback.print_exc()

