from fastapi import APIRouter
router = APIRouter()

@router.post("/")
@router.get("/")
def root():
    return {
        "status": "ok",
        "message": "Statfinity AI backend is running",
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
    }