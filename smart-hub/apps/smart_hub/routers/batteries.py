from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder

from ..models import BATTERIES_DB, Battery, UpdateBattery, Program, UpdateProgram, Task, BATTERIES_DB, TASKS_DB, PROGRAMS_DB, State

router = APIRouter()


@router.post("/", response_description="Add new battery")
async def create_battery(request: Request, battery: UpdateBattery = Body(...)):
    name = battery.name

    battery_found = await request.app.mongodb[BATTERIES_DB].find_one({"name": name})

    if battery_found is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Battery named {name} already exists")

    battery = Battery(name=name,
                      model=battery.model,
                      maxCapacity=battery.maxCapacity,
                      maxDischargeRate=battery.maxDischargeRate,
                      maxChargeRate=battery.maxChargeRate,
                      currentRate=battery.maxChargeRate
                      )

    battery = jsonable_encoder(battery)
    new_battery = await request.app.mongodb[BATTERIES_DB].insert_one(battery)

    created_battery = await request.app.mongodb[BATTERIES_DB].find_one(
        {"_id": new_battery.inserted_id}
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_battery)


@router.get("/", response_description="List all batteries")
async def list_batteries(request: Request):
    batteries = []
    for doc in await request.app.mongodb[BATTERIES_DB].find().to_list(length=100):
        batteries.append(doc)
    return batteries


@router.get("/{name}", response_description="Get a single battery")
async def show_battery(name: str, request: Request):
    if (battery := await request.app.mongodb[BATTERIES_DB].find_one({"name": name})) is not None:
        return battery

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Battery {name} not found")


@router.put("/{name}", response_description="Update an battery")
async def update_battery(name: str, request: Request, battery: UpdateBattery = Body(...)):
    search_name = battery.name
    battery_found = await request.app.mongodb[BATTERIES_DB].find_one({"name": search_name})

    if battery_found is not None and search_name != name:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Battery named {search_name} already exists")

    battery = {k: v for k, v in battery.dict().items() if v is not None}

    if len(battery) >= 1:
        update_result = await request.app.mongodb[BATTERIES_DB].update_one(
            {"name": name}, {"$set": battery}
        )

        if update_result.modified_count == 1:
            if (
                updated_battery := await request.app.mongodb[BATTERIES_DB].find_one({"name": battery["name"]})
            ) is not None:
                return updated_battery

    if (
        existing_battery := await request.app.mongodb[BATTERIES_DB].find_one({"name": battery["name"]})
    ) is not None:
        return existing_battery

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Battery {name} not found")


@router.delete("/{name}", response_description="Delete battery")
async def delete_battery(name: str, request: Request):
    battery = await request.app.mongodb[BATTERIES_DB].find_one({"name": name})

    if battery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Battery {name} not found")

    delete_result = await request.app.mongodb[BATTERIES_DB].delete_one({"name": name})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Battery {name} not found")


@router.post("/{name}/connect", response_description="Connect battery")
async def connect_batteryk(name: str, request: Request):
    battery = await request.app.mongodb[BATTERIES_DB].find_one({"name": name})

    if battery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Battery {name} not found")

    if battery["connected"] is True:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Battery {name} already connected")

    update_result = await request.app.mongodb[BATTERIES_DB].update_one(
        {"name": name}, {"$set": {"connected": True}}
    )

    if update_result.modified_count == 1:
        if (
            updated_battery := await request.app.mongodb[BATTERIES_DB].find_one({"name": battery["name"]})
        ) is not None:
            return updated_battery


@router.post("/{name}/disconnect", response_description="Disconnect battery")
async def connect_batteryk(name: str, request: Request):
    battery = await request.app.mongodb[BATTERIES_DB].find_one({"name": name})

    if battery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Battery {name} not found")

    if battery["connected"] is False:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Battery {name} already disconnected")

    update_result = await request.app.mongodb[BATTERIES_DB].update_one(
        {"name": name}, {"$set": {"connected": False}}
    )

    if update_result.modified_count == 1:
        if (
            updated_battery := await request.app.mongodb[BATTERIES_DB].find_one({"name": battery["name"]})
        ) is not None:
            return updated_battery
