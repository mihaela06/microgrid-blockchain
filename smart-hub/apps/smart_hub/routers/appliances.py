from fastapi import APIRouter, Body, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from ..models import (APPLIANCES_DB, PROGRAMS_DB, TASKS_DB, Appliance, Program,
                      State, Task, UpdateAppliance, UpdateProgram)

router = APIRouter()


@router.post("/", response_description="Add new appliance")
async def create_appliance(request: Request, appliance: UpdateAppliance = Body(...)):
    name = appliance.name
    model = appliance.model
    category = appliance.category
    appliance_found = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance_found is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Appliance named {name} already exists")

    appliance = Appliance(name=name, programs=[], tasks=[],
                          currentTask=None, model=model, category=category)

    appliance = jsonable_encoder(appliance)
    new_appliance = await request.app.mongodb[APPLIANCES_DB].insert_one(appliance)
    created_appliance = await request.app.mongodb[APPLIANCES_DB].find_one(
        {"_id": new_appliance.inserted_id}
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_appliance)


@router.get("/", response_description="List all appliances")
async def list_appliances(request: Request):
    appliances = []
    for doc in await request.app.mongodb[APPLIANCES_DB].find().to_list(length=100):
        appliances.append(doc)
    return appliances


@router.get("/{name}", response_description="Get a single appliance")
async def show_appliance(name: str, request: Request):
    if (appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})) is not None:
        return appliance

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Appliance {name} not found")


@router.put("/{name}", response_description="Update an appliance")
async def update_appliance(name: str, request: Request, appliance: UpdateAppliance = Body(...)):
    search_name = appliance.name
    appliance_found = await request.app.mongodb[APPLIANCES_DB].find_one({"name": search_name})

    if appliance_found is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Appliance named {search_name} already exists")

    appliance = {k: v for k, v in appliance.dict().items() if v is not None}

    if len(appliance) >= 1:
        update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
            {"name": name}, {"$set": appliance}
        )

        if update_result.modified_count == 1:
            if (
                updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": appliance["name"]})
            ) is not None:
                return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": appliance["name"]})
    ) is not None:
        return existing_appliance

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Appliance {name} not found")


@router.delete("/{name}", response_description="Delete appliance")
async def delete_appliance(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    for programName in appliance["programs"]:
        delete_result = await request.app.mongodb[PROGRAMS_DB].delete_one({"name": programName})

    delete_result = await request.app.mongodb[APPLIANCES_DB].delete_one({"name": name})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Appliance {name} not found")


@router.post("/{name}/programs", response_description="Add new program to appliance")
async def create_program(name: str, request: Request, program: Program = Body(...)):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program_found = await request.app.mongodb[PROGRAMS_DB].find_one({"name": program.name, "applianceId": appliance["_id"]})

    if program_found is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Program named {program.name} already exists for appliance {name}")

    program.applianceId = appliance["_id"]

    program = jsonable_encoder(program)
    new_program = await request.app.mongodb[PROGRAMS_DB].insert_one(program)

    appliance["programs"].append(program["name"])
    update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
        {"name": name}, {"$set": appliance}
    )

    if update_result.modified_count == 1:
        if (
            updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
        ) is not None:
            return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    ) is not None:
        return existing_appliance


@router.get("/{name}/programs", response_description="List all appliance programs")
async def list_programs(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    programs = []
    for doc in await request.app.mongodb[PROGRAMS_DB].find().to_list(length=100):
        if doc["applianceId"] == appliance["_id"]:
            programs.append(doc)

    return programs


@router.get("/{name}/programs/{program_name}", response_description="Get a single program")
async def show_program(name: str, program_name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program = await request.app.mongodb[PROGRAMS_DB].find_one({"name": program_name, "applianceId": appliance["_id"]})

    if program is not None:
        return program

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Program {program_name} not found for appliance {name}")


@router.put("/{name}/programs/{program_name}", response_description="Update a program")
async def update_program(name: str, program_name: str, request: Request, program: UpdateProgram = Body(...)):
    new_name = program.name
    appliance_found = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance_found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program_found = await request.app.mongodb[PROGRAMS_DB].find_one({"name": program_name, "applianceId": appliance_found["_id"]})

    if program_found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {program_name} not found for appliance {name}")

    program_existing = await request.app.mongodb[PROGRAMS_DB].find_one({"name": program.name, "applianceId": appliance_found["_id"]})

    if program_existing is not None and program_found["_id"] != program_existing["_id"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Program named {program.name} already exists for appliance {name}")

    program = {k: v for k, v in program.dict().items() if v is not None}

    if len(program) >= 1:
        update_result = await request.app.mongodb[PROGRAMS_DB].update_one(
            {"name": program_name}, {"$set": program}
        )

        if update_result.modified_count == 1:
            if (
                updated_program := await request.app.mongodb[PROGRAMS_DB].find_one({"name": new_name})
            ) is not None:
                return updated_program

    if (
        existing_program := await request.app.mongodb[APPLIANCES_DB].find_one({"_id": new_name})
    ) is not None:
        return existing_program


@router.delete("/{name}/programs/{program_name}", response_description="Delete a program")
async def delete_program(name: str, program_name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program_found = await request.app.mongodb[PROGRAMS_DB].find_one({"name": program_name, "applianceId": appliance["_id"]})

    if program_found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {program_name} not found for appliance {name}")

    delete_result = await request.app.mongodb[PROGRAMS_DB].delete_one({"name": program_name})

    if delete_result.deleted_count != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {program_name} not found for appliance {name}")

    appliance["programs"].remove(program_name)
    update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
        {"name": name}, {"$set": appliance}
    )

    if update_result.modified_count == 1:
        if (
            updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
        ) is not None:
            return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    ) is not None:
        return existing_appliance


@router.post("/{name}/tasks/start", response_description="Start new task")
async def start_task(name: str, request: Request, task: Task = Body(...)):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program = await request.app.mongodb[PROGRAMS_DB].find_one({"name": task.programName, "applianceId": appliance["_id"]})

    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {task.programName} does not exist for appliance {name}")

    task.programName = program["name"]
    task.remainingTime = program["duration"]
    task.currentPower = program["averagePower"]

    if appliance["currentTask"] is not None:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} has another task started")

    task.state = State.InProgress

    task_json = jsonable_encoder(task)

    new_task = await request.app.mongodb[TASKS_DB].insert_one(task_json)

    appliance["tasks"].append(new_task.inserted_id)
    appliance["currentTask"] = new_task.inserted_id

    update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
        {"name": name}, {"$set": appliance}
    )

    if update_result.modified_count == 1:
        if (
            updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
        ) is not None:
            return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    ) is not None:
        return existing_appliance


@router.post("/{name}/tasks/program", response_description="Program new task")
async def start_task(name: str, request: Request, task: Task = Body(...)):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    program = await request.app.mongodb[PROGRAMS_DB].find_one({"name": task.programName, "applianceId": appliance["_id"]})

    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {task.programName} does not exist for appliance {name}")

    if program["programmable"] is not True:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Program {task.programName} is not programmable")

    task.programName = program["name"]
    task.remainingTime = program["duration"]
    task.currentPower = program["averagePower"]

    task.state = State.Pending

    task_json = jsonable_encoder(task)

    new_task = await request.app.mongodb[TASKS_DB].insert_one(task_json)

    appliance["tasks"].append(new_task.inserted_id)

    update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
        {"name": name}, {"$set": appliance}
    )

    if update_result.modified_count == 1:
        if (
            updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
        ) is not None:
            return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    ) is not None:
        return existing_appliance


@router.post("/{name}/tasks/pause", response_description="Pause running task")
async def pause_task(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    if appliance["currentTask"] is None:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} has no task started")

    currentTask = await request.app.mongodb[TASKS_DB].find_one({"_id": appliance["currentTask"]})

    if currentTask["state"] != State.InProgress.value:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} current task is already paused")

    currentProgramName = currentTask["programName"]

    program = await request.app.mongodb[PROGRAMS_DB].find_one({"name": currentProgramName, "applianceId": appliance["_id"]})

    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Program {currentProgramName} does not exist for appliance {name}")

    if program["interruptible"] is not True:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Program {currentProgramName} is not interruptible")

    currentTask["state"] = State.Paused.value

    update_result = await request.app.mongodb[TASKS_DB].update_one(
        {"_id": currentTask["_id"]}, {"$set": currentTask}
    )

    if update_result.modified_count == 1:
        if (
            updated_task := await request.app.mongodb[TASKS_DB].find_one({"_id": currentTask["_id"]})
        ) is not None:
            return updated_task

    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail=f"Appliance {name} has no task started")


@router.post("/{name}/tasks/resume", response_description="Resume running task")
async def resume_task(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    if appliance["currentTask"] is None:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} has no task started")

    currentTask = await request.app.mongodb[TASKS_DB].find_one({"_id": appliance["currentTask"]})

    if currentTask["state"] != State.Paused.value:
        print(currentTask["state"])
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} current task is already in progress")

    currentTask["state"] = State.InProgress.value

    update_result = await request.app.mongodb[TASKS_DB].update_one(
        {"_id": currentTask["_id"]}, {"$set": currentTask}
    )

    if update_result.modified_count == 1:
        if (
            updated_task := await request.app.mongodb[TASKS_DB].find_one({"_id": currentTask["_id"]})
        ) is not None:
            return updated_task

    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail=f"Appliance {name} has no task started")


@router.post("/{name}/tasks/cancel", response_description="Cancel running task")
async def cancel_task(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    if appliance["currentTask"] is None:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"Appliance {name} has no task started")

    currentTask = await request.app.mongodb[TASKS_DB].find_one({"_id": appliance["currentTask"]})

    currentTask["state"] = State.Canceled.value

    update_result = await request.app.mongodb[TASKS_DB].update_one(
        {"_id": currentTask["_id"]}, {"$set": currentTask}
    )

    appliance["currentTask"] = None

    update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
        {"name": name}, {"$set": appliance}
    )

    if update_result.modified_count == 1:
        if (
            updated_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
        ) is not None:
            return updated_appliance

    if (
        existing_appliance := await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})
    ) is not None:
        return existing_appliance

    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail=f"Appliance {name} has no task started")


@router.delete("/{name}/tasks/{id}", response_description="Cancel task")
async def cancel_task(name: str, id: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance["currentTask"] == id:
        appliance["currentTask"] = None
        update_result = await request.app.mongodb[APPLIANCES_DB].update_one(
            {"name": name}, {"$set": appliance}
        )

    task = await request.app.mongodb[TASKS_DB].find_one({"_id": id})

    task["state"] = State.Canceled.value

    update_result = await request.app.mongodb[TASKS_DB].update_one(
        {"_id": task["_id"]}, {"$set": task}
    )

    if update_result.modified_count == 1:
        if (
            updated_task := await request.app.mongodb[TASKS_DB].find_one({"_id": task["_id"]})
        ) is not None:
            return updated_task


@router.get("/{name}/tasks", response_description="List all appliance tasks")
async def get_tasks(name: str, request: Request):
    appliance = await request.app.mongodb[APPLIANCES_DB].find_one({"name": name})

    if appliance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Appliance {name} not found")

    tasks = []

    for task in appliance["tasks"]:
        doc = await request.app.mongodb[TASKS_DB].find_one({"_id": task})
        tasks.append(doc)

    return tasks
