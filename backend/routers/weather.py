from fastapi import APIRouter

router = APIRouter()

@router.get("/weather")

def weather():

    return {
        "message":
        "weather api running"
    }
