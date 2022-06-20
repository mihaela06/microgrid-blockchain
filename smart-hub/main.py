import uvicorn
from fastapi import FastAPI
# from config import settings
from fastapi_utils.tasks import repeat_every
from motor.motor_asyncio import AsyncIOMotorClient

from .apps.smart_hub.models import TASKS_DB, State
from .apps.smart_hub.routers.appliances import router as appliances_router
from .apps.smart_hub.routers.batteries import router as batteries_router
from .apps.smart_hub.routers.data import router as data_router
from .apps.smart_hub.routers.dr import router as dr_router

app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    print("what")
    # app.mongodb_client = AsyncIOMotorClient(settings.DB_URL)
    # app.mongodb_client = AsyncIOMotorClient(
    #     "mongodb+srv://admin:lXBtOnV2SELj3qkR@cluster0.ke5tapi.mongodb.net/bd?retryWrites=true&w=majority&uuidRepresentation=standard")
    app.mongodb_client = AsyncIOMotorClient(
        "mongodb://root:password@mongo:27017/?retryWrites=true&w=majority&uuidRepresentation=standard")
    # app.mongodb = app.mongodb_client[settings.DB_NAME]
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


# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         host="localhost",
#         reload=True,
#         port=8116,
#     )
