import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from .apps.smart_hub.models import TASKS_DB, State
from .apps.smart_hub.routers.appliances import router as appliances_router
from .apps.smart_hub.routers.batteries import router as batteries_router
from .apps.smart_hub.routers.data import router as data_router
from .apps.smart_hub.routers.dr import router as dr_router
from .apps.smart_hub.routers.programs import router as programs_router
from .apps.smart_hub.routers.tasks import router as tasks_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # e.g. http://localhost:3001
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(
        "mongodb://root:password@" + os.environ.get("MONGO_HOST") + ":27017/?retryWrites=true&w=majority&uuidRepresentation=standard")
    app.mongodb = app.mongodb_client["hub"]
    print(app.mongodb)


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


app.include_router(appliances_router, tags=[
                   "appliances"], prefix="/appliances")
app.include_router(data_router, tags=["data"], prefix="/data")
app.include_router(dr_router, tags=["DR"], prefix="/dr")
app.include_router(batteries_router, tags=["batteries"], prefix="/batteries")
app.include_router(programs_router, tags=["programs"], prefix="/programs")
app.include_router(tasks_router, tags=["tasks"], prefix="/tasks")
