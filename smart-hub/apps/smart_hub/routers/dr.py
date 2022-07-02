from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
from fastapi.encoders import jsonable_encoder

from ..models import (DR_DB, DRSignal)

router = APIRouter()


@router.put("/", response_description="Update DR signal")
async def new_dr(request: Request):
    body = await request.json()
    try:
        raw_signal = body["signal"]
        signal = []
        for v in raw_signal:
            signal.append(float(v))
        print("new signal ", signal)
        db_signal = await request.app.mongodb[DR_DB].find().to_list(length=10)
        dr = DRSignal(values=signal)
        print(dr)
        dr = jsonable_encoder(dr)
        print(dr)
        if len(db_signal) == 0:
            _ = await request.app.mongodb[DR_DB].insert_one(dr)
        else:
            dr = db_signal[0]
            _ = await request.app.mongodb[DR_DB].update_one(
                {"counter": dr["counter"]}, {
                    "$set": {"values": signal, "counter": 0}}
            )
        return Response(status_code=status.HTTP_202_ACCEPTED)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No signal included in the request body.")


@router.get("/", response_description="Get DR signal")
async def get_dr(request: Request):
    db_signal = await request.app.mongodb[DR_DB].find().to_list(length=10)
    if len(db_signal) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No signal registered in database")
    else:
        return db_signal[0]["values"][db_signal[0]["counter"]:]
