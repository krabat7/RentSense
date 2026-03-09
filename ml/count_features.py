"""Число признаков после фичей v2 и отбора по корреляции. Требуется data/processed/train.csv."""

import sys
from pathlib import Path

import pandas as pd

# Подключаем ml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.train_baseline import prepare_features


def main():
    data_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
    train_path = data_dir / "train.csv"

    if not train_path.exists():
        print(f"Не найден: {train_path}")
        sys.exit(1)

    train_df = pd.read_csv(train_path)
    X, y, cat_cols, num_cols, feature_cols = prepare_features(
        train_df, use_correlation_filter=True, min_correlation=0.01
    )
    print(f"Признаков: {len(feature_cols)} (числовых: {len(num_cols)}, категориальных: {len(cat_cols)})")


if __name__ == "__main__":
    main()
