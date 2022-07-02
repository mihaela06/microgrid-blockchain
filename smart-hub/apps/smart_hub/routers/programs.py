from fastapi import APIRouter, Request

from ..models import PROGRAMS_DB

router = APIRouter()


@router.get("/", response_description="List all programs")
async def list_programs(request: Request):
    programs = []
    for doc in await request.app.mongodb[PROGRAMS_DB].find().to_list(length=100):
        programs.append(doc)
    return programs
