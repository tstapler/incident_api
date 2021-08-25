from functools import lru_cache
from timeit import default_timer

import uvicorn
from aiocache import Cache
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse
from pydantic import BaseSettings

from incident_api.external import non_blocking_fetch_employee_incidents
from incident_api.schemas import EmployeeRisk


class Settings(BaseSettings):
    elevate_api_user: str
    elevate_api_password: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
api_creds = (settings.elevate_api_user, settings.elevate_api_password)
app = FastAPI()
cache = Cache(Cache.MEMORY)


@app.get("/incidents", response_model=EmployeeRisk, response_class=ORJSONResponse)
async def get_incidents():
    start = default_timer()
    cached_incident_data = await cache.get("incidents")
    if cached_incident_data:
        return cached_incident_data
    end_cache = default_timer()
    print(f"Fetching from cache took {end_cache - start}")
    return await non_blocking_fetch_employee_incidents(api_creds)


async def cache_user_incidents():
    print("Caching incidents")
    incident_data = await non_blocking_fetch_employee_incidents(api_creds)
    # Caching the serialized response instead of just the data takes our responses
    # from 250ms down to 5ms or less
    await cache.set("incidents", ORJSONResponse(jsonable_encoder(incident_data)))
    print()


@app.on_event("startup")
async def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.start()
    scheduler.add_job(cache_user_incidents, 'interval', seconds=8,
                      # Using max_instances=1 guarantees that only one job
                      # runs at the same time (in this event loop).
                      max_instances=1)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
