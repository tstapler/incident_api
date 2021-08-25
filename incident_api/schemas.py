import abc
from datetime import datetime
from enum import Enum
from typing import Union, List

from pydantic import BaseModel, validator


class IncidentCategory(str, Enum):
    denial = "denial"
    intrusion = "intrusion"
    executable = "executable"
    misuse = "misuse"
    unauthorized = "unauthorized"
    probing = "probing"
    other = "other"


class IncidentSeverity(str, Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'


class UserIncident(BaseModel):
    type: IncidentCategory
    priority: IncidentSeverity
    timestamp: datetime
    employee_id: str


class IncidentSeverityAggregate(BaseModel):
    count: int = 0
    incidents: List[UserIncident] = []


class EmployeeRisk(BaseModel):
    low: IncidentSeverityAggregate = IncidentSeverityAggregate()
    medium: IncidentSeverityAggregate = IncidentSeverityAggregate()
    high: IncidentSeverityAggregate = IncidentSeverityAggregate()
    critical: IncidentSeverityAggregate = IncidentSeverityAggregate()

    def add_incident(self, incident: UserIncident):
        level: IncidentSeverityAggregate = self.__getattribute__(incident.priority)
        level.incidents.append(incident)
        level.count += 1


class IncidentType(BaseModel, abc.ABC):
    priority: IncidentSeverity
    timestamp: datetime

    @validator('timestamp', pre=True)
    def validate_timestamp(cls, v):
        return datetime.fromtimestamp(v)

    @abc.abstractmethod
    def to_user_incident(self, lookup: dict) -> UserIncident:
        pass


class Denial(IncidentType):
    reported_by: int
    source_ip: str

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=self.reported_by, type=IncidentCategory.denial
        )


class Executable(IncidentType):
    machine_ip: str

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=lookup[self.machine_ip], type=IncidentCategory.executable
        )


class Intrusion(IncidentType):
    internal_ip: str
    source_ip: str

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=lookup[self.internal_ip], type=IncidentCategory.intrusion
        )



class Misuse(IncidentType):
    employee_id: str

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=self.employee_id, type=IncidentCategory.misuse
        )


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


class Other(IncidentType):
    identifier: Union[int, str]

    def to_user_incident(self, lookup: dict):
        employee_id = self.identifier
        if not is_integer(employee_id):
            employee_id = lookup[employee_id]
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=employee_id, type=IncidentCategory.other
        )


class Probing(IncidentType):
    ip: str

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=lookup[self.ip], type=IncidentCategory.probing
        )


class Unauthorized(IncidentType):
    employee_id: int

    def to_user_incident(self, lookup: dict):
        return UserIncident(
            priority=self.priority, timestamp=self.timestamp,
            employee_id=self.employee_id, type=IncidentCategory.unauthorized
        )
