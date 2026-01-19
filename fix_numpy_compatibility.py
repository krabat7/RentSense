"""
Скрипт для проверки и исправления совместимости NumPy
"""
import subprocess
import sys

def check_numpy():
    try:
        import numpy as np
        version = np.__version__
        major_version = int(version.split('.')[0])
        print(f"Текущая версия NumPy: {version}")
        
        if major_version >= 2:
            print("\n⚠️ Обнаружен NumPy 2.x, который может вызывать проблемы совместимости")
            print("   с matplotlib, seaborn и другими библиотеками.")
            print("\nРекомендуется понизить до NumPy 1.x:")
            print("   pip install 'numpy<2'")
            
            response = input("\nХотите понизить NumPy сейчас? (y/n): ")
            if response.lower() == 'y':
                print("Устанавливаю NumPy <2...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "'numpy<2'"])
                print("✅ NumPy успешно понижен!")
                print("⚠️ Перезапустите ядро Jupyter для применения изменений")
            else:
                print("Пропущено. Продолжайте на свой риск.")
        else:
            print("✓ NumPy версия <2, совместимость должна быть нормальной")
            
    except ImportError:
        print("NumPy не установлен")
    except Exception as e:
        print(f"Ошибка при проверке NumPy: {e}")

if __name__ == "__main__":
    check_numpy()

