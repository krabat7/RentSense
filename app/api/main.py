import re
import uvicorn
import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException
from app.parser.main import apartPage
from .models import Params, PredictReq, PredictResponse
from .preprocess import preparams
from .theards import to_thread
from .model_loader import load_quantile_models, load_baseline_model
from .preprocess_inference import prepare_features_for_prediction, fill_missing_for_inference
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RentSense API",
    description="API для предсказания стоимости аренды недвижимости",
    version="2.0"
)
router = APIRouter()

# Загрузка моделей при старте
try:
    quantile_models = load_quantile_models()
    baseline_model = load_baseline_model('catboost')
    logger.info("Модели загружены успешно")
except Exception as e:
    logger.error(f"Ошибка при загрузке моделей: {e}")
    quantile_models = {}
    baseline_model = None


@router.get('/getparams', response_model=Params)
async def getparams(url: str):
    """Извлечение параметров объявления из URL Циана."""
    match = re.search(r'flat/(\d{4,})', url)
    if not match or not (id := match.group(1)):
        raise HTTPException(status_code=400, detail='Неверный формат объявления')
    data = await to_thread(apartPage, [id], dbinsert=False)
    if not data:
        raise HTTPException(status_code=400, detail='Неверный формат объявления')
    if not isinstance(data, dict):
        return
    data = Params(**data)
    response = await to_thread(preparams, data)
    return response


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
        # Преобразуем данные в словарь
        data_dict = request.data.dict()
        
        # Подготовка признаков
        df = prepare_features_for_prediction(data_dict)
        df = fill_missing_for_inference(df)
        
        # Если есть квантильные модели, используем их
        if quantile_models and 'P50' in quantile_models:
            predictions = {}
            for quantile in ['P10', 'P50', 'P90']:
                if quantile in quantile_models:
                    pred = quantile_models[quantile].predict(df)
                    predictions[quantile.lower()] = float(pred[0])
            
            return PredictResponse(
                price=predictions.get('p50', 0.0),
                price_p10=predictions.get('p10'),
                price_p90=predictions.get('p90')
            )
        
        # Иначе используем baseline модель
        elif baseline_model:
            pred = baseline_model.predict(df)
            return PredictResponse(price=float(pred[0]))
        
        else:
            raise HTTPException(status_code=500, detail='Модели не загружены')
    
    except Exception as e:
        logger.error(f"Ошибка при предсказании: {e}")
        raise HTTPException(status_code=500, detail=f'Ошибка при предсказании: {str(e)}')


from .search import router as search_router

app.include_router(router, prefix='/api')
app.include_router(search_router, prefix='/api')


async def fastapi():
    config = uvicorn.Config(app, host='0.0.0.0', log_config=None)
    await uvicorn.Server(config).serve()

@app.get('/health')
async def health():
    return {'status': 'ok'}
