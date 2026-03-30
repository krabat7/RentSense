#!/usr/bin/env python3
"""
Ежемесячное переобучение: prepare_data (БД в train/test CSV) + train_baseline_models.

Раз в месяц для долгосрочной аренды - нормальный компромисс: рынок
медленнее дневных колебаний, нагрузка на сервер умеренная.

Пример cron (1-е число, 03:00), из каталога с `docker-compose.prod.yml` на сервере
(путь замените на свой, ниже — типичный вариант для клона в `/root/RentSense`):

    0 3 1 * * cd /root/RentSense && docker compose -f docker-compose.prod.yml exec -T backend python scripts/monthly_model_retrain.py >> /root/RentSense/logs/monthly_retrain.log 2>&1

Нужен `.env` у compose с доступом к БД (как у `ml/prepare_data`). После прогона перезапусти API,
чтобы подхватить новый ml/models/catboost_baseline.model (или используй volume).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
for p in (str(ROOT), str(ML)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> None:
    from prepare_data import prepare_data
    from train_baseline import train_baseline_models

    print("=== 1/2 prepare_data ===", flush=True)
    prepare_data()
    print("=== 2/2 train_baseline_models (use_log_price=True) ===", flush=True)
    train_baseline_models(use_log_price=True)
    print("=== monthly_model_retrain: OK ===", flush=True)


if __name__ == "__main__":
    main()
