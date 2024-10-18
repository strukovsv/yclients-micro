from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

api_router = APIRouter(prefix="/api/v1")
user_router = APIRouter(prefix="/ui")


@api_router.post("/users")
@user_router.get("/changelog1", response_class=HTMLResponse)
async def get_changelog(request: Request):
    """
    Описание изменений сервиса по датам
    """
    if "text/html" in request.headers.get("accept", None):
        return "<html><body><h1>Test</h1></body></html>"
    else:
        return {"ok": 1}
