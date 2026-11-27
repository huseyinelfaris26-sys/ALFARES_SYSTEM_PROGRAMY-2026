from fastapi import APIRouter

router = APIRouter()

@router.get("/satellite")

def satellite():

    return {
        "message":
        "satellite running"
    }
