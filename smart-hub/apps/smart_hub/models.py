from enum import Enum
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Float
from beanie import Document, TimeSeriesConfig, Granularity

from pydantic import BaseModel, Field

APPLIANCES_DB = "appliances"
BATTERIES_DB = "batteries"
PROGRAMS_DB = "programs"
TASKS_DB = "tasks"
DR_DB = "dr"
ENERGY_DATA_DB = "energydata"

State = Enum("State", "Pending InProgress Paused Canceled Finished")


class Appliance(BaseModel):
    class DocumentMeta:
        collection_name = APPLIANCES_DB

    id: str = Field(default_factory=uuid4, alias="_id")
    name: str
    model: str
    category: str
    programs: List[str]
    tasks: List[str]
    currentTask: Optional[str]


class Battery(BaseModel):
    class DocumentMeta:
        collection_name = BATTERIES_DB

    id: str = Field(default_factory=uuid4, alias="_id")
    name: str
    model: str
    currentCapacity: float = Field(default=0)   # in Ws
    maxCapacity: float # in Ws
    maxDischargeRate: float
    maxChargeRate: float
    currentRate: Optional[float]
    connected: bool = Field(default=True)


class UpdateBattery(BaseModel):
    name: str
    model: str
    maxCapacity: float
    maxDischargeRate: float
    maxChargeRate: float


class UpdateAppliance(BaseModel):
    name: str
    model: str
    category: str


class Program(BaseModel):
    class DocumentMeta:
        collection_name = PROGRAMS_DB

    programId: str = Field(default_factory=uuid4, alias="_id")
    name: str
    averagePower: float
    duration: int
    priority: int
    downgradeable: bool
    programmable: bool
    interruptible: bool
    applianceId: Optional[str]
    generatesPower: bool = Field(default=False)


class UpdateProgram(BaseModel):
    name: str
    averagePower: float
    duration: int
    priority: int
    downgradeable: bool
    interruptible: bool
    programmable: bool


class Task(BaseModel):
    class DocumentMeta:
        collection_name = TASKS_DB

    taskId: str = Field(default_factory=uuid4, alias="_id")
    programName: str
    currentPower: Optional[float]
    remainingTime: Optional[int]
    state: Optional[int]


class DRSignal(BaseModel):
    class DocumentMeta:
        collection_name = DR_DB

    counter: int = Field(default=0)
    values: List[float]


class EnergyData(Document):
    ts: datetime = Field(default_factory=datetime.now)
    meta: str
    background: float
    appliances: dict
    generators: dict

    class Settings:
        timeseries = TimeSeriesConfig(
            time_field="ts",
            meta_field="meta",
            granularity=Granularity.seconds
        )


Appliance.update_forward_refs()
