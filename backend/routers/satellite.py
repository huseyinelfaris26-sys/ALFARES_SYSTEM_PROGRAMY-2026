from fastapi import APIRouter

router = APIRouter()


@router.get("/satellite/ndvi")
def ndvi():

    return {

        "formula":

        "(NIR-RED)/(NIR+RED)",

        "status":

        "ready"
    }
