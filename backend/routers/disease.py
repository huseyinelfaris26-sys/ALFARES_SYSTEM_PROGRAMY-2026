from fastapi import APIRouter

router = APIRouter()


@router.get("/disease")
def disease():

    return {

        "status":
        "ready"
    }
