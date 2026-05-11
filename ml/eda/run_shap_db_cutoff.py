"""
Разовый прогон SHAP с отбором офферов: offers.created_at <= заданного момента.
Использует тот же ETL, что prepare_data (без записи CSV на диск).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from dotenv import dotenv_values
from sqlalchemy import create_engine

ML = Path(__file__).resolve().parent.parent
ROOT = ML.parent
sys.path.insert(0, str(ML))

from prepare_data import (  # noqa: E402
    _db_setting,
    add_price_actual,
    clean_outliers,
    feature_engineering,
    fill_missing_values,
    filter_data,
    remove_duplicates,
    time_split,
)


def analyze_correlations(df, target_col="price_actual", min_corr=0.01):
    """Копия логики train_baseline (без импорта lightgbm)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target_col not in numeric_cols:
        return []
    correlations = {}
    for col in numeric_cols:
        if col != target_col:
            try:
                corr = df[[col, target_col]].corr().iloc[0, 1]
                if not np.isnan(corr):
                    correlations[col] = abs(corr)
            except Exception:
                pass
    return sorted(correlations.items(), key=lambda x: x[1], reverse=True)


def prepare_features(
    df,
    use_correlation_filter=True,
    min_correlation=0.01,
    max_numeric_features=None,
):
    """Копия train_baseline.prepare_features."""
    target_col = "price_actual" if "price_actual" in df.columns else "price"
    exclude_cols = [
        "cian_id",
        "price",
        "price_changes",
        "price_from_changes",
        "price_actual",
        "publication_at",
        "publication_date",
        "offer_created_at",
        "offer_updated_at",
        "description",
        "coordinates",
    ]
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    if use_correlation_filter:
        correlations = analyze_correlations(df, target_col, min_correlation)
        if correlations:
            low_corr_cols = [
                col for col, corr in correlations if abs(corr) < min_correlation
            ]
            feature_cols = [col for col in feature_cols if col not in low_corr_cols]
            if max_numeric_features is not None:
                corr_dict = dict(correlations)
                numeric_ordered = [c for c, _ in correlations if c in feature_cols]
                categorical_in_features = [
                    c for c in feature_cols if c not in corr_dict
                ]
                top_numeric = numeric_ordered[:max_numeric_features]
                feature_cols = top_numeric + categorical_in_features
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    y = pd.to_numeric(y, errors="coerce")
    categorical_cols_base = [
        "category",
        "county",
        "district",
        "street",
        "house",
        "metro",
        "travel_type",
        "repair_type",
        "windows_view",
        "material_type",
        "parking_type",
        "realty_type",
        "project_type",
        "heat_type",
        "gas_type",
        "deal_type",
        "flat_type",
        "payment_period",
        "developer_name",
        "district_encoded",
    ]
    categorical_cols = []
    numeric_cols = []
    for col in X.columns:
        if col in categorical_cols_base or X[col].dtype == "object":
            X[col] = X[col].astype(str).fillna("unknown")
            categorical_cols.append(col)
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce")
            if X[col].isna().any():
                X[col] = X[col].fillna(0)
            numeric_cols.append(col)
    return X, y, categorical_cols, numeric_cols, feature_cols


def _align_df_to_model(df: pd.DataFrame, model: CatBoostRegressor) -> pd.DataFrame:
    """Порядок и состав колонок = feature_names_, недостающие - 0 / 'unknown'."""
    names = list(model.feature_names_)
    cat_indices = list(model.get_cat_feature_indices())
    cat_names = {names[i] for i in cat_indices if 0 <= i < len(names)}
    out = pd.DataFrame(index=df.index)
    for name in names:
        if name in df.columns:
            ser = df[name]
            if name in cat_names:
                out[name] = ser.map(
                    lambda x: (
                        "unknown"
                        if pd.isna(x) or isinstance(x, (float, np.floating))
                        else (x if isinstance(x, (str, int)) else str(x))
                    )
                )
            else:
                out[name] = pd.to_numeric(ser, errors="coerce").fillna(0).values
        else:
            out[name] = "unknown" if name in cat_names else 0
    return out


# Дата отсечения для среза данных из ВКР.
OFFERS_CREATED_AT_LTE = "2026-03-31 00:21:11"

N_SAMPLES = 800
SEED = 42
TOP_PRINT = 25


def load_data_from_db_cutoff(engine) -> pd.DataFrame:
    query = f"""
    SELECT
        o.cian_id,
        o.price,
        o.price_changes,
        o.category,
        o.views_count,
        o.photos_count,
        o.floor_number,
        o.floors_count,
        o.publication_at,
        o.created_at as offer_created_at,
        o.updated_at as offer_updated_at,
        a.county,
        a.district,
        a.street,
        a.house,
        a.metro,
        a.travel_type,
        a.travel_time,
        a.coordinates,
        ri.repair_type,
        ri.total_area,
        ri.living_area,
        ri.kitchen_area,
        ri.ceiling_height,
        ri.balconies,
        ri.loggias,
        ri.rooms_count,
        ri.separated_wc,
        ri.combined_wc,
        ri.windows_view,
        ro.build_year,
        ro.entrances,
        ro.material_type,
        ro.parking_type,
        ro.garbage_chute,
        ro.lifts_count,
        ro.passenger_lifts,
        ro.cargo_lifts,
        rd.realty_type,
        rd.project_type,
        rd.heat_type,
        rd.gas_type,
        rd.is_apartment,
        rd.is_penthouse,
        rd.is_mortgage_allowed,
        rd.is_premium,
        rd.is_emergency,
        od.deal_type,
        od.flat_type,
        od.payment_period,
        od.deposit,
        od.prepay_months,
        od.utilities_included,
        od.client_fee,
        od.agent_fee,
        od.description,
        d.name as developer_name,
        d.review_count as developer_review_count,
        d.total_rate as developer_rate,
        d.buildings_count as developer_buildings_count,
        d.foundation_year as developer_foundation_year,
        d.is_reliable as developer_is_reliable
    FROM offers o
    LEFT JOIN addresses a ON o.cian_id = a.cian_id
    LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
    LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
    LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
    LEFT JOIN offers_details od ON o.cian_id = od.cian_id
    LEFT JOIN developers d ON o.cian_id = d.cian_id
    WHERE o.created_at <= '{OFFERS_CREATED_AT_LTE}'
    """
    return pd.read_sql(query, engine)


def main():
    env_path = ROOT / ".env"
    env = dotenv_values(env_path) or {}
    DBTYPE = _db_setting(env, "DB_TYPE", "mysql+pymysql")
    LOGIN = _db_setting(env, "DB_LOGIN", "root")
    PASS = _db_setting(env, "DB_PASS", "rootpassword")
    IP = _db_setting(env, "DB_IP", "127.0.0.1")
    PORT = _db_setting(env, "DB_PORT", "3306")
    DBNAME = _db_setting(env, "DB_NAME", "rentsense")
    url = f"{DBTYPE}://{LOGIN}:{PASS}@{IP}:{PORT}/{DBNAME}?charset=utf8mb4"
    engine = create_engine(url, pool_pre_ping=True)

    print("Загрузка (cutoff created_at)...", flush=True)
    df = load_data_from_db_cutoff(engine)
    rows_sql = len(df)
    print(f"Строк после SQL: {rows_sql}", flush=True)

    df = add_price_actual(df)
    df = filter_data(df)
    df = remove_duplicates(df)
    df = clean_outliers(df)
    df = feature_engineering(df)
    df = fill_missing_values(df)
    train_df, test_df = time_split(df, test_days=30)
    print(f"Train: {len(train_df)}, test: {len(test_df)}", flush=True)

    X_train, _, _, _, _ = prepare_features(
        train_df,
        use_correlation_filter=True,
        min_correlation=0.01,
        max_numeric_features=None,
    )
    X_test, _, _, _, _ = prepare_features(test_df, use_correlation_filter=False)
    X_test = X_test[X_train.columns]

    model_path = ML / "models" / "catboost_baseline.model"
    model = CatBoostRegressor()
    model.load_model(str(model_path))
    names_file = list(model.feature_names_)
    X_train = _align_df_to_model(X_train, model)
    X_test = _align_df_to_model(X_test, model)
    if list(X_train.columns) != names_file:
        print(
            "WARNING: после align колонки всё ещё не совпадают с моделью.",
            file=sys.stderr,
        )

    rng = np.random.default_rng(SEED)
    n = min(N_SAMPLES, len(X_test))
    idx = rng.choice(len(X_test), size=n, replace=False)
    X_sub = X_test.iloc[idx].reset_index(drop=True)

    pool = Pool(X_sub, cat_features=list(model.get_cat_feature_indices()))
    shap_full = np.asarray(model.get_feature_importance(pool, type="ShapValues"))
    phi = shap_full[:, :-1]
    mean_abs = np.mean(np.abs(phi), axis=0)
    imp = (
        pd.DataFrame({"feature": names_file, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )

    out_dir = Path(__file__).resolve().parent / "shap_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "offers_created_at_lte": OFFERS_CREATED_AT_LTE,
        "rows_after_sql": rows_sql,
        "rows_after_etl": len(df),
        "train_n": len(train_df),
        "test_n": len(test_df),
        "shap_sample_n": len(X_sub),
    }
    (out_dir / "shap_cutoff_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    imp.to_csv(out_dir / "shap_mean_abs_importance_cutoff.csv", index=False)

    print("\n--- meta ---")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"\n--- top {TOP_PRINT} mean |SHAP| ---")
    with pd.option_context("display.max_rows", None, "display.width", 120):
        print(imp.head(TOP_PRINT).to_string(index=False))
    print(f"\nCSV: {out_dir / 'shap_mean_abs_importance_cutoff.csv'}")


if __name__ == "__main__":
    main()
