import asyncio
import logging
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

import pandas as pd
import numpy as np
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request

from .model_loader import load_baseline_model, load_quantile_models
from .models import Params, PredictReq, PredictResponse
from .preprocess import preparams
from .preprocess_inference import fill_missing_for_inference, prepare_features_for_prediction
from .theards import to_thread

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_apart_page_in_process(flat_id: str, dbinsert: bool = False):
    """
    Вызов парсера в отдельном процессе.
    Playwright sync API несовместим с asyncio.to_thread (greenlet.error: cannot switch to a different thread).
    """
    from app.parser.main import apartPage
    return apartPage([flat_id], dbinsert=dbinsert)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = multiprocessing.get_context("spawn")
    app.state.process_pool = ProcessPoolExecutor(max_workers=2, mp_context=ctx)
    yield
    app.state.process_pool.shutdown(wait=True)


app = FastAPI(
    title="RentSense API",
    description="API для предсказания стоимости аренды недвижимости",
    version="2.0",
    lifespan=lifespan,
)

# Загрузка моделей при старте
try:
    quantile_models = load_quantile_models()
    baseline_model = load_baseline_model('catboost')
    logger.info("Модели загружены успешно")
except Exception as e:
    logger.error(f"Ошибка при загрузке моделей: {e}")
    quantile_models = {}
    baseline_model = None


def _extract_flat_id(url: str) -> str | None:
    """Извлекает id объявления из URL (поддерживает длинные ссылки с query-параметрами)."""
    match = re.search(r'flat/(\d{4,})', url)
    return match.group(1) if match else None


@router.get('/getparams')
async def getparams(request: Request, url: str):
    """Извлечение параметров объявления из URL Циана."""
    try:
        flat_id = _extract_flat_id(url)
        if not flat_id:
            raise HTTPException(status_code=400, detail='Неверный формат объявления')
        loop = asyncio.get_event_loop()
        pool = request.app.state.process_pool
        data = await loop.run_in_executor(
            pool, _run_apart_page_in_process, flat_id, False
        )
        if data is None or not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail='Объявление недоступно или снято с публикации. Проверьте ссылку.',
            )
        data = Params(**data)
        response = await to_thread(preparams, data)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("getparams failed: %s", e)
        raise HTTPException(
            status_code=400,
            detail='Не удалось загрузить объявление. Проверьте ссылку и доступность.',
        )


def _ensure_cat_string(ser: pd.Series) -> np.ndarray:
    """Категориальные признаки CatBoost: только str или int. Float/NaN → строка 'unknown'."""
    def to_cat(x):
        if pd.isna(x) or isinstance(x, (float, np.floating)):
            return "unknown"
        if isinstance(x, (str, int)):
            return x
        return str(x)
    return ser.apply(to_cat).values


def _align_df_to_model(df: pd.DataFrame, model) -> pd.DataFrame:
    """Приводит DataFrame к признакам модели: порядок колонок, недостающие — 0.
    Числовые: строки/unknown → float 0. Категориальные: float/NaN → строка 'unknown'."""
    try:
        names = getattr(model, 'feature_names_', None) or getattr(model, 'feature_names', lambda: None)()
        if not names:
            return df
        cat_indices = getattr(model, 'get_cat_feature_indices', lambda: [])()
        cat_indices = cat_indices if isinstance(cat_indices, (list, tuple)) else []
        cat_names = {names[i] for i in cat_indices if 0 <= i < len(names)}
    except Exception:
        cat_names = set()
        try:
            names = getattr(model, 'feature_names_', None)
        except Exception:
            return df
        if not names:
            return df
    out = pd.DataFrame(index=df.index)
    for name in names:
        if name in df.columns:
            ser = df[name]
            if name in cat_names:
                out[name] = _ensure_cat_string(ser)
            else:
                out[name] = pd.to_numeric(ser, errors='coerce').fillna(0).values
        else:
            out[name] = "unknown" if name in cat_names else 0
    return out


@router.post('/predict', response_model=PredictResponse)
async def prediction(request: PredictReq):
    """
    Предсказание цены аренды квартиры.
    
    Использует квантильные модели для получения вилки цен (P10, P50, P90).
    Если квантильные модели недоступны, использует baseline модель.
    
    Returns:
        PredictResponse с полями:
        - price: предсказанная цена (P50)
        - price_p10: нижняя граница вилки (P10)
        - price_p90: верхняя граница вилки (P90)
    """
    try:
        # Преобразуем данные в словарь (Pydantic v2 model_dump / v1 dict)
        if hasattr(request.data, 'model_dump'):
            data_dict = request.data.model_dump()
        else:
            data_dict = request.data.dict()

        # Подготовка признаков
        df = prepare_features_for_prediction(data_dict)
        df = fill_missing_for_inference(df)

        def _clip_price(p: float) -> float:
            """Цена не может быть отрицательной."""
            return max(0.0, float(p)) if p is not None else 0.0

        # Если есть квантильные модели, используем их
        if quantile_models and 'P50' in quantile_models:
            predictions = {}
            for quantile in ['P10', 'P50', 'P90']:
                if quantile in quantile_models:
                    m = quantile_models[quantile]
                    pred_df = _align_df_to_model(df, m)
                    pred = m.predict(pred_df)
                    predictions[quantile.lower()] = _clip_price(pred[0])
            return PredictResponse(
                price=predictions.get('p50', 0.0),
                price_p10=predictions.get('p10'),
                price_p90=predictions.get('p90')
            )

        # Иначе используем baseline модель
        if baseline_model:
            pred_df = _align_df_to_model(df, baseline_model)
            pred = baseline_model.predict(pred_df)
            return PredictResponse(price=_clip_price(pred[0]))

        raise HTTPException(status_code=500, detail='Модели не загружены')

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при предсказании")
        raise HTTPException(status_code=500, detail='Ошибка при предсказании')


from .search import router as search_router

app.include_router(router, prefix='/api')
app.include_router(search_router, prefix='/api')


async def fastapi():
    config = uvicorn.Config(app, host='0.0.0.0', log_config=None)
    await uvicorn.Server(config).serve()

@app.get('/health')
async def health():
    return {'status': 'ok'}
