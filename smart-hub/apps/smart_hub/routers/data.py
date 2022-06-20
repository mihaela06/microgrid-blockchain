from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder

from ..models import Appliance, UpdateAppliance, Program, UpdateProgram, Task, APPLIANCES_DB, TASKS_DB, PROGRAMS_DB, State

router = APIRouter()


@router.get("/values", response_description="Get all values")
async def get_data(request: Request):
    tasks_values = {}
    for task in await request.app.mongodb[TASKS_DB].find().to_list(length=100):
        tasks_values[task["applianceId"]] = task["currentPower"]
    return tasks_values
