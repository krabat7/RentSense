#!/usr/bin/env python3
"""Сбор train/test из БД (prepare_data) и обучение baseline (train_baseline_models, log-цель).

Пример cron (ежемесячно, 03:00), каталог с docker-compose.prod.yml, свой путь:

    0 3 1 * * cd /path/to/RentSense && docker compose -f docker-compose.prod.yml exec -T backend python scripts/monthly_model_retrain.py >> logs/monthly_retrain.log 2>&1

Требуются те же DB_* в окружении, что у ml/prepare_data. Новые веса в ml/models подхватывает API при рестарте или через общий volume.
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
