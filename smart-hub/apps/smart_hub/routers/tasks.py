from fastapi import APIRouter, Request

from ..models import TASKS_DB

router = APIRouter()


@router.get("/", response_description="List all tasks")
async def list_tasks(request: Request):
    tasks = []
    for doc in await request.app.mongodb[TASKS_DB].find().to_list(length=100):
        tasks.append(doc)
    return tasks
