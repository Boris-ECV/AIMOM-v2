import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from upload import router as upload_router
from transcribe import router as transcribe_router
from diarize import router as diarize_router
from summarize import router as summarize_router
from progress import router as progress_router
from history import router as history_router
from export import router as export_router
from admin import router as admin_router
from auth import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Minutes API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """統一處理未預期例外。

    FastAPI 的例外處理器會在 CORSMiddleware 之內執行，回應會正確帶上
    CORS 標頭；若讓例外原樣往上拋，會由 Starlette 最外層的
    ServerErrorMiddleware 產生 500 回應，該回應不會經過 CORSMiddleware，
    導致瀏覽器誤判為 CORS 被擋（實際上是後端錯誤）。
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"伺服器內部錯誤：{exc}"},
    )


@app.get("/api/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    """回傳目前登入使用者資訊（TASK-008）。"""
    return {"email": user.email, "role": user.role}


_auth_dep = [Depends(get_current_user)]

app.include_router(upload_router, prefix="/api", dependencies=_auth_dep)
app.include_router(transcribe_router, prefix="/api", dependencies=_auth_dep)
app.include_router(diarize_router, prefix="/api", dependencies=_auth_dep)
app.include_router(summarize_router, prefix="/api", dependencies=_auth_dep)
app.include_router(progress_router, prefix="/api", dependencies=_auth_dep)
app.include_router(history_router, prefix="/api", dependencies=_auth_dep)
app.include_router(export_router, prefix="/api", dependencies=_auth_dep)
app.include_router(admin_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
