from fastapi import APIRouter, Request

from ..models import (ENERGY_DATA_DB)

router = APIRouter()

# TODO dynamic length


@router.get("/values", response_description="Get all values")
async def get_data(request: Request):
    values = []
    for d in await request.app.mongodb[ENERGY_DATA_DB].find().limit(8640).sort([('$natural', -1)]).to_list(length=8640):
        values.append(d)
    return values
