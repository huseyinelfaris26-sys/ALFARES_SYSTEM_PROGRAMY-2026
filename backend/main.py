from fastapi import FastAPI

from routers.weather import router as weather_router
from routers.disease import router as disease_router
from routers.satellite import router as satellite_router
from routers.eppo import router as eppo_router

app = FastAPI(
    title="ALFARES AI API",
    version="2026"
)

app.include_router(weather_router)
app.include_router(disease_router)
app.include_router(satellite_router)
app.include_router(eppo_router)

@app.get("/")
def root():

    return {

        "project":
        "ALFARES_SYSTEM_PROGRAMY-2026",

        "status":
        "online"
    }
