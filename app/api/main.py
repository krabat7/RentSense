import re
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException
from app.parser.main import apartPage
from .models import Params, PredictReq, PredictResponse
from .preprocess import preparams
from .theards import to_thread

app = FastAPI()
router = APIRouter()


@router.get('/getparams', response_model=Params)
async def getparams(url: str):
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
    return {'price': 0.0}


app.include_router(router, prefix='/api')


async def fastapi():
    config = uvicorn.Config(app, host='0.0.0.0', log_config=None)
    await uvicorn.Server(config).serve()

@app.get('/health')
async def health():
    return {'status': 'ok'}
